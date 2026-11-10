"""Offline policy checks; actual OpenCode compaction still needs runtime validation."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("path", [
    "AGENTS.md",
    ".opencode/agents/mgwiki-editor.md",
    ".opencode/agents/mgwiki-section.md",
    ".opencode/commands/mgtranslate.md",
    ".opencode/skills/mgwiki-style/SKILL.md",
])
def test_compaction_uses_harness_template_not_editorial_format(path: str) -> None:
    text = " ".join((ROOT / path).read_text(encoding="utf-8").split())
    assert "compaction summaries" in text
    assert "conversation checkpoints" in text
    assert "OpenCode's supplied Markdown template exactly" in text
    assert "headings, order, labels, and structure" in text
    assert "convert the template to MediaWiki wikitext" in text
    assert "Use caveman ultra for free-text summary bodies" in text
    assert "remove filler and repetition, not substance" in text
    assert "Never compress required template text or change its meaning; clarity wins" in text
    for detail in (
        "paths", "commands", "identifiers", "hashes", "revisions", "URLs", "errors",
        "decisions", "blockers", "pending actions", "authorization limits", "safety guards",
    ):
        assert detail in text
    assert "caveman mode does not apply" not in text
    assert "wikitext" in text
