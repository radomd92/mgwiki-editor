"""Read-only terminology auditing never substitutes without sense review."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mgwiki_editor import cli
from mgwiki_editor.core import digest
from mgwiki_editor.terminology import audit_mathematical_terms


def test_audit_uses_database_and_preserves_draft(tmp_path: Path) -> None:
    draft = tmp_path / "section.wiki"
    text = "== Équation ==\nUne équation et un logarithme.\n"
    draft.write_text(text, encoding="utf-8")
    before = draft.read_bytes()
    result = audit_mathematical_terms(draft)
    assert result["draft_sha256"] == digest(before)
    assert [match["term"] for match in result["matches"]] == ["Équation", "équation", "logarithme"]
    assert result["matches"][0]["candidates"][0]["malagasy"] == "Fampimirana"
    assert len(result["matches"][2]["candidates"]) == 2
    assert all(match["status"] == "requires_context_review" for match in result["matches"])
    assert draft.read_bytes() == before


def test_audit_skips_protected_metadata_targets_and_comments(tmp_path: Path) -> None:
    draft = tmp_path / "section.wiki"
    draft.write_text(
        '<ref>Equation, Logarithme, https://example.org/equation</ref>\n'
        '<nowiki>Equation</nowiki><math>Equation</math><!-- Equation -->\n'
        '{{Cite|title=Equation|url=https://example.org/logarithme}}\n'
        '[[Equation|Sary]] [https://example.org/equation Sary]\n'
        '[[Untranslated target]] <gallery>File:Equation.jpg|Logarithme</gallery>\n'
        '[[Topic|équation]] [https://example.org Label: logarithme]\n',
        encoding="utf-8",
    )
    result = audit_mathematical_terms(draft)
    assert [match["term"] for match in result["matches"]] == ["équation", "logarithme"]
    assert all("link-label" in match["location"] for match in result["matches"])
    assert "protected quotations" in result["limits"]


def test_audit_never_replaces_substrings_inside_words(tmp_path: Path) -> None:
    draft = tmp_path / "section.wiki"
    draft.write_text("nonequation equationnaire logarithmement", encoding="utf-8")
    assert audit_mathematical_terms(draft)["matches"] == []


def test_audit_preserves_decomposed_accents_in_report(tmp_path: Path) -> None:
    draft = tmp_path / "section.wiki"
    term = "Carre\u0301"
    draft.write_text(term, encoding="utf-8")
    result = audit_mathematical_terms(draft)
    assert result["matches"][0]["term"] == term
    assert result["matches"][0]["candidates"][0]["malagasy"] == "Toradroa"


def test_cli_audit_reports_without_mutating_draft(
    tmp_path: Path, capsys: pytest.CaptureFixture,
) -> None:
    draft = tmp_path / "draft.wiki"
    draft.write_text("Equation", encoding="utf-8")
    output = tmp_path / "audit.json"
    assert cli.main(["vocab-audit", "--draft", str(draft), "--output", str(output)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["match_count"] == 1
    assert json.loads(output.read_bytes()) == result
    assert draft.read_text(encoding="utf-8") == "Equation"
