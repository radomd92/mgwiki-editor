"""Offline reviewed-tip promotion and query; advisory memory only."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mgwiki_editor import cli
from mgwiki_editor.core import GuardError
from mgwiki_editor.knowledge import knowledge_index, promote_memory


def entry(ident: str = "TM-test-tip", *, status: str = "reviewed", scope: str = "general") -> dict:
    return {
        "id": ident,
        "status": status,
        "scope": scope,
        "domain": "medicine",
        "source_language": "en",
        "target_language": "mg",
        "problem": "Acronym source is ambiguous.",
        "guidance": "Prefer the French form; keep English only when French uses it.",
        "evidence": ["notes.wiki"],
        "source_sections": ["02-treatment"],
    }


@pytest.fixture
def job(tmp_path: Path) -> Path:
    directory = tmp_path / "job"
    directory.mkdir()
    (directory / "notes.wiki").write_text("Evidence.\n", encoding="utf-8")
    return directory


def write_memory(job: Path, entries: list[dict]) -> Path:
    path = job / "translation-memory.json"
    path.write_text(json.dumps({"entries": entries}), encoding="utf-8")
    return path


def test_promote_reviewed_general_tip(job: Path, tmp_path: Path) -> None:
    memory = write_memory(job, [entry()])
    output = tmp_path / "shared"
    result = promote_memory(job, memory, output)
    assert result["status"] == "promoted"
    assert result["promoted"] == ["TM-test-tip"]
    stored = json.loads((output / "TM-test-tip.json").read_text(encoding="utf-8"))
    assert stored["guidance"].startswith("Prefer the French")
    assert stored["source_job"] == "job"
    assert stored["promoted_at"]


def test_candidate_and_article_scope_are_skipped(job: Path, tmp_path: Path) -> None:
    memory = write_memory(
        job,
        [entry("TM-candidate", status="candidate"), entry("TM-article", scope="article")],
    )
    result = promote_memory(job, memory, tmp_path / "shared")
    assert result["status"] == "nothing_to_promote"
    assert [row["id"] for row in result["skipped"]] == ["TM-candidate", "TM-article"]


def test_missing_evidence_blocks_promotion(job: Path, tmp_path: Path) -> None:
    broken = entry()
    broken["evidence"] = ["missing.json"]
    memory = write_memory(job, [broken])
    with pytest.raises(GuardError, match="evidence"):
        promote_memory(job, memory, tmp_path / "shared")


def test_memory_must_be_inside_job(job: Path, tmp_path: Path) -> None:
    outside = tmp_path / "outside.json"
    outside.write_text(json.dumps([entry()]), encoding="utf-8")
    with pytest.raises(GuardError, match="inside the job"):
        promote_memory(job, outside, tmp_path / "shared")


def test_duplicate_ids_are_rejected(job: Path) -> None:
    memory = write_memory(job, [entry(), entry()])
    with pytest.raises(GuardError, match="unique"):
        promote_memory(job, memory, job / "shared")


def test_index_filters_and_reports_invalid_files(job: Path, tmp_path: Path) -> None:
    root = tmp_path / "entries"
    root.mkdir()
    promote_memory(job, write_memory(job, [entry()]), root)
    (root / "broken.json").write_text("{", encoding="utf-8")
    result = knowledge_index(root, domain="medicine", query="french")
    assert result["match_count"] == 1
    assert result["entries"][0]["id"] == "TM-test-tip"
    assert result["invalid_entries"][0]["file"] == "broken.json"
    assert knowledge_index(root, domain="physics")["match_count"] == 0


def test_cli_promote_and_index(job: Path, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    memory = write_memory(job, [entry()])
    output = tmp_path / "entries"
    assert (
        cli.main(
            [
                "knowledge-promote",
                "--job",
                str(job),
                "--memory",
                str(memory),
                "--output-dir",
                str(output),
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["status"] == "promoted"
    assert cli.main(["knowledge-index", "--root", str(output), "--query", "acronym"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["match_count"] == 1
