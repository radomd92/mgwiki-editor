"""Offline vocabulary merge candidate; conflicts stay visible."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mgwiki_editor.core import GuardError
from mgwiki_editor.memos import merge_vocabulary


def record(term: str, expression: str, evidence: list[str]) -> dict:
    return {
        "source_term": term,
        "source_language": "en",
        "source_sense": "sense",
        "domain": "domain",
        "chosen_expression": expression,
        "malagasy_definition": "fanazavana",
        "status": "descriptive",
        "evidence_files": evidence,
    }


@pytest.fixture
def job(tmp_path: Path) -> Path:
    (tmp_path / "vocabulary.json").write_text(
        json.dumps([record("water", "rano", ["source.wiki", "../../evidence/lookup.json"])]),
        encoding="utf-8",
    )
    section = tmp_path / "sections/00-lead"
    section.mkdir(parents=True)
    (section / "vocabulary.json").write_text(
        json.dumps([record("water", "rano madio", ["source.wiki"])]),
        encoding="utf-8",
    )
    (tmp_path / "section-plan.json").write_text(
        json.dumps([{"id": "00-lead", "directory": "sections/00-lead"}]),
        encoding="utf-8",
    )
    return tmp_path


def test_merge_preserves_conflict_and_normalizes_evidence(job: Path) -> None:
    output = job / "assembly/vocabulary-merged.json"
    result = merge_vocabulary(job, output)
    assert result["source_record_count"] == 2
    assert result["merged_record_count"] == 1
    assert result["duplicate_count"] == 1
    assert result["conflicts"][0]["kept"] == "rano"
    assert result["conflicts"][0]["other"] == "rano madio"
    merged = json.loads(output.read_text(encoding="utf-8"))
    assert merged[0]["evidence_files"] == [
        "evidence/lookup.json",
        "sections/00-lead/source.wiki",
        "source.wiki",
    ]
    assert merged[0]["alternatives_rejected"] == ["rano madio"]


def test_merge_never_overwrites(job: Path) -> None:
    output = job / "assembly/vocabulary-merged.json"
    merge_vocabulary(job, output)
    with pytest.raises(GuardError, match="preserve"):
        merge_vocabulary(job, output)


def test_merge_requires_root_memo(tmp_path: Path) -> None:
    with pytest.raises(GuardError, match="root vocabulary"):
        merge_vocabulary(tmp_path, tmp_path / "merged.json")
