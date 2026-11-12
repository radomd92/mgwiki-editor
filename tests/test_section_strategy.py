"""Offline instruction regressions; not proof of runtime permission isolation."""

import re
from fnmatch import fnmatchcase
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def section_worker_rules() -> list[tuple[str, str, str]]:
    """Read this agent's simple rule triples; not OpenCode's runtime evaluator."""
    text = (ROOT / ".opencode/agents/mgwiki-section.md").read_text(encoding="utf-8")
    frontmatter = text.split("---\n", 2)[1]
    return [
        tuple(value.strip('"') for value in match)
        for match in re.findall(
            r"  - action: (.+)\n    resource: (.+)\n    effect: (allow|deny)\n",
            frontmatter,
        )
    ]


def test_coordinator_allows_article_section_and_issue_subagents() -> None:
    text = (ROOT / ".opencode/agents/mgwiki-editor.md").read_text(encoding="utf-8")
    assert ('action: subagent\n    resource: "*"\n    effect: deny') in text
    allowed = re.findall(
        r"action: subagent\n    resource: (.+)\n    effect: allow", text,
    )
    assert set(allowed) == {"mgwiki-article", "mgwiki-section", "Mgwiki-editor-issues-solver"}
    assert "You alone merge accepted fragments" in text


def test_article_coordinator_cannot_recursively_spawn_articles() -> None:
    text = (ROOT / ".opencode/agents/mgwiki-article.md").read_text(encoding="utf-8")
    allowed = re.findall(r"action: subagent\n    resource: (.+)\n    effect: allow", text)
    assert set(allowed) == {"mgwiki-section", "Mgwiki-editor-issues-solver"}
    assert "mode: subagent" in text
    for guard in ("ONE assigned article", "frontmatter does not grant tools", "draft-only/no-save",
                  "uncertain writes", "confirmed receipt", "Do not edit batch/shared queue"):
        assert guard in text


def test_batch_dispatch_is_before_expensive_coordinator_setup() -> None:
    text = (ROOT / ".opencode/agents/mgwiki-editor.md").read_text(encoding="utf-8")
    assert text.index("Batch dispatch first") < text.index("At the start load")
    for guard in ("fresh mgwiki-article", "never pass this conversation", "same child",
                  "duplicate active owners", "Do not load article skills/guides"):
        assert guard in text


def test_worker_skips_only_coordinator_procedures_not_style_or_evidence() -> None:
    text = (ROOT / ".opencode/agents/mgwiki-section.md").read_text(encoding="utf-8")
    assert "Load mgwiki-style and mg-vocab" in text
    assert "local style references in full once" in text
    assert "do not load mgwiki-edition" in text
    assert "relevant evidence" in text
    assert "no remote requests" in text


def test_section_worker_is_offline_and_has_separate_outputs() -> None:
    text = (ROOT / ".opencode/agents/mgwiki-section.md").read_text(encoding="utf-8")
    frontmatter, body = text.split("---\n", 2)[1:]
    assert "mode: subagent" in frontmatter
    assert 'action: "*"\n    resource: "*"\n    effect: deny' in frontmatter
    rules = section_worker_rules()
    assert len(rules) == 8
    for action in ("read", "glob", "grep", "skill"):
        assert f'action: {action}\n    resource: "*"\n    effect: allow' in frontmatter
    assert {action for action, _, effect in rules if effect == "allow"} == {
        "read", "glob", "grep", "edit", "skill",
    }
    assert not any(action == "patch" for action, _, _ in rules)
    assert [(resource, effect) for action, resource, effect in rules if action == "edit"] == [
        (f"runs/*/sections/*/{name}", "allow")
        for name in ("section.wiki", "notes.wiki", "vocabulary.json")
    ]
    for required in (
        "runs/<job>/sections/<id>/", "section.wiki", "notes.wiki", "vocabulary.json",
        "Never edit the root job's", "no remote requests", "or further subagents",
        "complete/blocked", "not a whole-article review",
        "edit permission action", "dynamically assigned section", "report blocked",
        "Do not delete or rename artifacts",
    ):
        assert required in body


@pytest.mark.parametrize("name", ["section.wiki", "notes.wiki", "vocabulary.json"])
def test_worker_edit_rule_covers_each_section_artifact(name: str) -> None:
    rules = section_worker_rules()
    path = f"runs/offline-fixture/sections/00-lead/{name}"
    matching = [
        effect for action, resource, effect in rules
        if action in {"*", "edit"} and fnmatchcase(path, resource)
    ]
    assert matching[-1] == "allow"


@pytest.mark.parametrize("path", [
    "runs/offline-fixture/draft.wiki",
    "runs/offline-fixture/notes.wiki",
    "runs/offline-fixture/vocabulary.json",
    "runs/offline-fixture/review.json",
    "runs/offline-fixture/job.json",
    "runs/offline-fixture/proposal.json",
    "runs/offline-fixture/receipt.json",
    "runs/offline-fixture/sections/00-lead/source.wiki",
    "runs/offline-fixture/sections/00-lead/lookup.json",
    "data/country-names.json",
    ".opencode/agents/mgwiki-editor.md",
    "mgwiki_editor/core.py",
])
def test_worker_edit_rules_do_not_allow_shared_inputs_or_project_files(path: str) -> None:
    rules = section_worker_rules()
    matching = [
        effect for action, resource, effect in rules
        if action in {"*", "edit"} and fnmatchcase(path, resource)
    ]
    assert matching[-1] == "deny"


@pytest.mark.parametrize("path", [
    "AGENTS.md",
    "docs/edition-protocol.wiki",
    ".opencode/skills/mgwiki-edition/SKILL.md",
    ".opencode/commands/mgtranslate.md",
    "README.wiki",
])
def test_section_strategy_is_discoverable(path: str) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    assert "mgwiki-section" in text
    assert "sections/<id>/" in text
    assert "coordinator" in text


def test_integration_requires_cross_section_checks_and_retains_work() -> None:
    text = (ROOT / "docs/edition-protocol.wiki").read_text(encoding="utf-8")
    for required in (
        "Missing, failed, or", "retain successful fragments", "evidence_files",
        "count uncertain\nitems across the entire job", "named reference definitions",
        "section anchors", "image/link coverage", "only the coordinator sets review.json",
    ):
        assert required in text
