"""Lean views preserve original evidence and guards; all fixtures offline."""

from __future__ import annotations

import json

import pytest

from mgwiki_editor import batching, cli
from mgwiki_editor.batching import evidence_pin, evidence_verify, lookup_batch, offline_audit
from mgwiki_editor.core import GuardError, artifact_hashes, digest, json_bytes, write_json
from mgwiki_editor.memos import pack_vocabulary, vocabulary_view
from mgwiki_editor.slicing import json_slice
from mgwiki_editor.usage import session_usage


@pytest.fixture
def job(tmp_path):
    (tmp_path / "source.wiki").write_text("Pinned evidence.", encoding="utf-8")
    rows = [{"source_term": "term", "source_language": "en", "source_sense": sense,
             "domain": "domain", "section_id": section, "status": status,
             "chosen_expression": "Safidy", "english_definition": "Definition.",
             "malagasy_definition": "Fanazavana.", "definition_origin": "editorial_simple_english",
             "reason": "Context.", "evidence_files": ["source.wiki"],
             "dictionary_checks": [{"status": "missing", "raw": "x" * 4000}],
             "old_review": {"status": "unresolved"}}
            for sense, section, status in [("first", "00", "descriptive"),
                                           ("second", "01", "unresolved"),
                                           ("third", "01", "verified")]]
    write_json(tmp_path / "vocabulary.json", rows)
    return tmp_path


def test_view_pages_exact_senses_and_preserves_source(job):
    before = (job / "vocabulary.json").read_bytes()
    page = vocabulary_view(job, "vocabulary.json", limit=1)
    assert page["source"]["sha256"] == digest(before)
    assert page["next_offset"] == 1
    assert page["matching_records"] == 3
    assert page["records"][0]["record_index"] == 0
    assert page["records"][0]["current"]["source_sense"] == "first"
    assert "dictionary_checks" in page["records"][0]["omitted_fields"]
    assert "x" * 100 not in json.dumps(page)
    filtered = vocabulary_view(job, "vocabulary.json", section="01", term="term", limit=1)
    assert filtered["records"][0]["record_index"] == 1
    assert filtered["records"][0]["current"]["status"] == "unresolved"
    assert vocabulary_view(job, "vocabulary.json", term="Term")["records"] == []
    last = vocabulary_view(job, "vocabulary.json", offset=2, limit=1)
    assert last["next_offset"] is None
    assert vocabulary_view(job, "vocabulary.json", offset=100)["records"] == []
    detailed = vocabulary_view(job, "vocabulary.json", limit=1, include_evidence=True)
    assert detailed["records"][0]["current"]["evidence_files"] == ["source.wiki"]
    assert "evidence_files" not in detailed["records"][0]["omitted_fields"]
    assert (job / "vocabulary.json").read_bytes() == before


@pytest.mark.parametrize("kwargs", [{"offset": -1}, {"limit": 0}, {"limit": 101},
                                    {"offset": True}, {"limit": False}])
def test_view_rejects_bad_page(job, kwargs):
    with pytest.raises(GuardError):
        vocabulary_view(job, "vocabulary.json", **kwargs)


def test_summary_saves_complete_report_without_replaying_it(job, capsys):
    output = job / "report.json"
    args = ["vocabulary-report", "--job", str(job), "--vocabulary", "vocabulary.json",
            "--output", str(output), "--summary"]
    assert cli.main(args) == 0
    summary = json.loads(capsys.readouterr().out)
    full = json.loads(output.read_bytes())
    assert full["records"][0]["dictionary_checks"][0]["raw"] == "x" * 4000
    assert full["unresolved_record_indices"] == [1]
    assert summary["view"] == "summary_only"
    assert summary["counts"]["unresolved_record_indices"] == 1
    assert summary["counts"]["records"] == 3
    assert summary["artifact"]["sha256"] == digest(output.read_bytes())
    assert "x" * 100 not in json.dumps(summary)
    assert cli.main(args) == 1
    assert "Output exists" in capsys.readouterr().err


