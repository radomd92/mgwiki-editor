"""Lean views preserve original evidence and guards; all fixtures offline."""

from __future__ import annotations

import json

import pytest

from mgwiki_editor import cli
from mgwiki_editor.core import GuardError, artifact_hashes, digest, json_bytes, write_json
from mgwiki_editor.memos import pack_vocabulary, vocabulary_view
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


def test_session_usage_never_bypasses_configured_broker(job, monkeypatch, capsys):
    monkeypatch.setenv("MGWIKI_BROKER_SOCKET", "/socket")
    monkeypatch.setenv("MGWIKI_CAPABILITY_FILE", "/cap")
    write_json(job / "usage.json", {"data": [usage_row()]})
    assert cli.main(["session-usage", "--input", str(job / "usage.json")]) == 1
    assert "no fallback" in capsys.readouterr().err


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
