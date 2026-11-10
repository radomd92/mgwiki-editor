"""Structured issue history and non-destructive human-readable memo projections."""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from pathlib import Path

from . import secure_files
from .policy_store import PolicyStore, StateError, encode, identifier

KINDS = {"source", "vocabulary_preference", "service", "meaning", "safety", "copyright",
         "citations", "identity", "technical"}


class Issues:
    def __init__(
        self, store: PolicyStore, workspace: Path, *, clock: Callable[[], float] = time.time,
    ) -> None:
        self.store, self.workspace, self.clock = store, Path(workspace), clock

    def evidence(self, run: str, names: list[str]) -> dict[str, str]:
        if not isinstance(names, list) or not names or any(not isinstance(n, str) for n in names):
            raise StateError("Issue/review evidence must name existing pinned local files.")
        root = self.workspace / "runs" / identifier(run)
        return {name: hashlib.sha256(secure_files.read(root, name)).hexdigest() for name in names}

    def record(
        self, run: str, issue: str, *, kind: str, details: str, next_action: str,
        blocking: bool, evidence: list[str], section: str | None = None,
        claims: list[dict] | None = None, handling: str | None = None,
    ) -> dict:
        key = identifier(run) + "/" + identifier(issue)
        if kind not in KINDS or type(blocking) is not bool:
            raise StateError("Invalid issue kind/blocking status.")
        if not details.strip() or not next_action.strip() or len(details) > 100_000:
            raise StateError("Issue needs bounded exact details and next action.")
        if kind in {"source", "vocabulary_preference"} and blocking:
            raise StateError("Source disagreement/preferred label alone is nonblocking.")
        if kind not in {"source", "vocabulary_preference", "service"} and not blocking:
            raise StateError("Material meaning/safety/integrity issues remain blockers.")
        if kind == "source":
            if (not isinstance(claims, list) or len(claims) < 2
                    or not handling or not handling.strip()
                    or any(not isinstance(claim, dict) or set(claim) != {"claim", "citation"}
                           or any(not isinstance(value, str) or not value.strip()
                                  for value in claim.values()) for claim in claims)):
                raise StateError("Source issue needs claims, citations and draft handling.")
        if section is not None:
            identifier(section)
        pinned = self.evidence(run, evidence) if evidence else {}
        state = self.store.get("runs", run)
        source = None
        if state and state.get("initialized"):
            raw = secure_files.read(self.workspace / "runs" / run, "job.json")
            source = json.loads(raw)["source"]
        with self.store.transaction() as tx:
            previous = tx.get("issues", key)
            if previous is not None:
                raise StateError("Issue ID exists; retain history and resolve explicitly.")
            value = {"run": run, "id": issue, "kind": kind, "status": "open",
                     "details": details, "next_action": next_action, "blocking": blocking,
                     "evidence": pinned, "section": section, "created_at": self.clock()}
            value.update(article=state["manifest"]["article_title"] if state else None,
                         source_revision=source["revision_id"] if source else None,
                         source_path="source.wiki" if source else None,
                         claims=claims, handling=handling)
            tx.put("issues", key, value, new=True)
            tx.event(self.clock(), "issue_recorded", run, value)
        self.project(run)
        return value

    def resolve(self, run: str, issue: str, *, note: str, evidence: list[str]) -> dict:
        pinned = self.evidence(run, evidence)
        if not note.strip():
            raise StateError("Coordinator resolution rationale required.")
        key = identifier(run) + "/" + identifier(issue)
        with self.store.transaction() as tx:
            value = tx.get("issues", key)
            if value is None or value["status"] != "open":
                raise StateError("Open assigned issue required.")
            value.update(status="resolved", resolved_at=self.clock(), resolution=note,
                         resolution_evidence=pinned)
            tx.put("issues", key, value)
            tx.event(self.clock(), "issue_resolved", run, value)
        self.project(run)
        return value

    def list(self, run: str) -> list[dict]:
        with self.store.transaction() as tx:
            return [value for _, value in tx.rows("issues") if value["run"] == run]

    def blockers(self, run: str) -> tuple[str, ...]:
        return tuple(value["id"] for value in self.list(run)
                     if value["status"] == "open" and value["blocking"])

    def project(self, run: str) -> str:
        """Append event snapshots; never overwrite legacy prose or erase history on resume."""
        run = identifier(run)
        state = self.store.get("runs", run)
        directory = run if state and state.get("initialized") else run + ".intake"
        root = self.workspace / "runs" / directory
        root.mkdir(parents=True, exist_ok=True)
        with self.store.transaction() as tx:
            services = {service for _, task in tx.rows("tasks") if task["run"] == run
                        for service in task.get("services", [task["service"]])}
        events = [event for event in self.store.events()
                  if event["scope"] == run or event["scope"] in services]
        for filename, source_only in (("deferred-issues.md", False), ("source-issues.md", True)):
            try:
                original = secure_files.read(root, filename)
                exists = True
            except FileNotFoundError:
                original = b""
                exists = False
            content = original if exists else f"# {filename}\n".encode()
            for event in events:
                payload = event["payload"]
                is_source = payload.get("kind") == "source"
                relevant = event["kind"] in {"issue_recorded", "issue_resolved", "operation_failed",
                                              "tasks_skipped", "service_deferred",
                                              "http_observation",
                                              "task_registered", "task_dependency_added",
                                              "outage_alert_queued"}
                if not relevant or (source_only != is_source):
                    continue
                marker = f"<!-- policy-event:{event['seq']} -->".encode()
                if marker not in content:
                    # Markdown memory, exact JSON evidence. Marker is inert, not article markup.
                    content += (b"\n\n" + marker + b"\n" +
                                f"## {event['kind']} — {event['at']}\n\n".encode() +
                                encode(payload).encode() + b"\n")
            if content != original:
                expected = hashlib.sha256(original).hexdigest() if exists else None
                secure_files.write(root, filename, content, expected=expected)
        return f"runs/{directory}/deferred-issues.md"
