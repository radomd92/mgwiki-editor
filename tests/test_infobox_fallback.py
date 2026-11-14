"""Canonical fallback infobox: 30% right float, 5px spacing, 75% text, centered image."""

from __future__ import annotations

from pathlib import Path

import pytest

from mgwiki_editor.core import lint_wikitext

ROOT = Path(__file__).resolve().parents[1]
SNIPPET = (
    '{| class="infobox" style="width:30%; float:right; clear:right; '
    'margin:0 0 5px 5px; font-size:75%;"\n'
    "|-\n"
    '| colspan="2" style="text-align:center;" | '
    "[[File:Example.jpg|center|220px|alt=Ohatra|Sary ohatra]]\n"
    "|-\n"
    '! scope="row" | Anarana\n'
    "| Ohatra\n"
    "|}\n"
)


@pytest.mark.parametrize(
    "path",
    [
        ".opencode/skills/mgwiki-style/SKILL.md",
        ".opencode/skills/mgwiki-style/references/manual-of-style.wiki",
        ".opencode/agents/mgwiki-editor.md",
        ".opencode/agents/mgwiki-section.md",
        "AGENTS.md",
        "docs/edition-protocol.md",
    ],
)
def test_fallback_infobox_policy_is_documented(path: str) -> None:
    text = " ".join((ROOT / path).read_text(encoding="utf-8").split())
    assert "infobox" in text.casefold()
    assert "30%" in text
    assert "75%" in text


def test_canonical_snippet_has_required_styles() -> None:
    assert "width:30%" in SNIPPET
    assert "float:right" in SNIPPET
    assert "margin:0 0 5px 5px" in SNIPPET
    assert "font-size:75%" in SNIPPET
    assert "text-align:center" in SNIPPET
    assert "|center|" in SNIPPET


def test_canonical_snippet_is_valid_wikitext() -> None:
    assert lint_wikitext(SNIPPET) == []
