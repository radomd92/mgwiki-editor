"""Offline policy checks; actual OpenCode compaction still needs runtime validation."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# Every role file that can be compacted, plus the coordinator protocol document.
ROLE_FILES = [
    "AGENTS.md",
    ".opencode/agents/mgwiki-editor.md",
    ".opencode/agents/mgwiki-article.md",
    ".opencode/agents/mgwiki-section.md",
    ".opencode/agents/Mgwiki-editor-issues-solver.md",
    ".opencode/commands/mgtranslate.md",
    ".opencode/skills/mgwiki-style/SKILL.md",
    ".opencode/skills/mgwiki-edition/SKILL.md",
    "docs/edition-protocol.wiki",
]

REQUIRED_FIELDS = (
    "paths", "commands", "identifiers", "hashes", "revisions", "URLs", "errors",
    "decisions", "blockers", "pending actions", "authorization limits", "safety guards",
)


@pytest.mark.parametrize("path", ROLE_FILES)
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
    for detail in REQUIRED_FIELDS:
        assert detail in text
    assert "caveman mode does not apply" not in text
    assert "wikitext" in text


def test_compaction_field_list_is_identical_in_every_role_file() -> None:
    """Parity guard: no role may keep a shortened list of protected identifiers."""
    for path in ROLE_FILES:
        text = " ".join((ROOT / path).read_text(encoding="utf-8").split())
        block = text[text.index("compaction summaries"):]
        block = block[:block.index("clarity wins")]
        missing = [detail for detail in REQUIRED_FIELDS if detail not in block]
        assert not missing, f"{path} compaction block lost: {missing}"


@pytest.mark.parametrize("path", [
    ".opencode/agents/mgwiki-section.md",
    "docs/token-efficient-workflow.md",
])
def test_worker_recovery_after_compaction_is_explicit(path: str) -> None:
    """A compacted worker must re-read its assignment instead of trusting a summary."""
    text = " ".join((ROOT / path).read_text(encoding="utf-8").split())
    assert "re-read" in text
    assert "never continue from a summary alone" in text or "never continue\nfrom" in text


@pytest.mark.parametrize("path", [
    ".opencode/agents/mgwiki-editor.md",
    ".opencode/agents/mgwiki-article.md",
    "docs/token-efficient-workflow.md",
])
def test_unconfirmed_receipt_survives_compaction(path: str) -> None:
    """Compaction is harness-driven, so an uncertain save needs an explicit recovery rule."""
    text = " ".join((ROOT / path).read_text(encoding="utf-8").split())
    assert "save receipt is unconfirmed" in text
    assert "reconcile" in text
