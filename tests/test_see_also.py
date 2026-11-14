"""Offline Jereo koa (See also) link gate; red links are intentional."""

from __future__ import annotations

from pathlib import Path

import pytest

from mgwiki_editor.core import lint_wikitext, see_also_errors

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "path",
    [
        "AGENTS.md",
        ".opencode/skills/mgwiki-style/SKILL.md",
        ".opencode/skills/mgwiki-style/references/manual-of-style.wiki",
        ".opencode/agents/mgwiki-editor.md",
        ".opencode/agents/mgwiki-section.md",
        "docs/edition-protocol.md",
    ],
)
def test_see_also_policy_is_documented(path: str) -> None:
    text = " ".join((ROOT / path).read_text(encoding="utf-8").split())
    assert "Jereo koa" in text
    assert "red link" in text or "does not exist" in text


def test_red_link_entries_pass() -> None:
    text = "== Jereo koa ==\n* [[Rano vaovao]]\n* [[Rano|Rano eto an-tany]]\n"
    assert see_also_errors(text) == []
    assert lint_wikitext(text) == []


def test_unlinked_entry_fails() -> None:
    text = "== Jereo koa ==\n* [[Rano]]\n* Ranomasina\n"
    errors = see_also_errors(text)
    assert errors == ["Jereo koa entry needs a linked article title (line 3)."]
    assert "Jereo koa entry needs a linked article title" in " ".join(lint_wikitext(text))


def test_non_article_links_do_not_satisfy_the_gate() -> None:
    text = (
        "== Jereo koa ==\n"
        "* [[:Sokajy:Rano]]\n"
        "* [[File:Rano.jpg]]\n"
        "* [[en:Water]]\n"
        "* [https://example.org Rano]\n"
    )
    assert len(see_also_errors(text)) == 4


def test_other_sections_and_comments_are_ignored() -> None:
    text = (
        "== Toe-javatra ==\n"
        "* Tsy rohy\n"
        "== Jereo koa ==\n"
        "* <!-- [[Hidden]] -->\n"
        "* [[Rano]]\n"
        "== Loharano ==\n"
        "* Tsy rohy\n"
    )
    assert see_also_errors(text) == []


def test_masked_nowiki_heading_is_ignored() -> None:
    text = "<nowiki>\n== Jereo koa ==\n* Tsy rohy\n</nowiki>\n"
    assert see_also_errors(text) == []
