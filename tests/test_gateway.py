"""End-to-end trusted gateway with a fake Wiki. Never contacts Wikimedia/dictionary."""

import copy
import io
import json
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from urllib.error import HTTPError

import pytest

from mgwiki_editor import core, network, secure_files
from mgwiki_editor.broker import Broker, handle
from mgwiki_editor.gateway import Gateway, PolicyBlocked
from mgwiki_editor.network import RequestGate
from mgwiki_editor.policy import Role, RunIntent
from mgwiki_editor.policy_store import PolicyStore, StateError


class MemoryWiki:
    def __init__(self):
        self.pages, self.saves, self.calls = {}, [], []
        self.fail_after_save = False
        self.account = "Bot-Jagwar"
        self.html = "<p>Rano</p>"
        self.put("en", "Water", "Water source.\n\n== History ==\nHistory source.\n", 11)

    def put(self, language, title, text, revision):
        self.pages[language, title] = {
            "language": language, "title": title, "requested_title": title,
            "revision_id": revision, "timestamp": "2026-11-03T10:00:00Z" if revision else None,
            "text": text, "sha256": core.digest(text.encode()),
            "url": f"https://{language}.wikipedia.org/w/index.php?oldid={revision}",
        }

    def snapshot(self, language, title, *, sandbox=False):
        self.calls.append(("snapshot", language, title))
        if (language, title) not in self.pages:
            self.put(language, title, "", None)
        return copy.deepcopy(self.pages[language, title])

    def existing_title(self, language, title, fallback):
        return fallback

    def render(self, destination, text):
        self.calls.append(("render", destination))
        return self.html

    def authenticated_account(self):
        return self.account

    def save(self, destination, text, base, summary):
        self.saves.append((destination, text))
        self.put("mg", destination, text, 99)
        if self.fail_after_save:
            raise OSError("simulated lost response after committed save")


