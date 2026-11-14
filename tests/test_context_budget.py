"""Static context budget; every session re-pays these bytes, so growth must be deliberate."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# Always-loaded rules: system prompt policy, required skills, local style references,
# agent prompts. Ceilings are the reviewed 2026-11-12 sizes; raising one is a policy
# decision (shorter is always allowed) and should be explained in the same change.
# The 2026-11-12 category/hatnote policy change added live Sokajy output and the
# {{lahatsoratra antsipirihany}} section-hatnote rule.
# The 2026-11-14 domain-acronym and Malagasy transcription policy added
# subject-specific acronym fallbacks plus geminate and /o/, /u/ transcription rules.
BUDGET = {
    "AGENTS.md": 18_600,
    ".opencode/skills/mgwiki-style/SKILL.md": 17_600,
    ".opencode/skills/mgwiki-style/references/manual-of-style.wiki": 17_450,
    ".opencode/skills/mgwiki-style/references/words-to-watch.wiki": 10_300,
    ".opencode/skills/mg-vocab/SKILL.md": 16_300,
    ".opencode/skills/mgwiki-edition/SKILL.md": 7_750,
    ".opencode/agents/mgwiki-editor.md": 19_300,
    ".opencode/agents/mgwiki-article.md": 3_950,
    ".opencode/agents/mgwiki-section.md": 8_000,
    ".opencode/commands/mgtranslate.md": 5_400,
}

# A fresh section worker loads these before any article evidence. The cap keeps the
# per-session fixed cost from creeping back up; article quality rules stay mandatory.
WORKER_FIXED = (
    "AGENTS.md",
    ".opencode/skills/mgwiki-style/SKILL.md",
    ".opencode/skills/mgwiki-style/references/manual-of-style.wiki",
    ".opencode/skills/mgwiki-style/references/words-to-watch.wiki",
    ".opencode/skills/mg-vocab/SKILL.md",
    ".opencode/agents/mgwiki-section.md",
)
WORKER_FIXED_CAP = 89_500


@pytest.mark.parametrize("name, ceiling", sorted(BUDGET.items()))
def test_always_loaded_rule_file_stays_within_budget(name: str, ceiling: int) -> None:
    size = len((ROOT / name).read_bytes())
    assert size <= ceiling, f"{name} grew to {size} bytes (budget {ceiling}); trim or justify"


def test_worker_fixed_context_stays_within_cap() -> None:
    total = sum(len((ROOT / name).read_bytes()) for name in WORKER_FIXED)
    assert total <= WORKER_FIXED_CAP, (
        f"worker fixed context is {total} bytes (cap {WORKER_FIXED_CAP}); "
        "remove duplication instead of adding a new copy of a rule"
    )


def test_bounded_evidence_tools_are_documented() -> None:
    """Rules must name the bounded readers, not just forbid giant reads."""
    policy = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    for command in ("json-slice", "vocabulary-view", "vocabulary-report --summary"):
        assert command in policy
    docs = (ROOT / "docs/token-efficient-workflow.md").read_text(encoding="utf-8")
    assert "json-slice" in docs
    assert "--group-max-bytes" in docs
