"""Trusted, typed execution boundary. Deploy behind broker in an isolated private workspace.

Direct Python access is not authentication. Trusted provision() is deliberately
not exposed by dispatch(); editable job files cannot create runs or promote intent.
"""

from __future__ import annotations

import base64
import fcntl
import hashlib
import json
import os
import re
import secrets
import time
import uuid
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from . import core, secure_files, workflow
from .dictionary_retries import DictionaryRetries
from .issues import Issues
from .network import RequestGate, dictionary_word
from .observations import Hooks, boot_id, service_id, transport_hooks
from .policy import (
    AssignmentFacts,
    Facts,
    NetworkFacts,
    Operation,
    Outcome,
    ReceiptState,
    Request,
    Role,
    RunIntent,
    Stage,
    TargetFacts,
    WorkflowFacts,
    evaluate,
)
from .policy_store import PolicyStore, StateError, encode, identifier
from .policy_store import shape as _shape
from .recovery import Recovery
from .wikitext import inventory, reference_inventory


def _category_key(link: str) -> str:
    """Compare category identity without the optional inert-link colon."""
    inner = link[2:-2] if link.startswith("[[") and link.endswith("]]") else link
    return inner.lstrip(":").strip()


class PolicyBlocked(StateError):
    def __init__(self, decision) -> None:
        super().__init__("Policy denied/deferred operation; inspect structured decision.")
        self.decision = decision.as_dict()


class _CapturedWiki:
    """Consume verified snapshots/render ONCE; save final recheck/read-back remain live."""

    def __init__(self, wiki) -> None:
        self.wiki, self.pages, self.preview = wiki, {}, None

    def snapshot(self, language, title, *, sandbox=False):
        key = (language, title, sandbox)
        if key in self.pages:
            return self.pages.pop(key)
        return self.wiki.snapshot(language, title, sandbox=sandbox)

    def render(self, destination, text):
        if self.preview is not None:
            value, self.preview = self.preview, None
            return value
        return self.wiki.render(destination, text)

    def save(self, *args, **kwargs):
        return self.wiki.save(*args, **kwargs)