@pytest.fixture
def rig(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    store = PolicyStore(tmp_path / "private-policy.sqlite")
    store.create()
    now = [1000.0]
    wiki = MemoryWiki()
    def advance(seconds):
        now[0] += seconds
    gate = RequestGate(tmp_path / "gate.json", clock=lambda: now[0], sleep=advance,
                       monotonic=lambda: now[0], jitter=lambda *a: 0)
    gateway = Gateway(tmp_path, store, wiki=wiki, clock=lambda: now[0], monotonic=lambda: now[0],
                      boot="test-boot", gate=gate)
    manifest = {"intent": "sandbox_edit", "source_language": "en",
                "source_title": "Water", "article_title": "Rano"}
    token = gateway.provision("water", manifest, expires_at=5000)
    return gateway, store, wiki, token, now


def dispatch(rig, command, **arguments):
    gateway, _, _, token, _ = rig
    return gateway.dispatch(token, command, arguments)["result"]


def assembled(rig):
    gateway, _, _, token, _ = rig
    dispatch(rig, "init")
    dispatch(rig, "plan")
    sections = dispatch(rig, "status")["sections"]
    for section in sections:
        child = dispatch(rig, "assign", role=Role.SECTION_WORKER.value,
                         id=section["id"])["capability"]
        fragment = ("'''Rano''' dia ranoka.\n" if section["id"].startswith("00-") else
                    "== Tantara ==\nMisy tantara izy io.\n")
        for name, content in (("section.wiki", fragment), ("notes.wiki", "Coverage checked.\n"),
                              ("vocabulary.json", "[]")):
            gateway.dispatch(child, "submit", {"name": f"sections/{section['id']}/{name}",
                                                "content": content})
        dispatch(rig, "accept-section", id=section["id"], note="Compared section evidence.")
    dispatch(rig, "assemble")
    return sections


def reviewed(rig):
    assembled(rig)
    dispatch(rig, "review", gates=dict.fromkeys(core.GATES, True),
             note="Actual autonomous checks in this fake fixture, not semantic proof.",
             evidence=["source.wiki", "existing.wiki", "sandbox.wiki", "draft.wiki", "notes.wiki"])


def prepared(rig):
    reviewed(rig)
    proposal = dispatch(rig, "prepare")
    dispatch(rig, "attest-proposal", digest=proposal["digest"],
             note="Inspected fake raw wikitext, preview, diff and references.")
    return proposal


def test_template_info_and_pinned_source_expansion_have_broker_provenance(rig):
    gateway, store, wiki, _, _ = rig
    wiki.put("en", "Water", "{{flag|Example}}\n", 11)
    wiki.template_metadata = lambda titles: {"language": "mg", "titles": titles}
    calls = []
    def expand(language, title, text):
        calls.append((language, title, text))
        return {"expandtemplates": {"wikitext": "[[File:Exact.svg]]"}}
    wiki.expand_template = expand
    dispatch(rig, "init")
    metadata = dispatch(rig, "template-info", titles=["Template:Flag"])
    assert store.get("evidence", "water/" + metadata["evidence_file"])["kind"] == "template-info"
    result = dispatch(rig, "source-expand", index=0)
    assert calls == [("en", "Water", "{{flag|Example}}")]
    assert result["result"]["template"] == "{{flag|Example}}"
    assert store.get("evidence", "water/" + result["evidence_file"])["kind"] == "source-expand"
    for index in (-1, True, 1):
        with pytest.raises(StateError):
            dispatch(rig, "source-expand", index=index)
    with pytest.raises(StateError):
        dispatch(rig, "source-expand", index=0, text="{{arbitrary}}")
    Path("runs/water/source.wiki").write_text("{{tampered}}")
    with pytest.raises(StateError, match="identity changed"):
        dispatch(rig, "source-expand", index=0)
    assert len(calls) == 1 and not wiki.saves


def test_render_check_is_scoped_read_only_before_gates_and_pins_exact_html(rig):
    assembled(rig)
    before = Path("runs/water/review.json").read_bytes()
    result = dispatch(rig, "render-check")
    assert result["result"]["diagnostics"]["valid"]
    assert result["result"]["html"] == rig[2].html
    assert Path("runs/water/review.json").read_bytes() == before
    assert dispatch(rig, "status")["stage"] == "assembled"
    assert not rig[2].saves and not Path("runs/water/proposal.json").exists()
    audit = dispatch(rig, "citation-audit")
    assert audit["result"]["status"] == "review_required"
    metadata = dispatch(rig, "metadata-audit", evidence=[])
    assert metadata["result"]["files"] == []
    assert metadata["result"]["status"] == "review_required"


def test_new_checks_reject_workers_and_render_rejects_incomplete_scope(rig):
    gateway, _, wiki, _, _ = rig
    dispatch(rig, "init")
    with pytest.raises(StateError, match="assembled"):
        dispatch(rig, "render-check")
    dispatch(rig, "plan")
    section = dispatch(rig, "status")["sections"][0]
    child = dispatch(rig, "assign", role=Role.SECTION_WORKER.value,
                     id=section["id"])["capability"]
    count = len(wiki.calls)
    for command in ("render-check", "template-info", "source-expand", "citation-audit",
                    "metadata-audit", "license-evidence", "license-report"):
        with pytest.raises(StateError, match="Coordinator"):
            gateway.dispatch(child, command, {})
    assert len(wiki.calls) == count


def test_frozen_metadata_check_is_denied_before_request(rig):
    prepared(rig)
    rig[2].template_metadata = lambda *a: pytest.fail("Frozen metadata request made")
    with pytest.raises(StateError, match="fresh run"):
        dispatch(rig, "template-info", titles=["Template:Flag"])


def test_live_license_capsule_has_journal_provenance_not_automatic_rights_approval(rig):
    gateway, store, wiki, _, _ = rig
    data = {"query": {"pages": [{"ns": 6, "title": "File:Exact.svg", "imagerepository": "shared",
        "imageinfo": [{"timestamp": "2026-11-10T00:00:00Z", "sha1": "a" * 40,
            "extmetadata": {"LicenseUrl": {"value": "https://creativecommons.org/licenses/by/4.0/"},
                            "Artist": {"value": "Author"}}}]}]}}
    calls = []
    def file_metadata(filename):
        calls.append(filename)
        return copy.deepcopy(data)
    wiki.file_metadata = file_metadata
    dispatch(rig, "init")
    captured = dispatch(rig, "license-evidence", filename="Exact.svg")
    assert calls == ["Exact.svg"]
    assert captured["result"]["origin"] == "broker_image_info_read"
    assert not captured["result"]["license_approved"]
    assert store.get("evidence", "water/" + captured["evidence_file"])["kind"] == "license-evidence"
    cached = dispatch(rig, "license-report", evidence=captured["evidence_file"],
                      filename="Exact.svg")
    assert cached["result"]["origin"] == "broker_pinned_file_metadata"
    assert calls == ["Exact.svg"] and not wiki.saves
    path = Path("runs/water") / captured["evidence_file"]
    changed = json.loads(path.read_bytes())
    changed["unreviewed_change"] = True
    path.write_bytes(core.json_bytes(changed))
    cached = dispatch(rig, "license-report", evidence=captured["evidence_file"],
                      filename="Exact.svg")
    assert cached["result"]["origin"] == "unverified_cached_input"
    assert not cached["result"]["license_approved"]


def test_activation_authenticates_existing_local_broker_scope_without_any_wiki_call(
    tmp_path, monkeypatch,
):
    from mgwiki_editor.activation import activate

    private, work, runtime = (tmp_path / name for name in ("private", "work", "runtime"))
    for path in (private, work, runtime):
        path.mkdir(mode=0o700)
    workspace = private / "workspace"
    workspace.mkdir()
    monkeypatch.chdir(workspace)
    store = PolicyStore(private / "policy.sqlite")
    store.create()
    wiki = MemoryWiki()
    gateway = Gateway(workspace, store, wiki=wiki, clock=lambda: 1000, boot="fake-boot")
    manifest = {"intent": "development", "source_language": "en", "source_title": "Water",
                "article_title": "Rano"}
    token = gateway.provision("fixture", manifest, expires_at=5000)
    secure_files.write(private, "fixture.cap", token.encode())
    socket_path = private / "socket"
    spec = {"work": str(work), "code": str(runtime), "socket": str(socket_path),
            "capability_file": str(private / "fixture.cap"), "private_roots": [str(private)],
            "executable": ["/usr/bin/true"], "run": "fixture", "manifest": manifest,
            "tool_scope": "whole_tool_process"}
    secure_files.write(private, "activation.json", core.json_bytes(spec))
    with Broker(socket_path, gateway) as server:
        worker = threading.Thread(target=server.handle_request)
        worker.start()
        try:
            result = activate(private / "activation.json", check_only=True)
        finally:
            worker.join(timeout=2)
        assert not worker.is_alive()
    assert result["status"] == "authenticated_configuration_checked_not_launched"
    assert wiki.calls == wiki.saves == []
    assert token not in json.dumps(result)


def test_complete_manifest_sections_review_proposal_save_and_readback(rig):
    gateway, store, wiki, token, _ = rig
    proposal = prepared(rig)
    result = dispatch(rig, "publish")
    assert result["status"] == "confirmed"
    assert result["proposal_digest"] == proposal["digest"]
    assert len(wiki.saves) == 1
    assert store.get("attempts", "water")["status"] == "confirmed"
    assert dispatch(rig, "status")["stage"] == "confirmed"
    assert core.read_json(Path("runs/water/proposal.json"))["artifacts"]["editorial-state.json"]
    assert token.encode() not in store.path.read_bytes()
    with pytest.raises(PolicyBlocked):
        dispatch(rig, "publish")
    assert len(wiki.saves) == 1
    store.verify()


def test_source_issues_remain_nonblocking_but_unknown_meaning_blocks(rig):
    assembled(rig)
    dispatch(rig, "record-issue", id="SRC-1", kind="source", blocking=False,
             details="Pinned source claims conflict: first claim [ref1], second claim [ref2].",
             claims=[{"claim": "first claim", "citation": "ref1"},
                     {"claim": "second claim", "citation": "ref2"}],
             handling="Retain both accounts with attribution/uncertainty.",
             next_action="Later review; retain attribution/uncertainty.", evidence=["source.wiki"])
    dispatch(rig, "review", gates=dict.fromkeys(core.GATES, True), note="Accounts faithful.",
             evidence=["source.wiki", "source-issues.md", "draft.wiki"])
    assert dispatch(rig, "prepare")["digest"]
    # New material issue after preparation cannot be hidden in immutable proposal snapshot.
    dispatch(rig, "record-issue", id="MEANING-1", kind="meaning", blocking=True,
             details="Material meaning unknown.", next_action="Resolve from pinned evidence.",
             evidence=["source.wiki"])
    with pytest.raises(PolicyBlocked):
        dispatch(rig, "publish")
    assert not rig[2].saves


@pytest.mark.parametrize("intent", [RunIntent.DRAFT_ONLY.value, RunIntent.DEVELOPMENT.value])
def test_trusted_nonpublishing_intent_cannot_be_promoted_by_editable_inputs(rig, intent):
    gateway, store, wiki, _, _ = rig
    with store.transaction() as tx:
        state = tx.get("runs", "water")  # Trusted launcher fixture, never agent RPC.
        state["intent"] = intent
        tx.put("runs", "water", state)
    prepared(rig)
    response = handle(gateway, {"schema": 1, "capability": rig[3], "command": "publish",
                                "arguments": {"intent": "sandbox_edit"}})
    assert response["ok"] is False
    with pytest.raises(PolicyBlocked):
        dispatch(rig, "publish")
    assert not wiki.saves


def test_missing_sections_and_unaccepted_fragments_block_completion(rig):
    dispatch(rig, "init")
    dispatch(rig, "plan")
    with pytest.raises(StateError, match="unaccepted"):
        dispatch(rig, "assemble")
    with pytest.raises(PolicyBlocked):
        dispatch(rig, "prepare")


def test_cannot_publish_before_exact_post_prepare_proposal_review(rig):
    reviewed(rig)
    dispatch(rig, "prepare")
    with pytest.raises(PolicyBlocked):
        dispatch(rig, "publish")
    assert not rig[2].saves


def test_changed_input_invalidates_review_and_never_sets_gate_automatically(rig):
    reviewed(rig)
    path = Path("runs/water/draft.wiki")
    old = core.digest(path.read_bytes())
    dispatch(rig, "submit", name="draft.wiki", content="'''Rano''' dia ranoka hafa.\n",
             expected_sha256=old)
    assert dispatch(rig, "status")["stage"] == "assembled"
    with pytest.raises(PolicyBlocked):
        dispatch(rig, "prepare")
    assert not rig[2].saves


def test_uncertain_save_cannot_replay_even_after_receipt_deleted_but_can_reconcile(rig):
    gateway, store, wiki, token, now = rig
    prepared(rig)
    wiki.fail_after_save = True
    with pytest.raises(OSError):
        dispatch(rig, "publish")
    Path("runs/water/receipt.json").unlink()  # Simulated attack outside isolated deployment.
    restarted = Gateway(gateway.workspace, store, wiki=wiki, clock=lambda: now[0],
                        monotonic=lambda: now[0], boot="test-boot", gate=gateway.gate)
    with pytest.raises(PolicyBlocked):
        restarted.dispatch(token, "publish", {})
    assert len(wiki.saves) == 1
    result = restarted.dispatch(token, "reconcile", {})["result"]
    assert result["status"] == "confirmed"
    assert store.get("attempts", "water")["status"] == "confirmed"
    assert len(wiki.saves) == 1


def test_new_live_revision_blocks_before_claim_and_save(rig):
    prepared(rig)
    rig[2].put("en", "Water", "Changed source", 12)
    with pytest.raises(PolicyBlocked):
        dispatch(rig, "publish")
    assert rig[1].get("attempts", "water") is None
    assert not rig[2].saves


def test_wrong_account_or_changed_render_denied_without_claim(rig):
    prepared(rig)
    rig[2].account = "Other"
    with pytest.raises(PolicyBlocked):
        dispatch(rig, "publish")
    rig[2].account = "Bot-Jagwar"
    rig[2].html = "<p>Changed</p>"
    with pytest.raises(PolicyBlocked):
        dispatch(rig, "publish")
    assert rig[1].get("attempts", "water") is None
    assert not rig[2].saves


def test_worker_capability_bound_to_exact_assignment_no_shared_writes_or_remote_operations(rig):
    gateway = rig[0]
    dispatch(rig, "init")
    dispatch(rig, "plan")
    sections = dispatch(rig, "status")["sections"]
    assigned = sections[0]["id"]
    child = dispatch(rig, "assign", role="section_worker", id=assigned)["capability"]
    forbidden = ["draft.wiki", "review.json", "job.json", "../outside",
                 f"sections/{sections[1]['id']}/section.wiki", f"sections/{assigned}/source.wiki"]
    for name in forbidden:
        with pytest.raises(StateError):
            gateway.dispatch(child, "submit", {"name": name, "content": "changed"})
    for action in (
        "read", "lookup", "accept-section", "assign", "publish", "review", "record-issue",
    ):
        with pytest.raises(StateError, match="Coordinator"):
            gateway.dispatch(child, action, {})
    dispatch(rig, "revoke-assignment", id=assigned)
    with pytest.raises(StateError, match="revoked"):
        gateway.dispatch(child, "artifact", {"name": "source.wiki"})


def test_issue_solver_proposal_requires_coordinator_acceptance_and_local_evidence(rig):
    gateway = rig[0]
    dispatch(rig, "init")
    dispatch(rig, "record-issue", id="ISSUE-1", kind="meaning", blocking=True,
             details="Sense unresolved.", next_action="Review local source context.",
             evidence=["source.wiki"])
    child = dispatch(rig, "assign", role="issue_solver", id="ISSUE-1")["capability"]
    gateway.dispatch(child, "submit", {"name": "issue-resolutions/ISSUE-1.md",
                                       "content": "Pinned context supports descriptive wording.\n"})
    assert gateway.issues.blockers("water") == ("ISSUE-1",)
    with pytest.raises(StateError, match="Coordinator"):
        gateway.dispatch(child, "accept-issue", {})
    dispatch(rig, "accept-issue", id="ISSUE-1", note="Context/evidence reviewed; wording resolved.",
             evidence=["source.wiki"])
    assert gateway.issues.blockers("water") == ()
    assert dispatch(rig, "status")["stage"] != "reviewed"
    memo = Path("runs/water/deferred-issues.md").read_text()
    assert "issue_recorded" in memo and "issue_resolved" in memo


def test_no_admin_raw_http_shell_or_cross_run_surface_and_expiry(rig):
    gateway, _, wiki, token, now = rig
    for action in ("provision", "create", "execute", "eval", "http", "delete", "move"):
        response = handle(gateway, {"schema": 1, "capability": token, "command": action,
                                    "arguments": {}})
        assert response["ok"] is False
    assert not wiki.calls
    with pytest.raises(StateError):
        gateway.dispatch("forged" * 10, "status", {})
    now[0] = 5000
    with pytest.raises(StateError, match="expired"):
        gateway.dispatch(token, "status", {})


def test_existing_jobs_never_adopted_and_failed_init_keeps_separate_memo(rig, monkeypatch):
    gateway, _, wiki, _, _ = rig
    def failed(*args, **kwargs):
        raise OSError("fake source outage")
    monkeypatch.setattr(wiki, "snapshot", failed)
    with pytest.raises(OSError):
        dispatch(rig, "init")
    memo = Path("runs/water.intake/deferred-issues.md")
    assert memo.exists()
    assert "operation_failed" in memo.read_text()
    assert not Path("runs/water/job.json").exists()
    monkeypatch.undo()
    # cwd monkeypatch also undone; restore explicitly for the local gateway fixture.
    monkeypatch.chdir(gateway.workspace)
    Path("runs/water").mkdir()
    with pytest.raises(core.GuardError, match="already exists"):
        dispatch(rig, "init")


def test_broker_envelope_rejects_forged_role_or_schema(rig):
    gateway, _, _, token, _ = rig
    for extra in ({"role": "coordinator"}, {"schema": True}, {"schema": 2}):
        envelope = {"schema": 1, "capability": token, "command": "status", "arguments": {}}
        envelope.update(extra)
        assert handle(gateway, envelope)["ok"] is False


def test_real_fake_transport_probes_skip_26_and_alert_without_counting_probes(rig, monkeypatch):
    gateway, store, _, _, now = rig
    dispatch(rig, "init")
    calls = []
    class Restarting:
        def open(self, request, timeout):
            calls.append(request.full_url)
            raise HTTPError(request.full_url, 502, "restart", {}, io.BytesIO(b"service restarting"))
    monkeypatch.setattr(network, "build_opener", lambda *a: Restarting())
    # Uses real guarded dictionary adapter with fake urllib; no sockets/external services.
    first = dispatch(rig, "lookup", edition="en", word="term-0")
    assert first["status"] == "failed"
    for number in range(1, 26):
        with pytest.raises(PolicyBlocked):
            dispatch(rig, "lookup", edition="en", word=f"term-{number}")
    with store.transaction() as tx:
        tasks = [value["id"] for _, value in tx.rows("tasks")
                 if value["service"].startswith("dictionary:")]
    assert len(tasks) == 26 and len(calls) == 1
    now[0] = 1600
    probe = dispatch(rig, "service-probe", service="dictionary")
    assert probe["probe_observed"] is True
    result = dispatch(rig, "skip", service="dictionary", tasks=tasks)
    assert result["distinct_count"] == 26
    assert gateway.recovery.alerts("water") == []
    now[0] = 1615
    dispatch(rig, "service-probe", service="dictionary")
    assert len(calls) == 3
    alert = gateway.recovery.alerts("water")[0]
    assert "runs/water/deferred-issues.md" in alert["text"]
    memo = Path("runs/water/deferred-issues.md").read_text()
    assert "http_observation" in memo and "tasks_skipped" in memo
    with store.transaction() as tx:
        assert len([value for _, value in tx.rows("tasks")
                    if value["service"].startswith("dictionary:")]) == 26


def test_offline_worker_proxy_import_enforces_child_scope(rig):
    dispatch(rig, "init")
    dispatch(rig, "plan")
    ident = dispatch(rig, "status")["sections"][0]["id"]
    child = dispatch(rig, "assign", role="section_worker", id=ident)["capability"]
    dispatch(rig, "submit-assigned", worker_capability=child,
             name=f"sections/{ident}/section.wiki", content="'''Rano''' dia ranoka.\n")
    with pytest.raises(StateError):
        dispatch(rig, "submit-assigned", worker_capability=child,
                 name="review.json", content="{}")
    assert any(event["kind"] == "worker_artifact_imported_by_coordinator"
               for event in rig[1].events("water"))


def test_artifact_chunks_preserve_exact_bytes_and_report_coverage(rig):
    dispatch(rig, "init")
    raw = Path("runs/water/source.wiki").read_bytes()
    chunks = []
    offset = 1
    while offset is not None:
        result = dispatch(rig, "artifact", name="source.wiki", offset=offset, limit=1)
        chunks.append(result["content"])
        assert result["sha256"] == core.digest(raw)
        offset = result["next_offset"]
    assert "".join(chunks).encode() == raw


def test_resume_cannot_replay_writes_or_invent_tasks(rig):
    dispatch(rig, "init")
    with pytest.raises(StateError, match="idempotent"):
        dispatch(rig, "resume", task="publish")
    dispatch(rig, "read", language="en", title="Water")
    with rig[1].transaction() as tx:
        task = next(value for _, value in tx.rows("tasks") if value["id"].startswith("read-"))
    assert dispatch(rig, "resume", task=task["id"])["status"] == "already_complete"


def test_lookup_intake_evidence_is_pinned_without_fabricating_job_then_inherited(rig):
    rig[0].dictionary_opener = lambda *a, **k: io.BytesIO(
        b'[{"language":"en","definitions":["sense"]}]')
    result = dispatch(rig, "lookup", edition="en", word="water")
    path = Path(result["evidence_base"]) / result["evidence_file"]
    before = path.read_bytes()
    assert not Path("runs/water/job.json").exists()
    initialized = dispatch(rig, "init")
    assert len(initialized["intake_evidence"]) == 1
    assert Path("runs/water", initialized["intake_evidence"][0]).read_bytes() == before
    assert path.read_bytes() == before


def term_record(**updates):
    record = {"source_term": "technical concept", "source_language": "en", "domain": "physics",
              "source_sense": "Source-specific sense.", "english_definition": "A clear concept.",
              "definition_origin": "editorial_simple_english",
              "malagasy_definition": "Hevitra mazava.",
              "chosen_expression": "hevitra", "reason": "Context reviewed; accurate description.",
              "status": "descriptive", "evidence_files": ["source.wiki"]}
    return {**record, **updates}


def set_vocabulary(rig, records):
    path = Path("runs/water/vocabulary.json")
    dispatch(rig, "submit", name="vocabulary.json", content=json.dumps(records),
             expected_sha256=core.digest(path.read_bytes()))


def test_failed_dictionary_never_blocks_accurate_reviewed_descriptive_vocabulary(rig):
    assembled(rig)
    set_vocabulary(rig, [term_record()])
    dispatch(rig, "review", gates=dict.fromkeys(core.GATES, True), note="Definition checked.",
             evidence=["source.wiki", "draft.wiki", "vocabulary.json"])
    assert dispatch(rig, "prepare")["digest"]


@pytest.mark.parametrize("record", [term_record(status="verified"),
                                    term_record(definition_origin="dictionary"),
                                    term_record(domain="mathematics")])
def test_no_fabricated_dictionary_verification_or_unsupported_math_lookup(rig, record):
    assembled(rig)
    set_vocabulary(rig, [record])
    with pytest.raises(StateError):
        dispatch(rig, "review", gates=dict.fromkeys(core.GATES, True), note="Provenance missing.",
                 evidence=["source.wiki"])


def test_101_uncertain_terms_generate_linked_memory_without_losing_definitions(rig):
    assembled(rig)
    records = [term_record(source_term=f"concept {index}") for index in range(101)]
    set_vocabulary(rig, records)
    dispatch(rig, "review", gates=dict.fromkeys(core.GATES, True), note="All descriptions checked.",
             evidence=["source.wiki", "vocabulary.json"])
    memo = Path("runs/water/unknown-vocabulary.wiki").read_text()
    assert "concept 100" in memo and "Hevitra mazava." in memo
    updated = core.read_json(Path("runs/water/vocabulary.json"))
    assert all("unknown-vocabulary.wiki" in record["evidence_files"] for record in updated)
    assert all(record["english_definition"] == "A clear concept." for record in updated)
    assert "unknown-vocabulary.wiki" in dispatch(rig, "prepare")["artifacts"]


def test_changed_referenced_review_evidence_is_not_hidden_behind_snapshot_hash(rig):
    assembled(rig)
    dispatch(rig, "submit", name="evidence/review.txt", content="Original exact review evidence.")
    dispatch(rig, "review", gates=dict.fromkeys(core.GATES, True), note="Evidence inspected.",
             evidence=["source.wiki", "evidence/review.txt"])
    path = Path("runs/water/evidence/review.txt")
    path.write_text("Simulated tampering outside broker isolation.")
    with pytest.raises(PolicyBlocked):
        dispatch(rig, "prepare")
    assert not rig[2].saves


def test_after_publication_issue_solver_can_work_later_without_reopening_save(rig):
    prepared(rig)
    dispatch(rig, "publish")
    dispatch(rig, "record-issue", id="LATER-1", kind="vocabulary_preference", blocking=False,
             details="Later terminology review.", next_action="Compare pinned context.",
             evidence=["source.wiki"])
    child = dispatch(rig, "assign", role="issue_solver", id="LATER-1")["capability"]
    rig[0].dispatch(child, "submit", {"name": "issue-resolutions/LATER-1.md",
                                      "content": "Proposal only.\n"})
    dispatch(rig, "accept-issue", id="LATER-1", note="Context confirmed; no automatic edit.",
             evidence=["source.wiki"])
    assert dispatch(rig, "status")["stage"] == "confirmed"
    assert len(rig[2].saves) == 1
    with pytest.raises(PolicyBlocked):
        dispatch(rig, "publish")


def test_artifact_versions_retained_and_scoped_and_renewal_never_changes_intent(rig):
    dispatch(rig, "init")
    old = dispatch(rig, "artifact", name="notes.wiki")
    dispatch(rig, "submit", name="notes.wiki", content="Updated notes.\nSecond line.\n",
             expected_sha256=old["sha256"])
    archived = dispatch(rig, "artifact-history", name="notes.wiki", sha256=old["sha256"])
    assert archived["content"] == old["content"]
    with pytest.raises(StateError):
        dispatch(rig, "artifact-history", name="notes.wiki", sha256="unknown")
    rig[4][0] = 5000
    new = rig[0].renew("water", expires_at=6000)
    result = rig[0].dispatch(new, "status", {})["result"]
    assert result["intent"] == "sandbox_edit"
    assert result["stage"] == "pinned"


def test_source_image_omission_cannot_be_hidden_by_true_review_booleans(rig):
    rig[2].put("en", "Water", "Source.\n[[File:Example.jpg|Original caption.]]\n", 11)
    assembled(rig)
    with pytest.raises(StateError, match="omissions"):
        dispatch(rig, "review", gates=dict.fromkeys(core.GATES, True), note="Image omitted.",
                 evidence=["source.wiki"])
    dispatch(rig, "review", gates=dict.fromkeys(core.GATES, True), note="Scope/license checked.",
             evidence=["source.wiki"],
             omissions={"images": {"Example.jpg": "Fake unavailable-file evidence."}})
    assert dispatch(rig, "prepare")["digest"]


def test_unverified_new_category_rejected_and_existing_category_preserved(rig):
    rig[2].put("mg", "Rano", "Existing.\n[[Sokajy:Rano|Sort key]]\n", 7)
    assembled(rig)
    with pytest.raises(StateError, match="category"):
        dispatch(rig, "review", gates=dict.fromkeys(core.GATES, True), note="Category dropped.",
                 evidence=["existing.wiki"])
    old = dispatch(rig, "artifact", name="draft.wiki")
    dispatch(rig, "submit", name="draft.wiki", expected_sha256=old["sha256"],
             content=old["content"] + "\n[[Sokajy:Rano|Sort key]]\n[[Sokajy:Guessed]]\n")
    with pytest.raises(StateError, match="categories"):
        dispatch(rig, "review", gates=dict.fromkeys(core.GATES, True), note="Unverified addition.",
                 evidence=["existing.wiki"])


def test_verified_category_allows_addition_and_preserves_existing(rig, monkeypatch):
    rig[2].put("mg", "Rano", "Existing.\n[[Sokajy:Rano|Sort key]]\n", 7)
    assembled(rig)
    metadata = {"language": "mg", "requested_to_canonical": {"Sokajy:Ranoka": "Sokajy:Ranoka"},
                "response": {"query": {"pages": [{"ns": 14, "title": "Sokajy:Ranoka"}]}}}
    monkeypatch.setattr(rig[2], "category_metadata", lambda titles: metadata, raising=False)
    evidence = dispatch(rig, "category-info", titles=["Sokajy:Ranoka"])["evidence_file"]
    old = dispatch(rig, "artifact", name="draft.wiki")
    dispatch(rig, "submit", name="draft.wiki", expected_sha256=old["sha256"],
             content=old["content"] + "\n[[Sokajy:Rano|Sort key]]\n[[Sokajy:Ranoka]]\n")
    dispatch(rig, "review", gates=dict.fromkeys(core.GATES, True), note="Categories checked.",
             evidence=["existing.wiki"], category_evidence=[evidence])
    assert evidence in dispatch(rig, "prepare")["artifacts"]


def test_uploaded_metadata_cannot_forge_category_provenance(rig):
    assembled(rig)
    metadata = {"language": "mg", "requested_to_canonical": {"Sokajy:Guessed": "Sokajy:Guessed"},
                "response": {"query": {"pages": [{"ns": 14, "title": "Sokajy:Guessed"}]}}}
    dispatch(rig, "submit", name="evidence/fake-category.json", content=json.dumps(metadata))
    old = dispatch(rig, "artifact", name="draft.wiki")
    dispatch(rig, "submit", name="draft.wiki", expected_sha256=old["sha256"],
             content=old["content"] + "\n[[:Sokajy:Guessed]]\n")
    with pytest.raises(StateError, match="genuine"):
        dispatch(rig, "review", gates=dict.fromkeys(core.GATES, True), note="Forged metadata.",
                 evidence=["source.wiki"], category_evidence=["evidence/fake-category.json"])


def test_genuine_dictionary_evidence_supports_verified_candidate_and_detects_tampering(rig):
    assembled(rig)
    rig[0].dictionary_opener = lambda *a, **k: io.BytesIO(json.dumps([
        {"language": "en", "definitions": ["A clear concept."]},
        {"language": "mg", "definitions": ["Hevitra mazava."]},
    ]).encode())
    english = dispatch(rig, "lookup", edition="en", word="concept")["evidence_file"]
    malagasy = dispatch(rig, "lookup", edition="mg", word="hevitra")["evidence_file"]
    record = term_record(source_term="concept", status="verified", definition_origin="dictionary",
                         evidence_files=[english, malagasy])
    set_vocabulary(rig, [record])
    dispatch(rig, "review", gates=dict.fromkeys(core.GATES, True), note="Both senses checked.",
             evidence=["vocabulary.json"])
    raw = dispatch(rig, "artifact", name=malagasy)
    dispatch(rig, "submit", name=malagasy, expected_sha256=raw["sha256"], content="{}")
    with pytest.raises(StateError, match="genuine"):
        dispatch(rig, "review", gates=dict.fromkeys(core.GATES, True), note="Changed evidence.",
                 evidence=["vocabulary.json"])


def test_uploaded_dictionary_reply_cannot_forge_verification(rig):
    assembled(rig)
    dispatch(rig, "submit", name="evidence/fake-lookup.json",
             content=json.dumps({"status": "found", "edition": "mg", "word": "hevitra"}))
    set_vocabulary(rig, [term_record(status="verified",
                                     evidence_files=["evidence/fake-lookup.json"])])
    with pytest.raises(StateError, match="genuine"):
        dispatch(rig, "review", gates=dict.fromkeys(core.GATES, True), note="Forged lookup.",
                 evidence=["vocabulary.json"])


def test_math_query_evidence_pins_database_hash_and_survives_reassembly(rig):
    rig[0].vocabulary_database = (
        Path(__file__).resolve().parents[1] / "data/vocabulary/kajy-mathematics.sqlite")
    assembled(rig)
    query = dispatch(rig, "vocab", word="équation", language="fr", exact=True)
    assert query["result"]["database_sha256"]
    assert query["result"]["entries"][0]["source_number"] == 102
    record = term_record(source_term="equation", domain="mathematics",
                         chosen_expression="fampimirana", evidence_files=[query["evidence_file"]])
    set_vocabulary(rig, [record])
    dispatch(rig, "assemble")
    saved = core.read_json(Path("runs/water/vocabulary.json"))
    assert saved[0]["chosen_expression"] == "fampimirana"
    dispatch(rig, "review", gates=dict.fromkeys(core.GATES, True), note="Sense bridge checked.",
             evidence=["vocabulary.json"])
    assert query["evidence_file"] in dispatch(rig, "prepare")["artifacts"]


def test_unicode_source_section_ids_and_explicit_local_only_section_workers(rig):
    rig[2].put("en", "Water", "Lead.\n\n== Équation ==\nSource.\n", 11)
    rig[2].put("mg", "Rano", "== Fanampiny ==\nHevitra voatahiry.\n", 7)
    source_sections = assembled(rig)
    assert any("équation" in section["id"] for section in source_sections)
    dispatch(rig, "plan-local", id="local-fanampiny", source="existing", start=1, end=2,
             after=source_sections[0]["id"])
    child = dispatch(rig, "assign", role="section_worker", id="local-fanampiny")["capability"]
    for filename, content in (("section.wiki", "== Fanampiny ==\nHevitra voatahiry.\n"),
                              ("notes.wiki", "Sourced local contribution retained.\n"),
                              ("vocabulary.json", "[]")):
        rig[0].dispatch(child, "submit", {"name": "sections/local-fanampiny/" + filename,
                                         "content": content})
    dispatch(rig, "accept-section", id="local-fanampiny", note="Local evidence reviewed.")
    dispatch(rig, "assemble")
    text = Path("runs/water/draft.wiki").read_text()
    assert text.index("Fanampiny") < text.index("Tantara")
    dispatch(rig, "review", gates=dict.fromkeys(core.GATES, True), note="Source/local checked.",
             evidence=["existing.wiki"])
    assert dispatch(rig, "prepare")["digest"]


def test_isolated_worker_cannot_read_secrets_mutate_code_fetch_or_escape_assignment(
    rig, tmp_path_factory,
):
    if shutil.which("bwrap") is None:
        pytest.skip("bubblewrap unavailable; hard-isolation guarantee not verified")
    gateway, _, _, _, _ = rig
    dispatch(rig, "init")
    dispatch(rig, "plan")
    ident = dispatch(rig, "status")["sections"][0]["id"]
    child = dispatch(rig, "assign", role="section_worker", id=ident)["capability"]
    capfile = gateway.workspace / "worker.cap"
    secure_files.write(gateway.workspace, capfile.name, child.encode())
    secret = gateway.workspace / "fake-private-secret"
    secret.write_text("FAKE TEST SECRET — never real credentials", encoding="utf-8")
    staging = tmp_path_factory.mktemp("isolated-agent")
    code, work = staging / "code", staging / "work"
    package = code / "mgwiki_editor"
    package.mkdir(parents=True)
    work.mkdir()
    root = Path(__file__).resolve().parents[1]
    for filename in ("__init__.py", "broker.py", "policy_store.py", "secure_files.py",
                     "control.py", "isolation.py"):
        (package / filename).write_bytes((root / "mgwiki_editor" / filename).read_bytes())
    entry = ("import sys,runpy;sys.path.insert(0," + repr(str(root)) + ");"
             "runpy.run_module('mgwiki_editor.control',run_name='__main__')")
    launcher = [sys.executable, "-I", "-c", entry]
    probe = subprocess.run(launcher + ["sandbox-check", "--work", str(work), "--code", str(code)],
                           capture_output=True, timeout=15, check=False)
    assert probe.returncode == 0, probe.stderr.decode()
    result = json.loads(probe.stdout)
    if not result["available"]:
        pytest.skip("Local isolation unavailable: " + result["details"])
    socket_path = gateway.workspace / "broker.sock"
    host_net = os.stat("/proc/self/ns/net").st_ino
    script = f"""
import errno, os, pathlib, socket, subprocess, sys
sys.path.insert(0, '/app')
from mgwiki_editor.broker import call, capability_file
assert not pathlib.Path({str(secret)!r}).exists()
assert not pathlib.Path('/proc/1/root' + {str(secret)!r}).exists()
assert os.stat('/proc/self/ns/net').st_ino != {host_net}
assert set(name for _, name in socket.if_nameindex()) <= {{'lo'}}
try:
    open('/app/mgwiki_editor/broker.py', 'wb')
except OSError as error:
    assert error.errno == errno.EROFS
else:
    raise AssertionError('trusted code writable')
token = capability_file(pathlib.Path('/run/mgwiki/capability'))
def request(command, arguments):
    return call(pathlib.Path('/run/mgwiki/broker.sock'), token, command, arguments)
assert request('artifact', {{'name':'source.wiki'}})['ok']
assert not request('artifact', {{'name':'../fake-private-secret'}})['ok']
assert not request('submit', {{'name':'review.json','content':'{{}}'}})['ok']
assert not request('submit', {{'name':'sections/other/section.wiki','content':'escape'}})['ok']
assert not request('lookup', {{'edition':'en','word':'secret'}})['ok']
assert not request('publish', {{}})['ok']
assert not request('provision', {{}})['ok']
submitted = request('submit', {{'name':{f'sections/{ident}/section.wiki'!r},'content':'fixture'}})
assert submitted['ok']
print('isolated-gateway-adversarial-ok')
"""
    with Broker(socket_path, gateway) as server:
        worker = threading.Thread(target=server.serve_forever)
        worker.start()
        try:
            result = subprocess.run(launcher + [
                "sandbox-run", "--work", str(work), "--code", str(code),
                "--socket", str(socket_path), "--capability-file", str(capfile),
                "--private-root", str(gateway.workspace), "--",
                "/usr/bin/python3", "-I", "-c", script,
            ], capture_output=True, timeout=30, check=False)
        finally:
            server.shutdown()
            worker.join(timeout=2)
    assert result.returncode == 0, result.stderr.decode()
    assert "isolated-gateway-adversarial-ok" in result.stdout.decode()
    assert secret.read_text(encoding="utf-8").startswith("FAKE TEST SECRET")
    assert not rig[2].saves
