"""Offline vocabulary-to-draft reconciliation; reports candidates, not approval."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mgwiki_editor import cli
from mgwiki_editor.core import GuardError
from mgwiki_editor.terminology_audit import audit_terminology


def record(term: str, sense: str, expression: str, *, status: str = "descriptive") -> dict:
    return {
        "source_term": term,
        "source_language": "en",
        "source_sense": sense,
        "domain": "test",
        "chosen_expression": expression,
        "malagasy_definition": "Famaritana.",
        "status": status,
    }


@pytest.fixture
def job(tmp_path: Path) -> Path:
    (tmp_path / "vocabulary.json").write_text(
        json.dumps(
            [
                record("water", "liquid", "rano"),
                record("sea", "body", "ranomasina"),
                record("river", "waterway", "ony"),
                record("water", "liquid", "rano vaovao"),
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "draft.wiki").write_text(
        """'''Rano''' dia ranoka. Ny rano no zava-dehibe.
Ny water dia hita ao amin' ny lahatsoratra.
''water'' sy "water" ary <ref>water</ref><references />
""",
        encoding="utf-8",
    )
    return tmp_path


def test_audit_reports_missing_and_variant_choices(job: Path) -> None:
    result = audit_terminology(job, job / "draft.wiki")
    missing = {row["source_term"] for row in result["missing_expression_records"]}
    assert missing == {"sea", "river", "water"}
    variants = result["choice_variants"]
    assert len(variants) == 1
    assert variants[0]["chosen_expressions"] == ["rano", "rano vaovao"]


def test_source_term_hits_skip_italics_quotes_and_refs(job: Path) -> None:
    result = audit_terminology(job, job / "draft.wiki")
    hits = result["source_term_hits"]
    assert {(row["source_term"], row["count"]) for row in hits} == {("water", 1)}
    assert len(hits) == 2  # one finding per matching vocabulary record


def test_missing_vocabulary_is_an_error(tmp_path: Path) -> None:
    (tmp_path / "draft.wiki").write_text("Rano.", encoding="utf-8")
    with pytest.raises(GuardError, match="no vocabulary.json"):
        audit_terminology(tmp_path, tmp_path / "draft.wiki")


def test_cli_strict_terminology_audit_fails_on_candidates(
    job: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert (
        cli.main(
            [
                "terminology-audit",
                "--job",
                str(job),
                "--draft",
                str(job / "draft.wiki"),
                "--strict",
            ]
        )
        == 1
    )
    result = json.loads(capsys.readouterr().out)
    assert result["finding_count"] > 0
    assert result["draft_sha256"]