class Gateway:
    def __init__(
        self, workspace: Path, store: PolicyStore, *, wiki: Any = None,
        clock: Callable[[], float] = time.time, monotonic: Callable[[], float] = time.monotonic,
        boot: str | None = None, gate: RequestGate | None = None,
        dictionary_url: str = core.DICTIONARY_URL,
        vocabulary_database: Path | None = None,
        dictionary_opener: Any = None,
    ) -> None:
        self.workspace, self.store = Path(workspace).absolute(), store
        self.wiki, self.clock, self.monotonic = wiki, clock, monotonic
        self.boot = boot  # boot-id read deferred until dispatch, never at import/construction.
        self.gate = gate or RequestGate()
        parsed = urlsplit(dictionary_url)
        if (parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username
                or parsed.password or parsed.query or parsed.fragment
                or parsed.path not in {"", "/"}):
            raise StateError("Trusted dictionary URL must be credential-free HTTP(S) origin.")
        self.dictionary_url = dictionary_url
        self.vocabulary_database = vocabulary_database
        self.dictionary_opener = dictionary_opener  # Trusted adapter injection for offline tests.
        self.recovery = Recovery(store, self.gate, clock=clock)
        self.issues = Issues(store, self.workspace, clock=clock)

    def provision(self, run: str, manifest: dict, *, expires_at: float) -> str:
        """Trusted local launcher only. Never reachable through capability RPC."""
        run = identifier(run)
        if run.endswith(".intake"):
            raise StateError("Reserved intake suffix.")
        _shape(manifest, {"intent", "source_language", "source_title", "article_title"},
               {"existing_title"})
        intent = RunIntent(manifest["intent"])
        if (not isinstance(manifest["source_language"], str)
                or not re.fullmatch(r"[a-z]{2,12}(?:-[a-z0-9]{1,12})*",
                                    manifest["source_language"])):
            raise StateError("Invalid source Wikipedia language.")
        if intent is RunIntent.SANDBOX_EDIT and manifest["source_language"] == "mg":
            raise StateError("Translation source must be non-Malagasy.")
        core.title(manifest["source_title"])
        destination = core.sandbox_title(manifest["article_title"])
        if expires_at <= self.clock() or expires_at - self.clock() > 86400 * 30:
            raise StateError("Capability lifetime must be positive and at most 30 days.")
        with self.store.transaction() as tx:
            tx.put("runs", run, {"id": run, "manifest": manifest, "intent": intent.value,
                                 "destination": destination, "initialized": False,
                                 "stage": Stage.INTAKE.value, "expires_at": expires_at}, new=True)
            tx.event(self.clock(), "run_provisioned", run, {"intent": intent.value})
        return self._capability(run, Role.COORDINATOR, None, expires_at)

    def _capability(self, run: str, role: Role, assignment: str | None, expiry: float) -> str:
        token = secrets.token_urlsafe(32)
        digest = hashlib.sha256(token.encode()).hexdigest()
        with self.store.transaction() as tx:
            tx.put("capabilities", digest,
                   {"run": run, "role": role.value, "assignment": assignment, "expires_at": expiry},
                   new=True)
            tx.event(self.clock(), "capability_issued", run,
                     {"role": role.value, "assignment": assignment, "expires_at": expiry})
        return token

    def renew(self, run: str, *, expires_at: float) -> str:
        """Trusted host renewal only; original intent, snapshots, gates and receipts unchanged."""
        run = identifier(run)
        if expires_at <= self.clock() or expires_at - self.clock() > 86400 * 30:
            raise StateError("Renewal lifetime must be positive and at most 30 days.")
        self._update(run, expires_at=expires_at)
        return self._capability(run, Role.COORDINATOR, None, expires_at)

    def authenticate(self, token: str) -> dict:
        if not isinstance(token, str) or not 32 <= len(token) <= 200:
            raise StateError("Invalid capability.")
        key = hashlib.sha256(token.encode()).hexdigest()
        cap = self.store.get("capabilities", key)
        if cap is None or cap["expires_at"] <= self.clock() or cap.get("revoked"):
            raise StateError("Unknown/expired/revoked capability.")
        return {**cap, "key": key}

    def _state(self, run: str) -> dict:
        value = self.store.get("runs", run)
        if value is None:
            raise StateError("Unknown run.")
        return value

    def _update(self, run: str, **changes) -> dict:
        with self.store.transaction() as tx:
            state = tx.get("runs", run)
            state.update(changes)
            tx.put("runs", run, state)
        return state

    def _job(self, run: str) -> Path:
        if Path.cwd().absolute() != self.workspace:
            raise StateError("Gateway needs its private workspace; cwd substitution refused.")
        return self.workspace / "runs" / identifier(run)

    def _read(self, run: str, name: str) -> bytes:
        return secure_files.read(self._job(run), name)

    def _json(self, run: str, name: str):
        return json.loads(self._read(run, name))

    def _put(self, run: str, name: str, data: bytes, *, expected: str | None = None) -> str:
        # Store exact historical bytes before mutation, including existing local prose.
        try:
            previous = self._read(run, name)
        except FileNotFoundError:
            previous = None
        if previous is not None:
            digest = core.digest(previous)
            with self.store.transaction() as tx:
                if tx.get("versions", digest) is None:
                    tx.put("versions", digest,
                           {"bytes": base64.b64encode(previous).decode()}, new=True)
        result = secure_files.write(self._job(run), name, data, expected=expected)
        with self.store.transaction() as tx:
            tx.event(self.clock(), "artifact_written", run,
                     {"name": name, "sha256": result,
                      "previous_sha256": core.digest(previous) if previous is not None else None})
        return result

    def _replace(self, run: str, name: str, data: bytes) -> str:
        try:
            expected = core.digest(self._read(run, name))
        except FileNotFoundError:
            expected = None
        return self._put(run, name, data, expected=expected)

    def _editable(self, run: str) -> None:
        state = self._state(run)
        if not state["initialized"] or state["stage"] in {
            Stage.PREPARED.value, Stage.SAVE_UNCONFIRMED.value, Stage.CONFIRMED.value,
        } or self.store.get("attempts", run) is not None:
            raise StateError("Uninitialized/prepared/save-attempt run; fresh run required.")

    def _decision(self, run: str, operation: Operation, facts: Facts, *, pending: bool = False):
        decision = evaluate(Request(operation, Role.COORDINATOR), facts, self.clock())
        with self.store.transaction() as tx:
            tx.event(self.clock(), "policy_decision", run, decision.as_dict())
        if decision.outcome is not Outcome.ALLOW:
            expected = {"workflow.live_revisions_match", "workflow.live_render_matches",
                        "target.account"}
            if not (pending and decision.outcome is Outcome.DEFER
                    and set(decision.required_evidence) <= expected):
                raise PolicyBlocked(decision)
        return decision

    def _network(self, *, write: bool = False) -> NetworkFacts:
        with self.gate.state() as state:
            deadline = max(state.get("next_request", 0), state.get("next_write", 0) if write else 0)
        return NetworkFacts(True, deadline)

    def _sections(self, run: str) -> list[dict]:
        with self.store.transaction() as tx:
            rows = [value for _, value in tx.rows("sections") if value["run"] == run]
        order = self._state(run).get("section_order", [row["id"] for row in rows])
        return sorted(rows, key=lambda row: (
            order.index(row["id"]) if row["id"] in order else len(order)))

    def _complete(self, run: str) -> bool:
        sections = self._sections(run)
        if not sections:
            return False
        plan = self._json(run, "section-plan.json")
        expected = {row["id"] for row in plan} | {
            row["id"] for row in sections if row.get("source_kind") in {"existing", "sandbox"}}
        if expected != {row["id"] for row in sections}:
            return False
        for section in sections:
            if not section.get("accepted"):
                return False
            if any(core.digest(self._read(run, name)) != digest
                   for name, digest in section["hashes"].items()):
                return False
        return True

    def _workflow(self, run: str) -> WorkflowFacts:
        state, review = self._state(run), self.store.get("reviews", run)
        attempt = self.store.get("attempts", run)
        receipt = (ReceiptState.ABSENT if attempt is None else
                   ReceiptState.CONFIRMED if attempt["status"] == "confirmed" else
                   ReceiptState.UNCONFIRMED)
        try:
            hashes = core.artifact_hashes(self._job(run))
        except core.GuardError:
            hashes = None
        review_matches = bool(review and hashes is not None and review["hashes"] == hashes
                              and not state.get("requires_rebase"))
        proposal_matches = None
        if state.get("prepared_digest"):
            proposal = self._json(run, "proposal.json")
            body = {key: value for key, value in proposal.items() if key != "digest"}
            proposal_matches = (
                proposal.get("digest") == state["prepared_digest"]
                == core.digest(core.json_bytes(body))
                and proposal["artifacts"] == hashes
                and core.digest(self._read(run, "preview.html")) == proposal["preview_sha256"]
                and core.digest(self._read(run, "changes.diff")) == proposal["diff_sha256"]
            )
        return WorkflowFacts(
            Stage(state["stage"]), RunIntent(state["intent"]), receipt, self._complete(run),
            self.issues.blockers(run), tuple(
                issue["id"] for issue in self.issues.list(run)
                if issue["kind"] == "source" and issue["status"] == "open"),
            bool(review and (state["stage"] != Stage.PREPARED.value
                             or state.get("proposal_reviewed") == state.get("prepared_digest"))),
            review_matches, proposal_matches,
        )

    def _publish_or_prepare(self, run: str, cap: dict, *, publish: bool) -> dict:
        from dataclasses import replace

        state = self._state(run)
        operation = Operation.PUBLISH if publish else Operation.PREPARE
        job_state = self._json(run, "job.json")
        if core.digest(self._read(run, "job.json")) != state["job_sha256"]:
            raise StateError("Pinned job identity changed.")
        core.check_state(job_state)
        target = TargetFacts("mg.wikipedia.org", state["destination"], 2)
        facts = Facts(network=self._network(write=publish), target=target,
                      workflow=self._workflow(run))
        self._decision(run, operation, facts, pending=True)
        task_name = "publish" if publish else "prepare"
        self.recovery.register_task(run, task_name, self._service(run, "wiki"))
        self.recovery.register_task(run, task_name, self._service(run, "mgwiki"))
        captured = _CapturedWiki(self.wiki)
        live = True
        for name in ("source", "existing", "sandbox"):
            old = job_state[name]
            key = (old["language"], old["requested_title"], name == "sandbox")
            actual = self.wiki.snapshot(key[0], key[1], sandbox=key[2])
            captured.pages[key] = actual
            try:
                core.assert_snapshot(old, actual)
            except core.GuardError:
                live = False
        facts = replace(facts, workflow=replace(facts.workflow, live_revisions_match=live))
        self._decision(run, operation, facts, pending=True)
        text = core.checked_draft(self._job(run))
        html = self.wiki.render(state["destination"], text)
        captured.preview = html
        if publish:
            expected_render = self._json(run, "proposal.json")["preview_sha256"]
            render_matches = core.digest(html.encode()) == expected_render
            if hasattr(self.wiki, "authenticated_account"):
                account = self.wiki.authenticated_account()
            else:
                site = self.wiki.site("mg")
                site.login()
                account = site.user()
            facts = replace(facts, target=replace(target, account=account),
                            workflow=replace(facts.workflow, live_render_matches=render_matches))
        self._decision(run, operation, facts)
        if not publish:
            result = core.prepare(captured, self._job(run))
            self._update(run, stage=Stage.PREPARED.value, prepared_digest=result["digest"])
            self._mark_complete(run, "prepare")
            return result
        # Atomic durable claim BEFORE invoking core.publish. Lost receipt/file cannot erase claim.
        with self.store.transaction() as tx:
            active_cap = tx.get("capabilities", cap["key"])
            if (active_cap is None or active_cap.get("revoked")
                    or active_cap["expires_at"] <= self.clock()):
                raise StateError("Publication capability expired/revoked during preflight.")
            tx.put("attempts", run, {"status": "unconfirmed", "proposal": state["prepared_digest"],
                                     "draft_sha256": core.digest(text.encode()),
                                     "destination": state["destination"],
                                     "base_revision": job_state["sandbox"]["revision_id"]},
                   new=True)
            updated = tx.get("runs", run)
            updated["stage"] = Stage.SAVE_UNCONFIRMED.value
            tx.put("runs", run, updated)
            tx.event(self.clock(), "save_reserved", run, {"digest": state["prepared_digest"]})
        result = core.publish(captured, self._job(run))
        with self.store.transaction() as tx:
            attempt = tx.get("attempts", run)
            attempt.update(status="confirmed", receipt=result)
            tx.put("attempts", run, attempt)
            updated = tx.get("runs", run)
            updated["stage"] = Stage.CONFIRMED.value
            tx.put("runs", run, updated)
        self._mark_complete(run, "publish")
        return result

    def dispatch(self, token: str, command: str, arguments: dict) -> dict:
        """Serial RPC/Python boundary. No shell/eval operation."""
        cap = self.authenticate(token)
        run, role = cap["run"], Role(cap["role"])
        if not isinstance(command, str) or not isinstance(arguments, dict):
            raise StateError("Typed command/arguments required.")
        lock = os.open(self.store.path.with_suffix(".lock"),
                       os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        operation_id = uuid.uuid4().hex
        try:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise StateError("Gateway busy; no parallel Wikipedia worker allowed.") from exc
            self.store.verify()
            with self.store.transaction() as tx:
                tx.put("operations", operation_id, {"run": run, "command": command,
                                                    "status": "reserved"}, new=True)
                tx.event(self.clock(), "operation_reserved", run, {"operation": operation_id,
                                                                  "command": command})
            if self.wiki is None:
                self.wiki = core.Wiki()
            probe = command == "service-probe"
            def before(service, safe, url):
                self.recovery.before(service, safe, url, probe=probe)
            hooks = Hooks(before,
                          self.recovery.observe, self.clock, self.monotonic, self.boot or boot_id(),
                          self.gate)
            with transport_hooks(hooks):
                result = self._execute(run, cap, role, command, arguments)
            with self.store.transaction() as tx:
                record = tx.get("operations", operation_id)
                record["status"] = "complete"
                tx.put("operations", operation_id, record)
                tx.event(self.clock(), "operation_complete", run, {"operation": operation_id})
            return {"operation_id": operation_id, "result": result,
                    "alerts": self.recovery.alerts(run)}
        except Exception as exc:
            # No native retries, exception-text parsing, secrets or remote text in audit.
            with self.store.transaction() as tx:
                record = tx.get("operations", operation_id)
                if record:
                    record["status"] = "unknown_or_failed"
                    tx.put("operations", operation_id, record)
                    tx.event(self.clock(), "operation_failed", run,
                             {"operation": operation_id, "command": command,
                              "error": type(exc).__name__,
                              "next_eligible_at": getattr(exc, "next_eligible_at", None)})
            raise
        finally:
            try:
                # Projection failure must never masquerade as permission to retry a save.
                if self.store.get("operations", operation_id) is not None:
                    try:
                        self.issues.project(run)
                    except (StateError, OSError) as exc:
                        self._update(run, memo_error=type(exc).__name__)
            finally:
                os.close(lock)

    def _execute(self, run: str, cap: dict, role: Role, command: str, args: dict) -> dict:
        state = self._state(run)
        if command == "artifact":
            _shape(args, {"name"}, {"offset", "limit"})
            name = args["name"]
            secure_files.relative(name)
            if role is not Role.COORDINATOR:
                shared = {"source.wiki", "existing.wiki", "sandbox.wiki", "vocabulary.json",
                          "deferred-issues.md", "source-issues.md"}
                prefix = ("sections/" if role is Role.SECTION_WORKER else "issue-resolutions/")
                scope = prefix + cap["assignment"] + ("/" if role is Role.SECTION_WORKER else ".md")
                if name not in shared and not name.startswith("evidence/") and not (
                    name.startswith(scope) if role is Role.SECTION_WORKER else name == scope
                ):
                    raise StateError("Artifact outside worker assignment.")
            raw = self._read(run, name)
            text = raw.decode("utf-8")
            if "offset" in args or "limit" in args:
                offset, limit = args.get("offset", 1), args.get("limit", 1000)
                if (type(offset) is not int or type(limit) is not int
                        or offset < 1 or not 1 <= limit <= 2000):
                    raise StateError("Artifact chunks need positive line offset/limit <=2000.")
                lines = text.splitlines(keepends=True)
                end = min(len(lines), offset - 1 + limit)
                return {"name": name, "content": "".join(lines[offset - 1:end]),
                        "sha256": core.digest(raw), "total_lines": len(lines),
                        "next_offset": end + 1 if end < len(lines) else None,
                        "complete": offset == 1 and end == len(lines)}
            return {"name": name, "content": text, "sha256": core.digest(raw), "complete": True}
        if command == "submit":
            _shape(args, {"name", "content"}, {"expected_sha256"})
            frozen = state["stage"] in {
                Stage.PREPARED.value, Stage.SAVE_UNCONFIRMED.value, Stage.CONFIRMED.value,
            }
            if role is not Role.ISSUE_SOLVER or not frozen:
                self._editable(run)
            name = args["name"]
            secure_files.relative(name)
            if role is Role.SECTION_WORKER:
                allowed = {f"sections/{cap['assignment']}/{file}" for file in
                           ("section.wiki", "notes.wiki", "vocabulary.json")}
            elif role is Role.ISSUE_SOLVER:
                allowed = {f"issue-resolutions/{cap['assignment']}.md"}
            else:
                allowed = {"draft.wiki", "notes.wiki", "vocabulary.json", "unknown-vocabulary.wiki"}
                if name.startswith("evidence/"):
                    allowed.add(name)
            if name not in allowed or not isinstance(args["content"], str):
                raise StateError("Write outside assignment/artifact allowlist.")
            digest = self._put(run, name, args["content"].encode(),
                               expected=args.get("expected_sha256"))
            if role is Role.SECTION_WORKER:
                with self.store.transaction() as tx:
                    section = tx.get("sections", run + "/" + cap["assignment"])
                    section["accepted"] = False
                    tx.put("sections", run + "/" + cap["assignment"], section)
                    task = tx.get("tasks", run + "/" + cap["assignment"])
                    if task:
                        task["status"] = "pending"
                        tx.put("tasks", run + "/" + cap["assignment"], task)
            next_stage = (Stage.PLANNED if role is Role.SECTION_WORKER else
                          Stage.ASSEMBLED if state["stage"] in {
                              Stage.ASSEMBLED.value, Stage.REVIEWED.value,
                          } else Stage(state["stage"]))
            self._update(run, stage=next_stage.value)
            return {"sha256": digest, "status": "submitted_not_accepted"}
        if role is not Role.COORDINATOR:
            raise StateError("Coordinator capability required; worker operation denied.")
        if command == "artifact-history":
            _shape(args, {"name"}, {"sha256"})
            name = args["name"]
            current = self._read(run, name)
            history = [event for event in self.store.events(run)
                       if event["kind"] == "artifact_written" and event["payload"]["name"] == name]
            known = {core.digest(current)}
            for event in history:
                known.update(value for key, value in event["payload"].items()
                             if key in {"sha256", "previous_sha256"} and value)
            if "sha256" not in args:
                return {"name": name, "sha256": sorted(known), "events": history}
            requested = args["sha256"]
            if requested not in known:
                raise StateError("Version outside this run/artifact history.")
            version = self.store.get("versions", requested)
            raw = base64.b64decode(version["bytes"]) if version else current
            if core.digest(raw) != requested:
                raise StateError("Archived version corrupt/missing; never substitute other bytes.")
            return {"name": name, "sha256": requested, "content": raw.decode("utf-8")}
        if command == "status":
            _shape(args, set())
            directory = run if state["initialized"] else run + ".intake"
            return {"run": run, "intent": state["intent"], "stage": state["stage"],
                    "manifest": state["manifest"], "destination": state["destination"],
                    "sections": self._sections(run), "issues": self.issues.list(run),
                    "attempt": self.store.get("attempts", run), "services": self.recovery.status(),
                    "tasks": self._tasks(run),
                    "memo_error": state.get("memo_error"),
                    "memo": f"runs/{directory}/deferred-issues.md"}
        if command == "submit-assigned":
            _shape(args, {"worker_capability", "name", "content"}, {"expected_sha256"})
            child = self.authenticate(args["worker_capability"])
            if child["run"] != run or child["role"] == Role.COORDINATOR.value:
                raise StateError("Local import needs this run's worker capability.")
            # Offline OpenCode workers retain read/patch-only permissions. Coordinator transports
            # their exact local bytes; provenance explicitly says proxy, not worker tool identity.
            result = self._execute(run, child, Role(child["role"]), "submit",
                                   {key: value for key, value in args.items()
                                    if key != "worker_capability"})
            with self.store.transaction() as tx:
                tx.event(self.clock(), "worker_artifact_imported_by_coordinator", run,
                         {"assignment": child["assignment"], "role": child["role"],
                          "name": args["name"], "sha256": result["sha256"]})
            return result
        if command == "init":
            _shape(args, set(), {"expected_manifest"})
            if args.get("expected_manifest", state["manifest"]) != state["manifest"]:
                raise StateError("CLI source/target does not match trusted run manifest.")
            if state["initialized"]:
                raise StateError("Run already initialized; snapshots retained.")
            self._decision(run, Operation.READ_SOURCE, Facts(network=self._network()))
            manifest = state["manifest"]
            self.recovery.register_task(run, "init", self._service(run, "wiki"))
            result = core.initialize(self.wiki, self._job(run), manifest["source_language"],
                                     manifest["source_title"], manifest["article_title"],
                                     manifest.get("existing_title"))
            self._update(run, initialized=True, stage=Stage.PINNED.value,
                         job_sha256=core.digest(self._read(run, "job.json")))
            intake = self.workspace / "runs" / (run + ".intake") / "evidence"
            inherited = []
            if intake.is_dir():
                for path in sorted(intake.iterdir()):
                    name = "evidence/intake-" + path.name
                    self._put(run, name, secure_files.read(intake, path.name))
                    old = self.store.get("evidence", run + "/evidence/" + path.name)
                    if old and old["sha256"] == core.digest(self._read(run, name)):
                        with self.store.transaction() as tx:
                            tx.put("evidence", run + "/" + name,
                                   {**old, "inherited_from": "evidence/" + path.name}, new=True)
                    inherited.append(name)
            self._replace(run, "notes.wiki", self._read(run, "notes.wiki") +
                          b"\nDeferred issues: deferred-issues.md; "
                          b"source issues: source-issues.md.\n")
            self._mark_complete(run, "init")
            return {"destination": result["destination"], "status": "pinned",
                    "intake_evidence": inherited}
        if command == "service-probe":
            _shape(args, {"service"})
            service = self._service(run, args["service"])
            prior = self.store.get("services", service)
            result = self._remote(run, command, args)
            latest = self.store.get("services", service)
            fresh = bool(latest and latest.get("latest", {}).get("id") !=
                         (prior or {}).get("latest", {}).get("id"))
            return {"probe_observed": fresh, "result": result,
                    "status": "real_response" if fresh else "deferred_no_fresh_probe"}
        if command in {"lookup", "read"}:
            return self._remote(run, command, args)
        if command == "resume":
            _shape(args, {"task"})
            task = self.store.get("tasks", run + "/" + identifier(args["task"]))
            if task is None or task.get("request", {}).get("command") not in {"lookup", "read"}:
                raise StateError("Only recorded idempotent read tasks may resume; never saves.")
            if task["status"] == "complete":
                return {"status": "already_complete", "task": args["task"]}
            request = task["request"]
            return self._remote(run, request["command"], request["arguments"])
        if command == "countries":
            _shape(args, set(), {"refresh"})
            refresh = args.get("refresh", False)
            if type(refresh) is not bool:
                raise StateError("Refresh flag must be boolean.")
            if refresh:
                self._decision(run, Operation.READ_SOURCE, Facts(network=self._network()))
                (self.workspace / "data").mkdir(exist_ok=True)
            return core.country_names(self.wiki, refresh=refresh)
        if command in {"vocab", "vocab-audit", "coverage", "links-build", "dictionary-index",
                       "vocabulary-report", "citation-audit", "metadata-audit", "license-report"}:
            return self._offline(run, command, args)
        if command == "license-evidence":
            from .licenses import file_name, license_evidence

            _shape(args, {"filename"})
            self._editable(run)
            filename = file_name(args["filename"])
            self._decision(run, Operation.READ_SOURCE, Facts(network=self._network()))
            response = self.wiki.file_metadata(filename)
            result = license_evidence(filename, response)
            result.update(origin="broker_image_info_read",
                          source_api="https://mg.wikipedia.org/w/api.php",
                          captured_at=self.clock())
            return self._evidence_result(run, command, result)
        if command in {"links-query", "image-info", "category-info", "template-info"}:
            required = ({"language", "titles"} if command == "links-query" else
                        {"titles"} if command in {"category-info", "template-info"}
                        else {"filename"})
            _shape(args, required)
            self._editable(run)  # Refuse frozen evidence work before any remote request.
            self._decision(run, Operation.READ_SOURCE, Facts(network=self._network()))
            result = (self.wiki.link_targets(args["language"], args["titles"])
                       if command == "links-query" else self.wiki.category_metadata(args["titles"])
                      if command == "category-info" else self.wiki.template_metadata(args["titles"])
                      if command == "template-info" else self.wiki.file_metadata(args["filename"]))
            return self._evidence_result(run, command, result)
        if command == "source-expand":
            _shape(args, {"index"})
            self._editable(run)
            if type(args["index"]) is not int or args["index"] < 0:
                raise StateError("Source template index must be a nonnegative integer.")
            pinned = self._json(run, "job.json")
            source = self._read(run, "source.wiki")
            if (core.digest(self._read(run, "job.json")) != state["job_sha256"]
                    or core.digest(source) != pinned["source"]["sha256"]):
                raise StateError("Pinned source identity changed; expansion refused.")
            calls = inventory(source.decode())["templates"]
            if args["index"] >= len(calls):
                raise StateError("Template index outside the pinned source inventory.")
            call = calls[args["index"]]
            self._decision(run, Operation.READ_SOURCE, Facts(network=self._network()))
            result = self.wiki.expand_template(pinned["source"]["language"],
                                               pinned["source"]["title"], call)
            return self._evidence_result(run, command, {
                "language": pinned["source"]["language"], "title": pinned["source"]["title"],
                "source_sha256": core.digest(source), "index": args["index"],
                "source_revision": pinned["source"]["revision_id"],
                "template": call, "response": result,
                "limits": "Actual expansion of this pinned call; not Commons rights, "
                          "Malagasy template compatibility or editorial approval. Current "
                          "template dependencies, not historical source-revision expansion.",
            })
        if command == "render-check":
            from .rendering import rendering_report

            _shape(args, set())
            self._editable(run)
            if not self._complete(run) or state["stage"] not in {
                Stage.ASSEMBLED.value, Stage.REVIEWED.value,
            }:
                raise StateError("Render check requires all accepted sections assembled.")
            text = self._read(run, "draft.wiki").decode()
            if errors := core.lint_wikitext(text):
                raise StateError(" ".join(errors))
            self._decision(run, Operation.RENDER_PREVIEW, Facts(
                network=self._network(), target=TargetFacts("mg.wikipedia.org",
                                                           state["destination"], 2)))
            html = self.wiki.render(state["destination"], text)
            diagnostics = rendering_report(html)
            return self._evidence_result(run, command, {
                "draft_sha256": core.digest(text.encode()),
                "html_sha256": core.digest(html.encode()),
                "html": html, "diagnostics": diagnostics, "valid": diagnostics["valid"],
                "status": "rendered_not_editorially_reviewed",
                "limits": "Guarded read-only parse; gates/stage/proposal unchanged. "
                          "Offline review required; no preview resources fetched.",
            })
        if command == "plan":
            _shape(args, set(), {"level"})
            self._editable(run)
            result = workflow.plan_sections(self._job(run), level=args.get("level", 2))
            plan = self._json(run, "section-plan.json")
            with self.store.transaction() as tx:
                for row in plan:
                    identifier(row["id"])
                    tx.put("sections", run + "/" + row["id"],
                           {"run": run, "id": row["id"], "accepted": False}, new=True)
            self._update(run, stage=Stage.PLANNED.value, section_order=[row["id"] for row in plan])
            return result
        if command == "plan-local":
            _shape(args, {"id", "source", "start", "end", "after"})
            self._editable(run)
            ident, after = identifier(args["id"]), identifier(args["after"])
            if args["source"] not in {"existing", "sandbox"}:
                raise StateError("Local section needs pinned existing/sandbox source.")
            start, end = args["start"], args["end"]
            lines = self._read(run, args["source"] + ".wiki").decode().splitlines(keepends=True)
            order = state.get("section_order", [])
            if (type(start) is not int or type(end) is not int
                    or not 1 <= start <= end <= len(lines)
                    or after not in order or ident in order):
                raise StateError("Unique ID, valid pinned line range and ordered anchor required.")
            fragment = "".join(lines[start - 1:end]).encode()
            self._put(run, f"sections/{ident}/source.wiki", fragment)
            with self.store.transaction() as tx:
                tx.put("sections", run + "/" + ident,
                       {"run": run, "id": ident, "accepted": False, "source_kind": args["source"],
                         "source_start": start, "source_end": end,
                         "source_sha256": core.digest(fragment)},
                       new=True)
            order = list(order)
            order.insert(order.index(after) + 1, ident)
            self._update(run, stage=Stage.PLANNED.value, section_order=order)
            return {"status": "local_section_planned", "id": ident}
        if command == "assign":
            _shape(args, {"role", "id"})
            child_role = Role(args["role"])
            if child_role is not Role.ISSUE_SOLVER:
                self._editable(run)
            assignment = identifier(args["id"])
            kind = "sections" if child_role is Role.SECTION_WORKER else "issues"
            if (child_role is Role.COORDINATOR
                    or self.store.get(kind, run + "/" + assignment) is None):
                raise StateError("Existing section/issue required; no coordinator delegation.")
            return {"capability": self._capability(run, child_role, assignment, cap["expires_at"]),
                    "role": child_role.value, "assignment": assignment}
        if command == "revoke-assignment":
            _shape(args, {"id"})
            assignment = identifier(args["id"])
            with self.store.transaction() as tx:
                for key, child in tx.rows("capabilities"):
                    if child["run"] == run and child["assignment"] == assignment:
                        child["revoked"] = True
                        tx.put("capabilities", key, child)
                tx.event(self.clock(), "assignment_revoked", run, {"assignment": assignment})
            return {"status": "assignment_revoked"}
        if command == "accept-section":
            _shape(args, {"id", "note"})
            self._editable(run)
            ident = identifier(args["id"])
            section = self.store.get("sections", run + "/" + ident)
            if section is None or not args["note"].strip():
                raise StateError("Assigned section/coordinator review note required.")
            names = [f"sections/{ident}/{name}" for name in
                     ("source.wiki", "section.wiki", "notes.wiki", "vocabulary.json")]
            hashes = self.issues.evidence(run, names)
            if not self._read(run, names[1]).strip() or not self._read(run, names[2]).strip():
                raise StateError("Nonempty section and handoff required.")
            # Validate all source ranges and exact assigned fragment before acceptance.
            workflow._load_plan(self._job(run))
            if section.get("source_kind"):
                source = self._read(run, section["source_kind"] + ".wiki").decode()
                lines = source.splitlines(keepends=True)
                selected = lines[section["source_start"] - 1:section["source_end"]]
                expected = "".join(selected).encode()
                if expected != self._read(run, names[0]):
                    raise StateError("Local section source changed.")
            workflow._worker_vocabulary(self._job(run), self._job(run) / "sections" / ident, ident)
            self._decision(run, Operation.ACCEPT_SECTION,
                           Facts(assignment=AssignmentFacts(ident, ident, True, True)))
            section.update(accepted=True, hashes=hashes, note=args["note"])
            with self.store.transaction() as tx:
                tx.put("sections", run + "/" + ident, section)
                task = tx.get("tasks", run + "/" + ident)
                if task:
                    task["status"] = "complete"
                    tx.put("tasks", run + "/" + ident, task)
            return {"id": ident, "status": "accepted_for_assembly"}
        if command == "assemble":
            _shape(args, set())
            self._editable(run)
            if not self._complete(run):
                raise StateError("Missing/changed/unaccepted sections block assembly.")
            output = self._job(run) / ("assembly-" + uuid.uuid4().hex)
            if any(section.get("source_kind") for section in self._sections(run)):
                result = self._assemble_local(run, output)
            else:
                result = workflow.assemble_sections(self._job(run), output=output)
            combined = json.loads(secure_files.read(output, "worker-vocabulary.json"))
            previous = self._json(run, "vocabulary.json")
            for entry in previous:
                key = tuple(entry.get(field) for field in ("source_language", "source_term",
                                                           "source_sense", "domain"))
                matches = [record for record in combined if tuple(record.get(field) for field in
                           ("source_language", "source_term", "source_sense", "domain")) == key]
                if matches and any(record.get("chosen_expression") != entry.get("chosen_expression")
                                   for record in matches):
                    raise StateError("Terminology conflict; retain work and reconcile explicitly.")
                if not matches:
                    combined.append(entry)
                else:
                    for record in matches:
                        evidence = sorted(
                            set(record["evidence_files"]) | set(entry["evidence_files"]))
                        record.update(entry)
                        record["evidence_files"] = evidence
            self._replace(run, "draft.wiki", secure_files.read(output, "draft.wiki"))
            self._replace(run, "vocabulary.json", core.json_bytes(combined))
            self._replace(run, "notes.wiki", self._read(run, "notes.wiki") + b"\n" +
                          secure_files.read(output, "section-handoffs.md"))
            self._update(run, stage=Stage.ASSEMBLED.value)
            return result
        if command == "record-issue":
            _shape(args, {"id", "kind", "details", "next_action", "blocking", "evidence"},
                   {"section", "claims", "handling"})
            result = self.issues.record(run, args["id"],
                                        **{k: v for k, v in args.items() if k != "id"})
            self._invalidate_issue_review(run)
            return result
        if command == "accept-issue":
            _shape(args, {"id", "note", "evidence"})
            ident = identifier(args["id"])
            proposal = f"issue-resolutions/{ident}.md"
            if not self._read(run, proposal).strip():
                raise StateError("Issue solver proposal required.")
            self._decision(run, Operation.ACCEPT_ISSUE,
                           Facts(assignment=AssignmentFacts(ident, ident, True, True)))
            result = self.issues.resolve(run, ident, note=args["note"],
                                         evidence=[proposal, *args["evidence"]])
            self._invalidate_issue_review(run)
            return result
        if command == "review":
            _shape(args, {"gates", "note", "evidence"}, {"omissions", "category_evidence"})
            self._editable(run)
            self.issues.project(run)
            if state["stage"] != Stage.ASSEMBLED.value or not self._complete(run):
                raise StateError("Assemble all accepted sections before whole-article review.")
            if (not isinstance(args["gates"], dict) or set(args["gates"]) != set(core.GATES)
                    or any(value is not True for value in args["gates"].values())
                    or not args["note"].strip() or self.issues.blockers(run)):
                raise StateError("All actual editorial attestations/no material blockers required.")
            self._validate_vocabulary(run)
            coverage_file = self._review_structure(run, args)
            evidence = self.issues.evidence(run, args["evidence"])
            pinned_job = self._json(run, "job.json")
            for name in ("source", "existing", "sandbox"):
                if core.digest(self._read(run, name + ".wiki")) != pinned_job[name]["sha256"]:
                    raise StateError("Pinned snapshot file changed; retain original job evidence.")
            evidence.update(self.issues.evidence(run, [
                "job.json", "source.wiki", "existing.wiki", "sandbox.wiki", "notes.wiki",
                "draft.wiki", "vocabulary.json", "source-issues.md", "section-plan.json",
                "section-inputs.json", "source-inventory.json",
            ]))
            evidence.update(self.issues.evidence(run, [coverage_file]))
            if args.get("category_evidence"):
                evidence.update(self.issues.evidence(run, args["category_evidence"]))
            if {"editorial-state.json", "review.json"} & evidence.keys():
                raise StateError("Generated attestations cannot be their own review evidence.")
            snapshot = {"policy_version": "1", "sections": self._sections(run),
                        "issues": self.issues.list(run), "review_evidence": evidence}
            self._replace(run, "editorial-state.json", core.json_bytes(snapshot))
            self._replace(run, "review.json", core.json_bytes(args["gates"]))
            core.checked_draft(self._job(run))
            with self.store.transaction() as tx:
                tx.put("reviews", run, {"hashes": core.artifact_hashes(self._job(run)),
                                        "evidence": evidence, "note": args["note"],
                                        "reviewer": "coordinator", "at": self.clock()})
                tx.event(self.clock(), "review_recorded", run, {"evidence": evidence})
            self._update(run, stage=Stage.REVIEWED.value)
            return {"status": "review_recorded_not_semantically_proven"}
        if command == "attest-proposal":
            _shape(args, {"digest", "note"})
            if (state["stage"] != Stage.PREPARED.value or not args["note"].strip()
                    or args["digest"] != state.get("prepared_digest")):
                raise StateError("Exact digest and actual raw/offline preview review required.")
            if not self._workflow(run).proposal_matches:
                raise StateError("Prepared content changed; fresh run required.")
            with self.store.transaction() as tx:
                tx.event(self.clock(), "proposal_review_recorded", run,
                         {"digest": args["digest"], "note": args["note"]})
            self._update(run, proposal_reviewed=args["digest"])
            return {"status": "proposal_review_recorded"}
        if command in {"prepare", "publish"}:
            _shape(args, set())
            return self._publish_or_prepare(run, cap, publish=command == "publish")
        if command == "reconcile":
            _shape(args, set())
            return self._reconcile(run)
        if command == "task-depend":
            _shape(args, {"task", "service"})
            task = identifier(args["task"])
            if self.store.get("sections", run + "/" + task) is None:
                raise StateError("Only planned section IDs can register extra dependencies.")
            self.recovery.register_task(run, task, self._service(run, args["service"]))
            return {"status": "dependency_recorded"}
        if command == "skip":
            _shape(args, {"tasks", "service"})
            if not isinstance(args["tasks"], list):
                raise StateError("Task list required.")
            return self.recovery.skip(run, tuple(args["tasks"]),
                                      self._service(run, args["service"]))
        if command == "ack-alert":
            _shape(args, {"episode"})
            self.recovery.acknowledge(run, args["episode"])
            return {"status": "alert_acknowledged"}
        raise StateError("Unknown broker operation; no generic execute/HTTP/filepath facility.")

    def _service(self, run: str, service: str) -> str:
        if service == "dictionary":
            return service_id(self.dictionary_url, dictionary=True)
        if service == "wiki":
            language = self._state(run)["manifest"]["source_language"]
            return service_id(f"https://{language}.wikipedia.org/w/api.php")
        if service == "mgwiki":
            return "wiki:mg.wikipedia.org"
        raise StateError("Service must be trusted configured dictionary or run source Wikipedia.")

    def _assemble_local(self, run: str, output: Path) -> dict:
        """Same native fragment/evidence contract, plus explicitly planned local-only sections."""
        pieces, notes, vocabulary = [], [], []
        for section in self._sections(run):
            ident = section["id"]
            directory = self._job(run) / "sections" / ident
            pieces.append(self._read(run, f"sections/{ident}/section.wiki").decode())
            handoff = self._read(run, f"sections/{ident}/notes.wiki").decode()
            notes.append(f"## {ident}\n\n" + handoff)
            vocabulary.extend(workflow._worker_vocabulary(self._job(run), directory, ident))
        text = pieces[0]
        for piece in pieces[1:]:
            if not text.endswith("\n"):
                text += "\n"
            if not text.endswith("\n\n"):
                text += "\n"
            text += piece
        if not text.endswith("\n"):
            text += "\n"
        refs = reference_inventory(text)
        if refs["undefined"] or refs["conflicts"]:
            raise StateError("Unresolved/conflicting cross-section references; correct workers.")
        output.mkdir(exist_ok=False)
        secure_files.write(output, "draft.wiki", text.encode())
        secure_files.write(output, "worker-vocabulary.json", core.json_bytes(vocabulary))
        secure_files.write(output, "section-handoffs.md", "\n\n".join(notes).encode())
        return {"output": str(output), "status": "candidate_only", "sections": len(pieces)}

    def _invalidate_issue_review(self, run: str) -> None:
        state = self._state(run)
        if state["stage"] == Stage.REVIEWED.value:
            self._update(run, stage=Stage.ASSEMBLED.value)
        elif state["stage"] in {Stage.PREPARED.value, Stage.SAVE_UNCONFIRMED.value,
                                 Stage.CONFIRMED.value}:
            self._update(run, requires_rebase=True)

    def _tasks(self, run: str) -> list[dict]:
        with self.store.transaction() as tx:
            return [value for _, value in tx.rows("tasks") if value["run"] == run]

    def _mark_complete(self, run: str, task: str) -> None:
        with self.store.transaction() as tx:
            value = tx.get("tasks", run + "/" + task)
            if value:
                value["status"] = "complete"
                tx.put("tasks", run + "/" + task, value)

    def _evidence_result(self, run: str, command: str, result: dict) -> dict:
        self._editable(run)
        filename = f"evidence/{command}-{uuid.uuid4().hex}.json"
        self._put(run, filename, core.json_bytes(result))
        with self.store.transaction() as tx:
            tx.put("evidence", run + "/" + filename,
                   {"kind": command, "sha256": core.digest(self._read(run, filename)),
                    "at": self.clock()}, new=True)
        return {"evidence_file": filename, "result": result}

    def _validate_vocabulary(self, run: str) -> None:
        records = self._json(run, "vocabulary.json")
        if not isinstance(records, list):
            raise StateError("Vocabulary memo must be a list.")
        required = {"source_term", "source_language", "domain", "source_sense",
                    "english_definition",
                    "definition_origin", "malagasy_definition", "chosen_expression", "reason"}
        uncertain = set()
        for entry in records:
            if (not isinstance(entry, dict) or any(not isinstance(entry.get(field), str)
                    or not entry[field].strip() for field in required)
                    or entry.get("definition_origin") not in {
                        "dictionary", "editorial_simple_english"}
                    or entry.get("status") not in {"verified", "descriptive"}
                    or not isinstance(entry.get("evidence_files"), list)
                    or not entry["evidence_files"]):
                raise StateError("Vocabulary needs sense, definitions, provenance and resolution.")
            pinned = self.issues.evidence(run, entry["evidence_files"])
            origins = []
            for name, digest in pinned.items():
                provenance = self.store.get("evidence", run + "/" + name)
                if provenance and provenance["sha256"] == digest:
                    origins.append(provenance)
            if entry["definition_origin"] == "dictionary" and not any(
                origin["kind"] == "lookup" and origin.get("edition") == "en"
                and origin.get("status") == "found" for origin in origins
            ):
                raise StateError("Dictionary definition needs pinned genuine English lookup.")
            if entry["status"] == "verified" and not any(
                origin["kind"] == "lookup" and origin.get("edition") == "mg"
                and origin.get("status") == "found" for origin in origins
            ):
                raise StateError("Verified candidate needs genuine Malagasy dictionary evidence.")
            if entry["domain"].casefold() in {"math", "mathematics", "matematika", "mathématiques"}:
                if not any(origin["kind"] == "vocab" for origin in origins):
                    raise StateError("Mathematical term needs pinned read-only SQLite query.")
            if entry["source_language"] == "en" and entry["status"] != "verified":
                uncertain.add(entry["source_term"].casefold().strip())
        if len(uncertain) > 100:
            name = "unknown-vocabulary.wiki"
            try:
                existing = self._read(run, name)
            except FileNotFoundError:
                existing = b"# Unknown vocabulary\n"
            content = existing
            for entry in records:
                if entry["source_language"] == "en" and entry["status"] != "verified":
                    marker = ("<!-- vocabulary:" + core.digest(encode([
                        entry["source_term"], entry["source_sense"], entry["domain"],
                    ]).encode()) + " -->").encode()
                    if marker not in content:
                        content += (b"\n" + marker + b"\n" + encode(entry).encode() +
                                    b"\nOne-word label not dictionary-verified; "
                                    b"descriptive meaning reviewed. "
                                    b"Next: optional later terminology review.\n")
                    if name not in entry["evidence_files"]:
                        entry["evidence_files"].append(name)
            self._replace(run, name, content)
            self._replace(run, "vocabulary.json", core.json_bytes(records))

    def _review_structure(self, run: str, args: dict) -> str:
        report = workflow.coverage_report(self._job(run), self._job(run) / "draft.wiki")
        omitted = args.get("omissions", {})
        if not isinstance(omitted, dict) or omitted.keys() - {"images", "urls"}:
            raise StateError("Omissions must be explicit image/URL reason maps.")
        missing_images = set(report["missing_files"])
        missing_images.update(candidate["value"].replace("_", " ")
                              for candidate in report["source"]["template_file_candidates"]
                              if candidate["value"].replace("_", " ")
                              not in report["draft"]["files"])
        missing_items = (("images", missing_images), ("urls", set(report["missing_source_urls"])))
        for kind, missing in missing_items:
            reasons = omitted.get(kind, {})
            if (not isinstance(reasons, dict) or not missing <= reasons.keys()
                    or any(not isinstance(reason, str) or not reason.strip()
                           for reason in reasons.values())):
                raise StateError("Missing source images/citation URLs need justified omissions.")
        draft_categories = report["draft"]["categories"]
        draft_keys = [_category_key(link) for link in draft_categories]
        preserved = set()
        existing_counts = Counter()
        for filename in ("existing.wiki", "sandbox.wiki"):
            local = inventory(self._read(run, filename).decode())
            local_missing = {name for name, count in local["files"].items()
                             if count > report["draft"]["files"].get(name, 0)}
            local_urls = set(local["urls"]) - set(report["draft"]["urls"])
            if (not local_missing <= omitted.get("images", {}).keys()
                    or not local_urls <= omitted.get("urls", {}).keys()):
                raise StateError("Preserve local images/citation URLs or give explicit reasons.")
            original = local["categories"]
            expected = [_category_key(link) for link in original]
            cursor = iter(draft_keys)
            if any(not any(candidate == link for candidate in cursor) for link in expected):
                raise StateError("Preserve existing category targets, labels, sort keys and order.")
            preserved.update(expected)
            existing_counts |= Counter(expected)
        if any(count > max(existing_counts[key], 1)
               for key, count in Counter(draft_keys).items()):
            raise StateError("Do not duplicate existing or newly added category links.")
        additions = set(draft_keys) - preserved
        verified = set()
        category_files = args.get("category_evidence", [])
        if not isinstance(category_files, list):
            raise StateError("Category evidence must name pinned metadata files.")
        for filename in category_files:
            raw = self._read(run, filename)
            provenance = self.store.get("evidence", run + "/" + filename)
            if (not provenance or provenance["kind"] != "category-info"
                    or provenance["sha256"] != core.digest(raw)):
                raise StateError("Category naming needs genuine pinned namespace metadata.")
            data = json.loads(raw)
            pages = data["response"].get("query", {}).get("pages", [])
            present = {page["title"] for page in pages if page.get("ns") == 14 and (
                not page.get("missing") or page.get("categoryinfo", {}).get("size", 0) > 0)}
            verified.update(requested for requested, canonical
                            in data["requested_to_canonical"].items()
                            if canonical in present)
        for link in additions:
            target = link.split("|", 1)[0].strip()
            if core.title(target) not in verified:
                raise StateError("New categories need verified Malagasy targets; never guess.")
        report.update(omissions=omitted, category_evidence=category_files)
        return self._evidence_result(run, "coverage", report)["evidence_file"]

    def _offline(self, run: str, command: str, args: dict) -> dict:
        from .citations import citation_audit
        from .licenses import license_report
        from .links import build_link_map
        from .memos import dictionary_index, vocabulary_report
        from .metadata import metadata_audit
        from .terminology import audit_mathematical_terms
        from .vocabulary import vocabulary

        job = self._job(run)
        if command == "license-report":
            _shape(args, {"evidence", "filename"})
            self._read(run, args["evidence"])
            result = license_report(job, args["evidence"], args["filename"])
            provenance = self.store.get("evidence", run + "/" + args["evidence"])
            if (provenance and provenance["kind"] in {"image-info", "license-evidence"}
                    and provenance["sha256"] == result["input"]["sha256"]):
                result.update(origin="broker_pinned_file_metadata",
                              source_api="https://mg.wikipedia.org/w/api.php",
                              captured_at=provenance["at"])
        elif command == "metadata-audit":
            _shape(args, {"evidence"}, {"draft"})
            name = args.get("draft", "draft.wiki")
            self._read(run, name)
            if not isinstance(args["evidence"], list):
                raise StateError("Metadata evidence must name scoped files.")
            for filename in args["evidence"]:
                self._read(run, filename)
            result = metadata_audit(job, args["evidence"], name)
        elif command == "citation-audit":
            _shape(args, set(), {"draft"})
            name = args.get("draft", "draft.wiki")
            self._read(run, "source.wiki")
            self._read(run, name)
            result = citation_audit(job, name)
        elif command == "vocab":
            _shape(args, set(), {"word", "language", "exact"})
            if self.vocabulary_database is None:
                raise StateError("Trusted vocabulary DB not configured; never fetch per run.")
            if type(args.get("exact", False)) is not bool:
                raise StateError("Exact-match flag must be boolean.")
            result = vocabulary(args.get("word"), language=args.get("language", "fr"),
                                exact=args.get("exact", False), cache=self.vocabulary_database)
        elif command == "vocab-audit":
            _shape(args, set(), {"draft"})
            name = args.get("draft", "draft.wiki")
            self._read(run, name)
            if self.vocabulary_database is None:
                raise StateError("Trusted vocabulary database not configured.")
            result = audit_mathematical_terms(job / name, cache=self.vocabulary_database)
        elif command == "coverage":
            _shape(args, set())
            result = workflow.coverage_report(job, job / "draft.wiki")
        elif command == "links-build":
            _shape(args, {"source_language", "evidence"}, {"local_evidence"})
            result = build_link_map(job, args["evidence"], args["source_language"],
                                    local_files=args.get("local_evidence", []))
        elif command == "dictionary-index":
            _shape(args, {"lookups"})
            result = dictionary_index(job, args["lookups"])
        else:
            _shape(args, {"lookups"}, {"vocabulary"})
            result = vocabulary_report(job, args.get("vocabulary", "vocabulary.json"),
                                       args["lookups"])
        return self._evidence_result(run, command, result)

    def _remote(self, run: str, command: str, args: dict) -> dict:
        is_probe = command == "service-probe"
        if command == "service-probe":
            _shape(args, {"service"})
            if args["service"] == "wiki":
                manifest = self._state(run)["manifest"]
                return self.wiki.snapshot(manifest["source_language"], manifest["source_title"])
            if args["service"] == "mgwiki":
                return self.wiki.snapshot("mg", self._state(run)["destination"], sandbox=True)
            if args["service"] != "dictionary":
                raise StateError("Unknown service; no guessed health endpoint.")
            health = self.store.get("health_reads", self._service(run, "dictionary"))
            if health is None:
                # Known read endpoint/word documented in README's dictionary setup evidence.
                # Existing per-word exhaustion remains authoritative; no retry budget reset.
                health = {"edition": "mg", "word": "rano"}
            args, command = {"edition": health["edition"], "word": health["word"]}, "lookup"
        if command == "read":
            _shape(args, {"language", "title"}, {"sandbox"})
            sandbox = args.get("sandbox", False)
            if type(sandbox) is not bool:
                raise StateError("Sandbox flag must be boolean.")
            if (not isinstance(args["language"], str)
                    or not re.fullmatch(r"[a-z]{2,12}(?:-[a-z0-9]{1,12})*", args["language"])):
                raise StateError("Invalid Wikipedia language.")
            core.title(args["title"])
            task = "read-" + hashlib.sha256(encode(args).encode()).hexdigest()[:24]
            service = service_id(f"https://{args['language']}.wikipedia.org/w/api.php")
            self.recovery.register_task(run, task, service)
            self._remember_read(run, task, command, args)
            self._decision(run, Operation.READ_SOURCE, Facts(network=self._network()))
            result = self.wiki.snapshot(args["language"], args["title"], sandbox=sandbox)
            with self.store.transaction() as tx:
                record = tx.get("tasks", run + "/" + task)
                record["status"] = "complete"
                tx.put("tasks", run + "/" + task, record)
            return result
        _shape(args, {"edition", "word"})
        if args["edition"] not in {"en", "mg"}:
            raise StateError("Dictionary edition must be en/mg.")
        args = {"edition": args["edition"], "word": dictionary_word(args["word"])}
        task = "lookup-" + hashlib.sha256(encode(args).encode()).hexdigest()[:24]
        service = self._service(run, "dictionary")
        if not is_probe:
            self.recovery.register_task(run, task, service)
            self._remember_read(run, task, command, args)
        self._decision(run, Operation.LOOKUP_DICTIONARY, Facts(network=self._network()))
        retries = DictionaryRetries(self.gate.path.with_name("dictionary-retries.json"),
                                    clock=self.clock)
        opener = {"opener": self.dictionary_opener} if self.dictionary_opener else {}
        result = core.lookup(args["edition"], args["word"], base_url=self.dictionary_url,
                             retries=retries, **opener)
        filename = f"evidence/{task}-{uuid.uuid4().hex}.json"
        if self._state(run)["initialized"]:
            self._put(run, filename, core.json_bytes(result))
        else:
            intake = self.workspace / "runs" / (run + ".intake")
            intake.mkdir(parents=True, exist_ok=True)
            secure_files.write(intake, filename, core.json_bytes(result))
        with self.store.transaction() as tx:
            tx.put("evidence", run + "/" + filename,
                   {"kind": "lookup", "edition": args["edition"], "status": result["status"],
                    "sha256": core.digest(core.json_bytes(result)), "at": self.clock()}, new=True)
        with self.store.transaction() as tx:
            if result["status"] in {"found", "missing", "no_matching_language"}:
                tx.put("health_reads", service, {"edition": args["edition"], "word": args["word"]})
                record = tx.get("tasks", run + "/" + task)
                if record:
                    record["status"] = "complete"
                    tx.put("tasks", run + "/" + task, record)
        directory = run if self._state(run)["initialized"] else run + ".intake"
        return {**result, "evidence_file": filename, "evidence_base": f"runs/{directory}"}

    def _remember_read(self, run: str, task: str, command: str, args: dict) -> None:
        with self.store.transaction() as tx:
            record = tx.get("tasks", run + "/" + task)
            record["request"] = {"command": command, "arguments": args}
            tx.put("tasks", run + "/" + task, record)

    def _reconcile(self, run: str) -> dict:
        state, attempt = self._state(run), self.store.get("attempts", run)
        facts = Facts(network=self._network(),
                      target=TargetFacts("mg.wikipedia.org", state["destination"], 2),
                      workflow=WorkflowFacts(stage=Stage(state["stage"]),
                                             receipt=ReceiptState.UNCONFIRMED if attempt else None))
        self._decision(run, Operation.RECONCILE_SAVE, facts)
        actual = self.wiki.snapshot("mg", state["destination"], sandbox=True)
        if (actual["sha256"] != attempt["draft_sha256"] or actual["revision_id"] is None
                or actual["revision_id"] == attempt["base_revision"]):
            return {"status": "unconfirmed", "next_action": "retain evidence; do not resubmit"}
        receipt = {"status": "confirmed", "revision_id": actual["revision_id"],
                   "url": actual["url"],
                   "draft_sha256": actual["sha256"], "proposal_digest": attempt["proposal"]}
        with self.store.transaction() as tx:
            attempt.update(status="confirmed", receipt=receipt)
            tx.put("attempts", run, attempt)
            state["stage"] = Stage.CONFIRMED.value
            tx.put("runs", run, state)
            tx.event(self.clock(), "save_reconciled", run, receipt)
        return receipt
