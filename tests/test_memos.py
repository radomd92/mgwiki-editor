"""Sense-specific reports never merge meanings, rewrite records or upgrade statuses."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from mgwiki_editor import cli
from mgwiki_editor.core import GuardError, digest, write_json
from mgwiki_editor.memos import dictionary_index, vocabulary_report


@pytest.fixture
def job(tmp_path: Path) -> Path:
    (tmp_path / "evidence").mkdir()
    (tmp_path / "source.wiki").write_text("Pinned source.", encoding="utf-8")
    return tmp_path


def reply(job: Path, name: str, **fields) -> str:
    filename = f"evidence/{name}.json"
    write_json(job / filename, {"edition": "en", "word": "term", "status": "found",
                                "entries": [], **fields})
    return filename


def record(**fields) -> dict:
    return {"source_language": "en", "source_term": "term", "source_sense": "a specific sense",
            "domain": "domain", "status": "descriptive", "chosen_expression": "chosen wording",
            "english_definition": "A simple editorial definition.",
            "definition_origin": "editorial_simple_english", "malagasy_definition": "Explanation.",
            "reason": "Contextual descriptive choice.", "evidence_files": ["source.wiki"], **fields}


def test_dictionary_groups_exact_identity_keeps_all_reply_statuses(job: Path) -> None:
    files = [reply(job, "found"), reply(job, "missing", status="missing"),
             reply(job, "failed", status="failed"), reply(job, "capital", word="Term"),
             reply(job, "mg", edition="mg"), reply(job, "plural", word="terms")]
    result = dictionary_index(job, files + [files[0]])
    assert result == dictionary_index(job, list(reversed(files)))
    assert len(result["lookups"]) == 4
    responses = next(r["responses"] for r in result["lookups"]
                     if (r["edition"], r["word"]) == ("en", "term"))
    assert {r["status"] for r in responses} == {"found", "missing", "failed"}
    assert len(responses) == 3
    assert result["status"] == "indexed_only"


def test_dictionary_404_identity_from_exact_recorded_url(job: Path) -> None:
    filename = "evidence/404.json"
    write_json(job / filename, {"status": "missing", "entries": [],
                                "url": "http://dictionary.invalid/wiktionary-pages/en/a%20term"})
    row = dictionary_index(job, [filename])["lookups"][0]
    assert (row["edition"], row["word"]) == ("en", "a term")
    assert row["responses"][0]["status"] == "missing"


@pytest.mark.parametrize("fields", [
    {"edition": None, "word": None}, {"status": None}, {"entries": "bad"},
    {"url": "http://dictionary.invalid/wiktionary-pages/mg/other"},
    {"url": "file:///wiktionary-pages/en/term"},
    {"url": "https://user:secret@dictionary.invalid/wiktionary-pages/en/term"},
])
def test_bad_lookup_evidence_rejected_without_reclassifying_as_miss(job: Path, fields) -> None:
    filename = reply(job, "bad", **fields)
    before = (job / filename).read_bytes()
    with pytest.raises(GuardError):
        dictionary_index(job, [filename])
    assert (job / filename).read_bytes() == before


def test_vocabulary_exact_sense_groups_preserve_variants_and_unresolved_status(job: Path) -> None:
    records = [record(), record(chosen_expression="variant wording", status="unresolved"),
               record(source_sense="another sense"), record(domain="another domain")]
    write_json(job / "vocabulary.json", records)
    before = (job / "vocabulary.json").read_bytes()
    result = vocabulary_report(job, "vocabulary.json", [])
    assert result["records"] == records
    assert (job / "vocabulary.json").read_bytes() == before
    assert len(result["sense_groups"]) == 3
    group = next(row for row in result["sense_groups"] if row["record_indices"] == [0, 1])
    assert group["reconciliation_fields"] == ["chosen_expression", "status"]
    assert group["chosen_expressions"] == ["chosen wording", "variant wording"]
    assert result["unresolved_record_indices"] == [1]
    assert result["distinct_uncertain_english_terms"] == 1
    assert result["artifacts"]["vocabulary.json"] == digest(before)


def test_dictionary_candidate_presence_never_attaches_or_verifies_senses(job: Path) -> None:
    filename = reply(job, "term", entries=[{"language": "en", "definitions": ["Unrelated sense"]}])
    records = [record(status="unresolved", reason="Sense uncertain.")]
    write_json(job / "vocabulary.json", records)
    result = vocabulary_report(job, "vocabulary.json", [filename])
    assert result["records"] == records
    assert result["records"][0]["evidence_files"] == ["source.wiki"]
    assert result["unresolved_record_indices"] == [0]
    assert filename in result["artifacts"]


def test_missing_identity_not_silently_assumed_english_or_merged(job: Path) -> None:
    records = [record(source_language=""), record(source_sense=""), record(source_term="")]
    write_json(job / "vocabulary.json", {"entries": records})
    result = vocabulary_report(job, "vocabulary.json", [])
    assert result["unclassified_record_indices"] == [0, 1, 2]
    assert result["sense_groups"] == []
    assert result["records"] == records
    assert result["missing_fields"][0]["record_index"] == 1


@pytest.mark.parametrize("count,required", [(100, False), (101, True)])
def test_unknown_memo_threshold_counts_distinct_uncertain_english_terms(
    job: Path, count: int, required: bool,
) -> None:
    records = [record(source_term=f"term-{i}") for i in range(count)]
    records += [record(source_term="term-0", source_sense="another sense"),
                record(source_term="verified", status="verified"),
                record(source_term="French", source_language="fr")]
    write_json(job / "vocabulary.json", records)
    result = vocabulary_report(job, "vocabulary.json", [])
    assert result["distinct_uncertain_english_terms"] == count
    assert result["unknown_vocabulary_memo_required"] is required
    assert not (job / "unknown-vocabulary.wiki").exists()


@pytest.mark.parametrize("fields", [
    {"evidence_files": ["missing.wiki"]}, {"evidence_files": ["/etc/hosts"]},
    {"evidence_files": ["../outside"]}, {"evidence_files": "source.wiki"},
    {"source_sense": []}, {"status": {}},
])
def test_invalid_vocab_identity_or_evidence_rejected(job: Path, fields) -> None:
    write_json(job / "vocabulary.json", [record(**fields)])
    with pytest.raises(GuardError):
        vocabulary_report(job, "vocabulary.json", [])


def test_report_never_overwrites_source_issues_or_review(job: Path) -> None:
    for name, text in {"source-issues.md": "# Open issue\nKeep history.",
                       "review.json": '{"approved": false}'}.items():
        (job / name).write_text(text, encoding="utf-8")
    write_json(job / "vocabulary.json", [record()])
    before = {p: p.read_bytes() for p in job.iterdir() if p.is_file()}
    vocabulary_report(job, "vocabulary.json", [])
    assert {p: p.read_bytes() for p in before} == before


def test_report_does_not_mutate_supplied_record_data() -> None:
    from mgwiki_editor.memos import vocabulary_records

    data = [record()]
    before = copy.deepcopy(data)
    assert vocabulary_records({"terms": data}) == before
    assert data == before


def test_memo_cli_offline_with_shared_exclusive_writer(job: Path, monkeypatch, capsys) -> None:
    filename = reply(job, "term")
    write_json(job / "vocabulary.json", [record()])

    def forbidden():
        raise AssertionError("No Wiki construction")

    monkeypatch.setattr(cli, "Wiki", forbidden)
    assert cli.main(["dictionary-index", "--job", str(job), "--lookup", filename]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "indexed_only"
    output = job / "report.json"
    args = ["vocabulary-report", "--job", str(job), "--vocabulary", "vocabulary.json",
            "--lookup", filename, "--output", str(output)]
    assert cli.main(args) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "review_required"
    before = output.read_bytes()
    assert cli.main(args) == 1
    assert "Output exists" in capsys.readouterr().err
    assert output.read_bytes() == before
