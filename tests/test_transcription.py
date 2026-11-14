"""Offline transcription policy/audit regressions; not proof of pronunciation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mgwiki_editor import cli
from mgwiki_editor.core import digest
from mgwiki_editor.transcription import audit_transcription

ROOT = Path(__file__).resolve().parents[1]
STYLE = ROOT / ".opencode/skills/mgwiki-style/SKILL.md"


def test_domain_acronym_rules_are_documented() -> None:
    text = " ".join(STYLE.read_text(encoding="utf-8").split())
    for required in (
        "Medical articles: use the French form of the same acronym",
        "if French also uses the English acronym, use the English one",
        "Government agencies: use the acronym current in the country's original "
        "or official language",
        "Computer science, mathematics and physics: use the English acronym",
        "European history and geography: for a Latin term, use the French form",
        "quotations, original titles, citation metadata, identifiers, link targets and filenames",
    ):
        assert required in text


def test_malagasy_transcription_spelling_rules_are_documented() -> None:
    text = " ".join(STYLE.read_text(encoding="utf-8").split())
    for required in (
        "No geminated consonants",
        "source /o/ sound is written `ô`",
        "source /u/ sound is written `o`",
        "transcription-audit --draft PATH",
        "Do not guess pronunciation",
    ):
        assert required in text


@pytest.mark.parametrize(
    "path",
    [
        "AGENTS.md",
        ".opencode/agents/mgwiki-editor.md",
        "docs/edition-protocol.md",
        ".opencode/skills/mg-vocab/SKILL.md",
    ],
)
def test_roles_repeat_the_domain_and_transcription_rules(path: str) -> None:
    text = " ".join((ROOT / path).read_text(encoding="utf-8").split())
    assert "transcription-audit" in text
    assert "geminated consonants" in text
    assert "French" in text


def test_audit_reports_geminates_and_skips_protected_text(tmp_path: Path) -> None:
    draft = tmp_path / "draft.wiki"
    text = """'''Rosi''' dia mpilalao. Rossi koa no anarany. Ny "Baggio" sy ''football''.
Ny kommissiona no nanao izany; <ref>Mann (2001)</ref><references />
"""
    draft.write_text(text, encoding="utf-8")
    result = audit_transcription(draft)
    words = {finding["word"] for finding in result["findings"]}
    assert words == {"Rossi", "kommissiona"}
    assert result["draft_sha256"] == digest(text.encode("utf-8"))
    assert result["finding_count"] == len(result["findings"])
    assert any("ô" in check for check in result["manual_checks"])
    for finding in result["findings"]:
        assert finding["status"] == "review_required"
        assert finding["context"]


def test_cli_transcription_audit_returns_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    draft = tmp_path / "draft.wiki"
    draft.write_text("Ny kommissiona.\n", encoding="utf-8")
    assert cli.main(["transcription-audit", "--draft", str(draft)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["finding_count"] == 1
    assert result["findings"][0]["word"] == "kommissiona"


def test_cli_strict_transcription_audit_fails_on_candidates(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    draft = tmp_path / "draft.wiki"
    draft.write_text("Ny kommissiona.\n", encoding="utf-8")
    assert cli.main(["transcription-audit", "--draft", str(draft), "--strict"]) == 1
    assert json.loads(capsys.readouterr().out)["finding_count"] == 1