def test_summary_missing_or_existing_output_fails_before_remote_call(job, monkeypatch, capsys):
    monkeypatch.setattr(cli, "lookup", lambda *a: pytest.fail("Unnecessary remote lookup"))
    args = ["lookup", "--edition", "en", "--word", "term", "--summary"]
    assert cli.main(args) == 1
    assert "requires --output" in capsys.readouterr().err
    assert cli.main([*args, "--output", str(job / "source.wiki")]) == 1
    assert "Output exists" in capsys.readouterr().err


def test_summary_broker_preserves_full_result_and_denial(job, monkeypatch, capsys):
    from mgwiki_editor import control

    monkeypatch.setenv("MGWIKI_BROKER_SOCKET", "/socket")
    monkeypatch.setenv("MGWIKI_CAPABILITY_FILE", "/cap")
    full = {"status": "failed", "entries": [], "error_body": "raw failure"}
    monkeypatch.setattr(control, "client", lambda *a: {"ok": True, "result": full})
    args = ["lookup", "--edition", "en", "--word", "term", "--summary",
            "--output", str(job / "reply.json")]
    assert cli.main(args) == 0
    assert json.loads(capsys.readouterr().out)["result"]["signals"]["status"] == "failed"
    assert json.loads((job / "reply.json").read_bytes()) == full
    monkeypatch.setattr(control, "client", lambda *a: {"ok": False, "decision": "DENY"})
    args[-1] = str(job / "denied.json")
    assert cli.main(args) == 1
    assert json.loads(capsys.readouterr().out)["decision"] == "DENY"
    assert not (job / "denied.json").exists()


@pytest.mark.parametrize("command", ["vocabulary-view", "vocabulary-pack"])
def test_new_memo_tools_never_bypass_configured_broker(job, monkeypatch, capsys, command):
    monkeypatch.setenv("MGWIKI_BROKER_SOCKET", "/socket")
    monkeypatch.setenv("MGWIKI_CAPABILITY_FILE", "/cap")
    monkeypatch.setattr(cli, "vocabulary_view", lambda *a, **k: pytest.fail("Bypass"))
    monkeypatch.setattr(cli, "pack_vocabulary", lambda *a, **k: pytest.fail("Bypass"))
    args = [command, "--job", str(job), "--vocabulary", "vocabulary.json"]
    if command == "vocabulary-pack":
        args += ["--output", str(job / "candidate")]
    assert cli.main(args) == 1
    assert "no fallback" in capsys.readouterr().err


def test_pack_losslessly_archives_auxiliary_fields_and_binds_raw_evidence(job):
    before = (job / "vocabulary.json").read_bytes()
    original = json.loads(before)
    result = pack_vocabulary(job, "vocabulary.json", job / "candidate")
    lean = json.loads((job / "candidate/vocabulary.json").read_bytes())
    archive = json.loads((job / "candidate/details.json").read_bytes())
    assert result["status"] == "candidate_only"
    assert result["candidate_bytes"] < len(before)
    assert result["unique_auxiliary_values"] == 2
    for index, row in enumerate(lean):
        restored = {key: value for key, value in row.items() if key != "packed_details"}
        restored["evidence_files"] = restored["evidence_files"][:-1]
        for key, sha256 in archive["records"][index].items():
            value = archive["objects"][sha256]
            assert digest(json_bytes(value)) == sha256
            restored[key] = value
        assert restored == original[index]
        assert row["evidence_files"] == ["source.wiki", "candidate/details.json"]
        assert row["status"] == original[index]["status"]
    assert (job / "vocabulary.json").read_bytes() == before
    # Simulate explicit coordinator adoption; normal proposal hashing binds archive AND raw source.
    write_json(job / "vocabulary.json", lean)
    for name in ("job.json", "review.json", "notes.wiki", "draft.wiki"):
        (job / name).write_text("fixture", encoding="utf-8")
    hashes = artifact_hashes(job)
    assert hashes["source.wiki"] == digest((job / "source.wiki").read_bytes())
    assert hashes["candidate/details.json"] == digest((job / "candidate/details.json").read_bytes())
    (job / "candidate/details.json").write_text("tampered", encoding="utf-8")
    assert hashes != artifact_hashes(job)


