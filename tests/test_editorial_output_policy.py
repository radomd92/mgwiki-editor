"""Offline instruction checks; not proof of runtime editorial behavior."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
POLICIES = [
    "AGENTS.md",
    ".opencode/agents/mgwiki-editor.md",
    ".opencode/agents/mgwiki-section.md",
    ".opencode/commands/mgtranslate.md",
    ".opencode/skills/mgwiki-style/SKILL.md",
    ".opencode/skills/mgwiki-edition/SKILL.md",
    ".opencode/skills/mg-vocab/SKILL.md",
    "docs/edition-protocol.wiki",
    "README.wiki",
]


@pytest.mark.parametrize("path", POLICIES)
def test_non_article_output_is_not_wikitext_and_uses_ultra(path: str) -> None:
    text = " ".join((ROOT / path).read_text(encoding="utf-8").split())
    assert "caveman ultra" in text
    assert "only for Malagasy translation/" in text
    assert "memories" in text or "Memory" in text
    assert "plain text" in text
    assert "All responses: wikitext" not in text
    assert "All responses use MediaWiki" not in text
    assert "user-facing editorial responses remain wikitext" not in text
    assert "handoff reports remain wikitext" not in text


@pytest.mark.parametrize("path", POLICIES)
def test_source_issues_have_durable_nonblocking_memory(path: str) -> None:
    text = " ".join((ROOT / path).read_text(encoding="utf-8").split())
    assert "source-issues.md" in text
    assert "nonblocking review issues" in text
    assert "contradictions" in text
    assert "translation meaning" in text
    if path != ".opencode/skills/mg-vocab/SKILL.md":
        assert "revision" in text
        assert "next review action" in text
        assert "copyright" in text
