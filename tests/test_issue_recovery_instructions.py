"""Offline policy regressions; not proof of agent scheduling or runtime permissions."""

import re
from fnmatch import fnmatchcase
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SOLVER = ".opencode/agents/mgwiki-issues-solver.md"


def text(path: str) -> str:
    return " ".join((ROOT / path).read_text(encoding="utf-8").split())


@pytest.mark.parametrize(
    "path",
    [
        "AGENTS.md",
        ".opencode/agents/mgwiki-editor.md",
        ".opencode/commands/mgtranslate.md",
        ".opencode/skills/mgwiki-edition/SKILL.md",
        "docs/edition-protocol.md",
        "docs/usage.md",
    ],
)
def test_entry_points_expose_deferred_memo_solver_and_recovery(path: str) -> None:
    policy = text(path)
    for required in (
        "docs/issue-recovery.md",
        "deferred-issues.md",
        "mgwiki-issues-solver",
        "issue-resolutions/<issue-id>.md",
        "600 seconds",
        "25 distinct skipped tasks",
        "SEVERE SERVICE OUTAGE DETECTED",
    ):
        assert required in policy


def test_default_autonomy_preserves_work_and_separates_blockers() -> None:
    policy = text("docs/issue-recovery.md")
    for required in (
        "Autonomous mode default unless user specifies otherwise",
        "no questions",
        "runs/<job>/deferred-issues.md",
        "runs/<run-id>/deferred-issues.md",
        "do not fabricate",
        "continue independent tasks",
        "stable task ID",
        "skipped never means complete",
        "vocabulary.json",
        "source-issues.md",
        "retain after publication/rebase",
        "final handoff",
        "Coordinator alone accepts proposals",
        "freshly prepares changed proposals",
    ):
        assert required in policy


def test_recovery_requires_real_timed_probes_and_honors_existing_guards() -> None:
    policy = text("docs/issue-recovery.md")
    for required in (
        "HTTP 500–599, including 502",
        "15 seconds after failed response",
        "Retry-After",
        "circuit breaker",
        "per-lookup budget wins",
        "Never retry uncertain writes",
        "No hidden/native retries",
        "manual shell sleep/poll loops",
        "several times",
        "600 seconds",
        "real authorized read-only request",
        "not cached failed output",
        "gate refusal",
        "defer test until allowed",
        "no intervening successful",
        "Successful/missing-page replies end continuous outage episode",
        "at most 15 seconds old",
        "do not replay that lookup or reset its budget",
        "type=error/status=502/details.type=NoPage",
        "not outage",
    ):
        assert required in policy


def test_severe_alert_boundary_count_scope_and_output_contract() -> None:
    policy = text("docs/issue-recovery.md")
    for required in (
        "More than 25 distinct tasks skipped = at least 26",
        "same continuously down service episode",
        "test service again when eligible",
        "fresh qualifying 5xx required",
        "do not inflate count",
        "Deduplicate alert per episode",
        "Emit exact line in OpenCode output, not only memo",
        "SEVERE SERVICE OUTAGE DETECTED",
        "one simple paragraph",
        "assessment",
        "count and all blocked/skipped task IDs",
        "memo path",
        "Alert never authorizes skipped review/save guards",
    ):
        assert required in policy


def solver_rules() -> list[tuple[str, str, str]]:
    frontmatter = (ROOT / SOLVER).read_text(encoding="utf-8").split("---\n", 2)[1]
    return [
        tuple(value.strip('"') for value in match)
        for match in re.findall(
            r"  - action: (.+)\n    resource: (.+)\n    effect: (allow|deny)\n",
            frontmatter,
        )
    ]


def permitted(action: str, resource: str) -> bool:
    matches = [
        effect
        for rule_action, pattern, effect in solver_rules()
        if rule_action in {"*", action} and fnmatchcase(resource, pattern)
    ]
    return bool(matches) and matches[-1] == "allow"


def test_solver_has_only_offline_tools_and_resolution_output() -> None:
    policy = text(SOLVER)
    assert "mode: subagent" in policy
    assert {action for action, _, effect in solver_rules() if effect == "allow"} == {
        "read",
        "glob",
        "grep",
        "edit",
        "skill",
    }
    assert permitted("edit", "runs/example/issue-resolutions/ISSUE-001.md")
    for required in (
        "no user questions",
        "pinned local evidence",
        "resolved-proposal/needs-evidence/still-blocked",
        "Static edit rule cannot bind dynamic assignment",
        "do not delete or rename",
        "No shell, execute, network",
        "or further subagents",
        "No nested agents",
        "Local evidence cannot prove a remote service recovered",
        "Proposal is not coordinator acceptance",
        "caveman ultra",
        "Markdown/plain text",
    ):
        assert required in policy


@pytest.mark.parametrize(
    "action",
    [
        "shell",
        "execute",
        "webfetch",
        "websearch",
        "subagent",
        "question",
    ],
)
def test_solver_rules_deny_remote_execution_and_delegation(action: str) -> None:
    assert not permitted(action, "*")


@pytest.mark.parametrize(
    "path",
    [
        "runs/example/deferred-issues.md",
        "runs/example/source-issues.md",
        "runs/example/draft.wiki",
        "runs/example/vocabulary.json",
        "runs/example/review.json",
        "runs/example/proposal.json",
        "runs/example/receipt.json",
        "runs/example/sections/00-lead/section.wiki",
        "AGENTS.md",
        "mgwiki_editor/network.py",
    ],
)
def test_solver_rules_deny_shared_inputs_and_article_edits(path: str) -> None:
    assert not permitted("edit", path)