@pytest.mark.parametrize("marker", ["proposal.json", "receipt.json"])
def test_pack_refuses_prepared_or_uncertain_save_jobs(job, marker):
    (job / marker).write_text("{}", encoding="utf-8")
    with pytest.raises(GuardError, match="Prepared/save-attempt"):
        pack_vocabulary(job, "vocabulary.json", job / "candidate")
    assert not (job / "candidate").exists()


def test_pack_rejects_overwrite_unsafe_evidence_and_escaped_output(job, tmp_path):
    pack_vocabulary(job, "vocabulary.json", job / "candidate")
    with pytest.raises(GuardError, match="exists"):
        pack_vocabulary(job, "vocabulary.json", job / "candidate")
    with pytest.raises(GuardError, match="inside the job"):
        pack_vocabulary(job, "vocabulary.json", job.parent / "escape")
    rows = json.loads((job / "vocabulary.json").read_bytes())
    rows[0]["evidence_files"] = ["../outside"]
    write_json(job / "vocabulary.json", rows)
    with pytest.raises(GuardError, match="unsafe"):
        pack_vocabulary(job, "vocabulary.json", job / "candidate2")
    assert not (job / "candidate2").exists()


def test_pack_cli_is_offline_candidate_only(job, monkeypatch, capsys):
    monkeypatch.setattr(cli, "Wiki", lambda: pytest.fail("No Wiki"))
    assert cli.main(["vocabulary-pack", "--job", str(job), "--vocabulary", "vocabulary.json",
                     "--output", str(job / "candidate")]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "candidate_only"
    assert not (job / "review.json").exists()


def test_pack_cannot_make_empty_evidence_pass_by_adding_archive(job):
    rows = json.loads((job / "vocabulary.json").read_bytes())
    rows[0]["evidence_files"] = []
    write_json(job / "vocabulary.json", rows)
    with pytest.raises(GuardError, match="nonempty evidence_files"):
        pack_vocabulary(job, "vocabulary.json", job / "candidate")
    assert not (job / "candidate").exists()


def test_pack_refuses_dangling_output_symlink(job):
    (job / "candidate").symlink_to(job / "nonexistent", target_is_directory=True)
    with pytest.raises(GuardError, match="exists"):
        pack_vocabulary(job, "vocabulary.json", job / "candidate")
    assert not (job / "nonexistent").exists()


def test_view_cli_offline(job, monkeypatch, capsys):
    monkeypatch.setattr(cli, "Wiki", lambda: pytest.fail("No Wiki"))
    assert cli.main(["vocabulary-view", "--job", str(job), "--limit", "1"]) == 0
    assert len(json.loads(capsys.readouterr().out)["records"]) == 1


def test_json_slice_pages_and_projects_large_evidence(job):
    payload = {"status": "review", "files": [
        {"filename": f"File {index}.jpg", "decision": "retain", "capsule": {"blob": "x" * 2000}}
        for index in range(50)]}
    write_json(job / "media.json", payload)
    path = "media.json"
    before = (job / path).read_bytes()
    page = json_slice(job, path, key="files", limit=2, fields=["filename", "decision"])
    assert page["total_items"] == 50
    assert page["offset"] == 0
    assert page["next_offset"] == 2
    assert page["items"][0] == {"filename": "File 0.jpg", "decision": "retain"}
    assert page["selected_fields"] == ["decision", "filename"]
    assert page["omitted_fields"] == ["capsule"]
    assert page["source"]["sha256"] == digest(before)
    assert "x" * 100 not in json.dumps(page)
    assert (job / path).read_bytes() == before
    last = json_slice(job, path, key="files", offset=49, limit=2)
    assert last["next_offset"] is None
    assert len(last["items"]) == 1


@pytest.mark.parametrize("kwargs", [
    {"offset": -1}, {"limit": 0}, {"limit": 101}, {"offset": True}, {"limit": False},
    {"key": "missing"}, {"key": "files.nope"},
])
def test_json_slice_rejects_bad_arguments(job, kwargs):
    write_json(job / "media.json", {"files": [{"name": "a"}]})
    with pytest.raises(GuardError):
        json_slice(job, "media.json", **kwargs)


def test_json_slice_refuses_root_without_key_and_unsafe_paths(job, tmp_path):
    write_json(job / "media.json", {"files": [{"name": "a"}]})
    with pytest.raises(GuardError, match="not an array"):
        json_slice(job, "media.json")
    with pytest.raises(GuardError, match="unsafe"):
        json_slice(job, "../outside.json")


def test_json_slice_cli_summary_keeps_full_output_and_source(job, monkeypatch, capsys):
    monkeypatch.setattr(cli, "Wiki", lambda: pytest.fail("No Wiki"))
    write_json(job / "media.json", {"files": [{"filename": "a.jpg", "blob": "x" * 5000},
                                               {"filename": "b.jpg", "blob": "x" * 5000}]})
    output = job / "slice.json"
    args = ["json-slice", "--job", str(job), "--path", "media.json", "--key", "files",
            "--limit", "1", "--field", "filename", "--output", str(output), "--summary"]
    assert cli.main(args) == 0
    summary = json.loads(capsys.readouterr().out)
    full = json.loads(output.read_bytes())
    assert summary["view"] == "summary_only"
    assert summary["counts"]["items"] == 1
    assert summary["artifact"]["sha256"] == digest(output.read_bytes())
    assert full["items"] == [{"filename": "a.jpg"}]
    assert "x" * 100 not in json.dumps(summary)
    assert cli.main(args) == 1
    assert "Output exists" in capsys.readouterr().err


def test_json_slice_never_bypasses_configured_broker(job, monkeypatch, capsys):
    monkeypatch.setenv("MGWIKI_BROKER_SOCKET", "/socket")
    monkeypatch.setenv("MGWIKI_CAPABILITY_FILE", "/cap")
    write_json(job / "media.json", {"files": []})
    assert cli.main(["json-slice", "--job", str(job), "--path", "media.json"]) == 1
    assert "no fallback" in capsys.readouterr().err


def test_session_usage_never_bypasses_configured_broker(job, monkeypatch, capsys):
    monkeypatch.setenv("MGWIKI_BROKER_SOCKET", "/socket")
    monkeypatch.setenv("MGWIKI_CAPABILITY_FILE", "/cap")
    write_json(job / "usage.json", {"data": [usage_row()]})
    assert cli.main(["session-usage", "--input", str(job / "usage.json")]) == 1
    assert "no fallback" in capsys.readouterr().err


def fake_lookup(status="found"):
    def look(edition, word):
        return {"edition": edition, "word": word, "status": status, "entries": [],
                "retrieved_at": "2026-11-12T00:00:00+00:00",
                "url": f"http://dictionary.invalid/wiktionary-pages/{edition}/{word}"}
    return look


def test_lookup_batch_writes_one_file_per_word_with_manifest(job, monkeypatch, capsys):
    monkeypatch.setattr(cli, "Wiki", lambda: pytest.fail("No Wiki"))
    monkeypatch.setattr(batching, "lookup", fake_lookup())
    assert cli.main(["lookup-batch", "--edition", "en", "--word", "rano", "--word", "Volamena",
                     "--job", str(job), "--output-dir", str(job / "evidence/lookups-b01"),
                     "--output", str(job / "evidence/lookups-b01.json")]) == 0
    manifest = json.loads(capsys.readouterr().out)
    assert manifest["status"] == "evidence_only"
    assert manifest["status_counts"] == {"found": 2}
    for row in manifest["results"]:
        path = job / row["file"]
        assert path.is_file()
        assert row["sha256"] == digest(path.read_bytes())
        reply = json.loads(path.read_bytes())
        assert reply["word"] == row["word"]
    # Case/accents keep their exact identity: separate files, no merging.
    assert manifest["results"][0]["word"] == "rano"
    assert manifest["results"][1]["word"] == "Volamena"


def test_lookup_batch_keeps_pending_evidence_and_continues(job, monkeypatch, capsys):
    monkeypatch.setattr(cli, "Wiki", lambda: pytest.fail("No Wiki"))
    replies = {"found": fake_lookup()("en", "good"), "failed": fake_lookup("failed")("en", "bad")}
    def look(edition, word):
        return replies["failed" if word == "bad" else "found"]
    monkeypatch.setattr(batching, "lookup", look)
    args = ["lookup-batch", "--edition", "en", "--word", "good", "--word", "bad",
            "--job", str(job), "--output-dir", str(job / "evidence/lookups-b02")]
    assert cli.main(args) == 0
    manifest = json.loads(capsys.readouterr().out)
    assert manifest["status_counts"] == {"found": 1, "failed": 1}
    assert len(manifest["results"]) == 2


@pytest.mark.parametrize("words,kwargs", [
    (["same", "same"], {}), (["", "x"], {}), ([f"w{i}" for i in range(51)], {}),
    (["x"], {"output_dir": "outside"}),
])
def test_lookup_batch_rejects_duplicates_oversize_and_escapes(job, words, kwargs):
    output_dir = job.parent / "escape" if kwargs.get("output_dir") == "outside" \
        else job / "evidence/lookups-b03"
    with pytest.raises(GuardError):
        lookup_batch("en", words, job, output_dir)
    if output_dir == job / "evidence/lookups-b03":
        assert not output_dir.exists()


def test_lookup_batch_never_bypasses_configured_broker(job, monkeypatch, capsys):
    monkeypatch.setenv("MGWIKI_BROKER_SOCKET", "/socket")
    monkeypatch.setenv("MGWIKI_CAPABILITY_FILE", "/cap")
    monkeypatch.setattr(cli, "lookup", lambda *a: pytest.fail("Bypass"))
    assert cli.main(["lookup-batch", "--edition", "en", "--word", "x", "--job", str(job),
                     "--output-dir", str(job / "evidence/lookups-b04")]) == 1
    assert "no fallback" in capsys.readouterr().err


def test_offline_audit_runs_all_checks_and_reports_errors(job, monkeypatch, capsys):
    monkeypatch.setattr(cli, "Wiki", lambda: pytest.fail("No Wiki"))
    (job / "source.wiki").write_bytes(b"Pinned source.")
    (job / "draft.wiki").write_bytes(b"'''Rano''' dia ranoka.\n")
    monkeypatch.setattr(batching, "coverage_report", lambda j, d: {"missing_files": {}})
    monkeypatch.setattr(batching, "citation_audit", lambda j, d: {"short_candidates": []})
    monkeypatch.setattr(batching, "metadata_audit", lambda j, e, d: {"gaps": []})
    def failing(*a, **k):
        raise GuardError("boom")
    monkeypatch.setattr(batching, "audit_mathematical_terms", failing)
    manifest_path = job / "evidence/audit-b01.json"
    args = ["offline-audit", "--job", str(job), "--draft", "draft.wiki",
            "--vocab-audit", "--output", str(manifest_path)]
    assert cli.main(args) == 1  # one failing check must not hide the others
    manifest = json.loads(capsys.readouterr().out)
    assert manifest["status"] == "reports_only"
    assert manifest["failed_checks"] == ["vocab-audit"]
    by_name = {row["check"]: row for row in manifest["checks"]}
    assert by_name["validate"]["status"] == "ok"
    for name in ("coverage", "citation-audit", "metadata-audit"):
        path = job / by_name[name]["output"]
        assert path.is_file() and by_name[name]["sha256"] == digest(path.read_bytes())
    error_row = by_name["vocab-audit"]
    assert error_row["status"] == "error" and error_row["error"] == "GuardError"
    assert not (job / "evidence/audit-b01-vocab-audit.json").exists()


def test_offline_audit_refuses_existing_outputs(job):
    (job / "draft.wiki").write_bytes(b"x")
    manifest = job / "evidence/audit-b02.json"
    manifest.parent.mkdir()
    manifest.write_bytes(b"{}")
    with pytest.raises(GuardError, match="preserve it"):
        offline_audit(job, "draft.wiki", manifest)


def test_evidence_pin_and_verify_roundtrip(job, monkeypatch, capsys):
    monkeypatch.setattr(cli, "Wiki", lambda: pytest.fail("No Wiki"))
    (job / "draft.wiki").write_bytes(b"before")
    pin = job / "evidence/pin-b01.json"
    assert cli.main(["evidence-pin", "--job", str(job), "--artifact", "draft.wiki",
                     "--output", str(pin)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["artifacts"]["draft.wiki"]["sha256"] == digest(b"before")
    assert cli.main(["evidence-verify", "--job", str(job), "--pin", "evidence/pin-b01.json"]) == 0
    verify = json.loads(capsys.readouterr().out)
    assert verify["unchanged"] is True and not verify["mismatches"]
    (job / "draft.wiki").write_bytes(b"after")
    args = ["evidence-verify", "--job", str(job), "--pin", "evidence/pin-b01.json",
            "--output", str(job / "evidence/verify-b01.json")]
    assert cli.main(args) == 0
    verify = json.loads(capsys.readouterr().out)
    assert verify["unchanged"] is False
    assert verify["mismatches"][0]["artifact"] == "draft.wiki"
    assert verify["mismatches"][0]["expected"] == digest(b"before")
    assert verify["mismatches"][0]["actual"] == digest(b"after")


def test_evidence_pin_rejects_empty_missing_and_existing(job):
    with pytest.raises(GuardError):
        evidence_pin(job, [], job / "evidence/pin-b02.json")
    with pytest.raises(GuardError, match="Missing or unsafe"):
        evidence_pin(job, ["nope.wiki"], job / "evidence/pin-b02.json")
    pin = job / "evidence/pin-b03.json"
    pin.parent.mkdir(exist_ok=True)
    pin.write_bytes(b"{}")
    with pytest.raises(GuardError, match="preserve it"):
        evidence_pin(job, ["source.wiki"], pin)


def test_evidence_verify_rejects_bad_pin_and_missing_artifacts(job):
    (job / "evidence").mkdir(exist_ok=True)
    (job / "evidence/bad.json").write_bytes(b'{"schema": 1}')
    with pytest.raises(GuardError, match="Invalid artifact pin"):
        evidence_verify(job, "evidence/bad.json")
    (job / "draft.wiki").write_bytes(b"x")
    pin = job / "evidence/pin-b04.json"
    write_json(pin, {"schema": 1, "kind": "artifact_pin",
                     "artifacts": {"draft.wiki": {"sha256": "0" * 64, "bytes": 1},
                                   "gone.wiki": {"sha256": "1" * 64, "bytes": 1}}})
    result = evidence_verify(job, "evidence/pin-b04.json")
    assert result["unchanged"] is False
    assert result["missing"] == ["gone.wiki"]
    assert result["mismatches"][0]["artifact"] == "draft.wiki"


def usage_row(ident="parent", parent=None, **tokens):
    return {"id": ident, "parentID": parent,
            "tokens": {"input": 10, "output": 3, "reasoning": 2,
                       "cache": {"read": 100, "write": 0}, **tokens}}


def test_usage_roots_only_duplicate_dedup_and_reasoning_not_added():
    parent = usage_row()
    child = usage_row("child", "parent")
    result = session_usage({"data": [parent, child, parent]})
    assert len(result["sessions"]) == 1
    assert result["totals"] == {"input": 10, "output": 3, "reasoning": 2,
                                "cache_read": 100, "cache_write": 0}
    assert result["cache_read_fraction"] == 100 / 113
    assert session_usage([parent, child], sessions=["child"])["sessions"][0]["id"] == "child"
    assert session_usage([])["cache_read_fraction"] is None


@pytest.mark.parametrize("rows,selection", [
    ([usage_row(), usage_row("child", "parent")], ["parent", "child"]),
    ([usage_row(), usage_row("child", "parent"), usage_row("worker", "child")],
     ["parent", "worker"]),
    ([usage_row("loop", "loop")], ["loop"]),
    ([usage_row()], ["missing"]),
    ([usage_row(), usage_row(input=20)], None),
    ([usage_row(input=-1)], None), ([usage_row(output=True)], None),
    ([{"id": "bad"}], None),
])
def test_usage_refuses_ambiguous_or_invalid_counters(rows, selection):
    with pytest.raises(GuardError):
        session_usage(rows, sessions=selection)


def test_usage_cli_reads_snapshot_offline(job, monkeypatch, capsys):
    monkeypatch.setattr(cli, "Wiki", lambda: pytest.fail("No Wiki"))
    source = job / "usage.json"
    write_json(source, {"data": [usage_row()]})
    assert cli.main(["session-usage", "--input", str(source)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["totals"]["cache_read"] == 100
    assert result["source"]["sha256"] == digest(source.read_bytes())
