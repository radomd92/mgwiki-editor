"""Pure policy decisions, not execution, authentication, or proof of editorial quality.

Used by the scoped gateway/recovery controller, never as caller authentication.
Gateway verifies facts, reserves operations, and rechecks mutable inputs at effects.
Python callers can construct facts/roles; these dataclasses are not capabilities.
No imports from core/network, filesystem access, wall-clock reads, or global state.
"""

import math
import unicodedata
from dataclasses import dataclass, fields, is_dataclass
from enum import StrEnum
from types import UnionType
from typing import get_args, get_origin

POLICY_VERSION = "1"
REQUEST_SCHEMA = 1
# Unix seconds through year 9999; reject unrepresentable/absurd clocks fail-closed.
MAX_TIMESTAMP = 253402300799


class Outcome(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    DEFER = "DEFER"


class Role(StrEnum):
    COORDINATOR = "coordinator"
    SECTION_WORKER = "section_worker"
    ISSUE_SOLVER = "issue_solver"


class Operation(StrEnum):
    READ_SOURCE = "read_source"
    LOOKUP_DICTIONARY = "lookup_dictionary"
    RENDER_PREVIEW = "render_preview"
    ACCEPT_SECTION = "accept_section"
    ACCEPT_ISSUE = "accept_issue"
    PREPARE = "prepare"
    PUBLISH = "publish"
    RECONCILE_SAVE = "reconcile_save"
    RETRY_READ = "retry_read"
    CONFIRM_OUTAGE = "confirm_outage"
    SKIP_TASKS = "skip_tasks"
    EMIT_OUTAGE_ALERT = "emit_outage_alert"


class Stage(StrEnum):
    INTAKE = "intake"
    PINNED = "pinned"
    PLANNED = "planned"
    ASSEMBLED = "assembled"
    REVIEWED = "reviewed"
    PREPARED = "prepared"
    SAVE_UNCONFIRMED = "save_unconfirmed"
    CONFIRMED = "confirmed"


class RunIntent(StrEnum):
    SANDBOX_EDIT = "sandbox_edit"
    DRAFT_ONLY = "draft_only"
    DEVELOPMENT = "development"


class ReceiptState(StrEnum):
    ABSENT = "absent"
    UNCONFIRMED = "unconfirmed"
    CONFIRMED = "confirmed"


class Rule(StrEnum):
    ALLOWED = "POLICY.ALLOWED"
    INVALID_INPUT = "POLICY.INVALID_INPUT"
    REQUIRED_FACTS = "FACTS.REQUIRED"
    COORDINATOR_ONLY = "ROLE.COORDINATOR_ONLY"
    ENDPOINT = "NET.ENDPOINT_ALLOWED"
    DEADLINE = "NET.RETRY_DEADLINE"
    SANDBOX = "SAVE.SANDBOX_ONLY"
    ACCOUNT = "SAVE.FIXED_ACCOUNT"
    INTENT = "SAVE.AUTHORIZED_INTENT"
    NO_REPLAY = "SAVE.NO_UNCERTAIN_REPLAY"
    STAGE = "WORKFLOW.STAGE"
    SECTIONS = "SECTION.REQUIRED_COMPLETE"
    BLOCKERS = "EDITORIAL.MATERIAL_BLOCKERS"
    REVIEW = "EDITORIAL.REVIEW_RECORDED"
    REVIEW_INPUTS = "EVIDENCE.REVIEW_INPUTS_MATCH"
    PROPOSAL = "EVIDENCE.PROPOSAL_MATCHES"
    LIVE_REVISIONS = "EVIDENCE.LIVE_REVISIONS_MATCH"
    LIVE_RENDER = "EVIDENCE.LIVE_RENDER_MATCHES"
    ASSIGNMENT = "ASSIGNMENT.EXACT_SCOPE"
    ASSIGNMENT_EVIDENCE = "ASSIGNMENT.EVIDENCE_CHECKED"
    SAFE_RETRY = "RETRY.SAFE_READ_ONLY"
    RETRY_CLASS = "RETRY.GENUINE_5XX"
    LOOKUP_BUDGET = "RETRY.LOOKUP_BUDGET"
    RETRY_WINDOW = "RETRY.RECOVERY_WINDOW"
    OUTAGE_HISTORY = "OUTAGE.VERIFIED_HISTORY"
    OUTAGE_PROBE = "OUTAGE.REAL_PROBE"
    OUTAGE_TIME = "OUTAGE.CONFIRMED_600S"
    PROBE_FRESHNESS = "OUTAGE.PROBE_FRESHNESS"
    DEPENDENCIES = "OUTAGE.DEPENDENT_TASKS"
    ALERT_COUNT = "OUTAGE.ALERT_26"
    ALERT_PROBE = "OUTAGE.NEW_ALERT_PROBE"
    ALERT_ONCE = "OUTAGE.ALERT_ONCE"


@dataclass(frozen=True, slots=True)
class Request:
    operation: Operation
    role: Role
    task_ids: tuple[str, ...] = ()
    schema: int = REQUEST_SCHEMA


@dataclass(frozen=True, slots=True)
class NetworkFacts:
    endpoint_permitted: bool | None = None
    # Verified maximum of existing shared request/edit/cooldown deadlines, not a new gate.
    next_request_at: float | None = None


@dataclass(frozen=True, slots=True)
class TargetFacts:
    site: str | None = None
    title: str | None = None
    namespace: int | None = None
    account: str | None = None


@dataclass(frozen=True, slots=True)
class WorkflowFacts:
    stage: Stage | None = None
    intent: RunIntent | None = None
    receipt: ReceiptState | None = None
    required_sections_complete: bool | None = None
    # Empty tuple = checked, none found. None = not checked. Source issues separate.
    material_blockers: tuple[str, ...] | None = None
    open_source_issue_ids: tuple[str, ...] = ()
    review_recorded: bool | None = None
    review_inputs_match: bool | None = None
    proposal_matches: bool | None = None
    live_revisions_match: bool | None = None
    live_render_matches: bool | None = None


@dataclass(frozen=True, slots=True)
class AssignmentFacts:
    assigned_id: str | None = None
    submitted_id: str | None = None
    output_scope_verified: bool | None = None
    evidence_checked: bool | None = None


@dataclass(frozen=True, slots=True)
class RetryFacts:
    operation: Operation | None = None
    failure_status: int | None = None
    backend_missing_page: bool | None = None
    first_failure_at: float | None = None
    last_failure_at: float | None = None
    retry_after_at: float | None = None
    # Actual retries after initial lookup; exhaustion must never be reset for a probe.
    lookup_retries_used: int | None = None


@dataclass(frozen=True, slots=True)
class RecoveryFacts:
    service_id: str | None = None
    episode_id: str | None = None
    history_verified: bool | None = None
    clock_verified: bool | None = None
    first_failure_at: float | None = None
    last_success_at: float | None = None
    probe_id: str | None = None
    probe_at: float | None = None
    probe_status: int | None = None
    probe_is_real_read: bool | None = None
    probe_backend_missing_page: bool | None = None
    dependent_task_ids: tuple[str, ...] | None = None
    skipped_task_ids: tuple[str, ...] | None = None
    threshold_reached_at: float | None = None
    threshold_probe_id: str | None = None
    alert_emitted: bool | None = None


@dataclass(frozen=True, slots=True)
class Facts:
    network: NetworkFacts | None = None
    target: TargetFacts | None = None
    workflow: WorkflowFacts | None = None
    assignment: AssignmentFacts | None = None
    retry: RetryFacts | None = None
    recovery: RecoveryFacts | None = None


@dataclass(frozen=True, slots=True)
class Finding:
    rule_id: Rule
    outcome: Outcome
    reason: str
    required_evidence: tuple[str, ...] = ()
    next_eligible_at: float | None = None


@dataclass(frozen=True, slots=True)
class Decision:
    outcome: Outcome
    findings: tuple[Finding, ...]
    next_eligible_at: float | None = None
    policy_version: str = POLICY_VERSION

    @property
    def rule_ids(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item.rule_id.value for item in self.findings))

    @property
    def required_evidence(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(
            name for item in self.findings for name in item.required_evidence
        ))

    def as_dict(self) -> dict:
        """Return detached JSON-compatible diagnostics, never an execution token."""
        return {
            "outcome": self.outcome.value, "policy_version": self.policy_version,
            "rule_ids": list(self.rule_ids), "required_evidence": list(self.required_evidence),
            "next_eligible_at": self.next_eligible_at,
            "findings": [{"rule_id": item.rule_id.value, "outcome": item.outcome.value,
                          "reason": item.reason,
                          "required_evidence": list(item.required_evidence),
                          "next_eligible_at": item.next_eligible_at} for item in self.findings],
        }


def _timestamp(value: object) -> bool:
    return (
        type(value) in {int, float} and 0 <= value <= MAX_TIMESTAMP and math.isfinite(value)
    )


def _typed(value: object, annotation: object) -> bool:
    """Strict validation of our closed, immutable schema; no coercion/eval/JSON parser."""
    origin, args = get_origin(annotation), get_args(annotation)
    if origin is UnionType:
        return any(_typed(value, part) for part in args)
    if origin is tuple:
        return type(value) is tuple and all(_typed(part, args[0]) for part in value)
    if annotation is float:
        return _timestamp(value)
    if type(value) is not annotation:
        return False
    if annotation is str:
        return bool(value.strip()) and not any(
            unicodedata.category(c).startswith("C") for c in value
        )
    if is_dataclass(value):
        return all(_typed(getattr(value, field.name), field.type) for field in fields(value))
    return True


class _Checks:
    """Evaluation-local accumulator. DENY beats DEFER; no external state changes."""

    def __init__(self) -> None:
        self.findings: list[Finding] = []

    def add(
        self, rule: Rule, outcome: Outcome, reason: str, evidence: tuple[str, ...] = (),
        deadline: float | None = None,
    ) -> None:
        self.findings.append(Finding(rule, outcome, reason, evidence, deadline))

    def require(self, value: bool | None, rule: Rule, evidence: str, reason: str) -> None:
        if value is not True:
            self.add(rule, Outcome.DEFER if value is None else Outcome.DENY,
                     reason, (evidence,))

    def present(self, value: object, evidence: str) -> bool:
        if value is None:
            self.add(Rule.REQUIRED_FACTS, Outcome.DEFER, "Required fact missing.", (evidence,))
            return False
        return True

    def ready(self, deadline: float | None, now: float, evidence: str) -> None:
        if self.present(deadline, evidence) and deadline > now:
            self.add(Rule.DEADLINE, Outcome.DEFER, "Persisted cooldown not elapsed.",
                     (evidence,), deadline)

    def decision(self) -> Decision:
        if not self.findings:
            return Decision(Outcome.ALLOW, (
                Finding(Rule.ALLOWED, Outcome.ALLOW, "Supplied facts satisfy applicable rules."),
            ))
        outcome = (Outcome.DENY if any(f.outcome is Outcome.DENY for f in self.findings)
                   else Outcome.DEFER)
        deadlines = [f.next_eligible_at for f in self.findings if f.next_eligible_at is not None]
        # A known deadline is a lower bound, not a promise that missing evidence will appear.
        deadline = max(deadlines) if deadlines and outcome is Outcome.DEFER else None
        return Decision(outcome, tuple(self.findings), deadline)


def _network(checks: _Checks, facts: NetworkFacts | None, now: float) -> None:
    if not checks.present(facts, "network"):
        return
    checks.require(facts.endpoint_permitted, Rule.ENDPOINT, "network.endpoint_permitted",
                   "Endpoint must be permitted for this operation.")
    checks.ready(facts.next_request_at, now, "network.next_request_at")


def _canonical_sandbox(value: str) -> bool:
    prefix = "Mpikambana:Bot-Jagwar/"
    if not value.startswith(prefix):
        return False
    article = value[len(prefix):]
    canonical = unicodedata.normalize("NFC", article.replace("_", " ").strip())
    try:
        return (
            bool(article) and article == canonical and len(article.encode("utf-8")) <= 220
            and len(value.encode("utf-8")) <= 255 and not article.startswith(":")
            and not article.casefold().startswith(("mpikambana:", "user:"))
            and not any(c in article for c in "#|[]{}<>")
        )
    except UnicodeError:
        return False


def _target(checks: _Checks, facts: TargetFacts | None, *, account: bool = False) -> None:
    if not checks.present(facts, "target"):
        return
    for field in ("site", "title", "namespace"):
        value = getattr(facts, field)
        if checks.present(value, f"target.{field}"):
            valid = (value == "mg.wikipedia.org" if field == "site" else
                     value == 2 if field == "namespace" else _canonical_sandbox(value))
            checks.require(valid, Rule.SANDBOX, f"target.{field}",
                           "Exact Bot-Jagwar Malagasy sandbox required.")
    if account:
        checks.require(None if facts.account is None else facts.account == "Bot-Jagwar",
                       Rule.ACCOUNT, "target.account", "Authenticated account must be Bot-Jagwar.")


def _stage(checks: _Checks, facts: WorkflowFacts, expected: Stage) -> None:
    checks.require(None if facts.stage is None else facts.stage is expected,
                   Rule.STAGE, "workflow.stage", "Operation not valid at this workflow stage.")


def _editorial(checks: _Checks, facts: WorkflowFacts) -> None:
    checks.require(facts.required_sections_complete, Rule.SECTIONS,
                   "workflow.required_sections_complete", "All required sections must be complete.")
    checks.require(None if facts.material_blockers is None else not facts.material_blockers,
                   Rule.BLOCKERS, "workflow.material_blockers", "Material blockers unresolved.")
    checks.require(facts.review_recorded, Rule.REVIEW,
                   "workflow.review_recorded", "Autonomous editorial review must be recorded.")
    checks.require(facts.review_inputs_match, Rule.REVIEW_INPUTS,
                   "workflow.review_inputs_match", "Review must bind the current exact inputs.")
    # open_source_issue_ids intentionally do not fail any gate.


def _workflow(checks: _Checks, operation: Operation, facts: WorkflowFacts | None) -> None:
    if not checks.present(facts, "workflow"):
        return
    if operation is Operation.RECONCILE_SAVE:
        _stage(checks, facts, Stage.SAVE_UNCONFIRMED)
        checks.require(None if facts.receipt is None else facts.receipt is ReceiptState.UNCONFIRMED,
                       Rule.NO_REPLAY, "workflow.receipt", "Unconfirmed receipt required.")
        return  # Read-only reconciliation must not require the publication gates to pass.
    _stage(checks, facts, Stage.REVIEWED if operation is Operation.PREPARE else Stage.PREPARED)
    _editorial(checks, facts)
    checks.require(None if facts.receipt is None else facts.receipt is ReceiptState.ABSENT,
                   Rule.NO_REPLAY, "workflow.receipt", "Prior save attempt forbids resubmission.")
    checks.require(facts.live_revisions_match, Rule.LIVE_REVISIONS,
                   "workflow.live_revisions_match", "Pinned live revisions must still match.")
    if operation is Operation.PUBLISH:
        checks.require(None if facts.intent is None else facts.intent is RunIntent.SANDBOX_EDIT,
                       Rule.INTENT, "workflow.intent", "Translation/edit intent required for save.")
        checks.require(facts.proposal_matches, Rule.PROPOSAL,
                       "workflow.proposal_matches", "Exact prepared proposal must still match.")
        checks.require(facts.live_render_matches, Rule.LIVE_RENDER,
                       "workflow.live_render_matches", "Live render must match reviewed preview.")


def _assignment(checks: _Checks, facts: AssignmentFacts | None) -> None:
    if not checks.present(facts, "assignment"):
        return
    assigned = checks.present(facts.assigned_id, "assignment.assigned_id")
    submitted = checks.present(facts.submitted_id, "assignment.submitted_id")
    if assigned and submitted:
        checks.require(facts.assigned_id == facts.submitted_id, Rule.ASSIGNMENT,
                       "assignment.submitted_id", "Submission must match exact assigned ID.")
    checks.require(facts.output_scope_verified, Rule.ASSIGNMENT,
                   "assignment.output_scope_verified", "Output must stay inside assigned scope.")
    checks.require(facts.evidence_checked, Rule.ASSIGNMENT_EVIDENCE,
                   "assignment.evidence_checked", "Coordinator must check submitted evidence.")


def _retry(checks: _Checks, facts: RetryFacts | None, now: float) -> None:
    if not checks.present(facts, "retry"):
        return
    safe = {Operation.READ_SOURCE, Operation.LOOKUP_DICTIONARY, Operation.RENDER_PREVIEW}
    checks.require(None if facts.operation is None else facts.operation in safe,
                   Rule.SAFE_RETRY, "retry.operation", "Only idempotent reads may be retried.")
    checks.require(None if facts.failure_status is None else 500 <= facts.failure_status <= 599,
                   Rule.RETRY_CLASS, "retry.failure_status", "Genuine HTTP 5xx required.")
    checks.require(None if facts.backend_missing_page is None else not facts.backend_missing_page,
                   Rule.RETRY_CLASS, "retry.backend_missing_page", "NoPage is missing, not outage.")
    if facts.operation is Operation.LOOKUP_DICTIONARY:
        checks.require(None if facts.lookup_retries_used is None else
                       0 <= facts.lookup_retries_used < 10, Rule.LOOKUP_BUDGET,
                       "retry.lookup_retries_used", "Dictionary ten-retry budget must remain.")
    if checks.present(facts.last_failure_at, "retry.last_failure_at"):
        checks.require(facts.last_failure_at <= now, Rule.INVALID_INPUT,
                       "retry.last_failure_at", "Failure cannot be in the future.")
        checks.ready(facts.last_failure_at + 15, now, "retry.minimum_cooldown")
    checks.ready(facts.retry_after_at, now, "retry.retry_after_at")
    if checks.present(facts.first_failure_at, "retry.first_failure_at"):
        if facts.last_failure_at is not None:
            checks.require(facts.first_failure_at <= facts.last_failure_at, Rule.INVALID_INPUT,
                           "retry.first_failure_at", "Failure history must be ordered.")
        if now >= facts.first_failure_at + 600:
            checks.add(Rule.RETRY_WINDOW, Outcome.DEFER,
                       "Recovery window elapsed; perform permitted outage probe instead.",
                       ("recovery",))


def _recovery(checks: _Checks, request: Request, facts: RecoveryFacts | None, now: float) -> None:
    if not checks.present(facts, "recovery"):
        return
    for field in ("service_id", "episode_id", "probe_id"):
        checks.present(getattr(facts, field), f"recovery.{field}")
    checks.require(facts.history_verified, Rule.OUTAGE_HISTORY, "recovery.history_verified",
                   "Episode history must be verified, not inferred from elapsed time.")
    checks.require(facts.clock_verified, Rule.OUTAGE_HISTORY, "recovery.clock_verified",
                   "Elapsed-time evidence must survive clock/restart ambiguity.")
    checks.require(facts.probe_is_real_read, Rule.OUTAGE_PROBE, "recovery.probe_is_real_read",
                   "Cached failures and gate refusals are not service probes.")
    checks.require(None if facts.probe_status is None else 500 <= facts.probe_status <= 599,
                   Rule.OUTAGE_PROBE, "recovery.probe_status", "Probe must return genuine 5xx.")
    checks.require(None if facts.probe_backend_missing_page is None else
                   not facts.probe_backend_missing_page, Rule.OUTAGE_PROBE,
                   "recovery.probe_backend_missing_page", "NoPage is not an outage probe.")
    if checks.present(facts.first_failure_at, "recovery.first_failure_at"):
        if facts.last_success_at is not None and facts.last_success_at >= facts.first_failure_at:
            checks.add(Rule.OUTAGE_HISTORY, Outcome.DENY,
                       "Service success ended this outage episode.", ("recovery.episode_id",))
        if checks.present(facts.probe_at, "recovery.probe_at"):
            if facts.probe_at < facts.first_failure_at + 600:
                checks.add(Rule.OUTAGE_TIME, Outcome.DEFER,
                           "Real failed probe at/after ten minutes required.",
                           ("recovery.probe_at",), facts.first_failure_at + 600)
            if not facts.first_failure_at <= facts.probe_at <= now:
                checks.add(Rule.INVALID_INPUT, Outcome.DENY, "Probe timestamps inconsistent.")
    if facts.probe_at is not None and now - facts.probe_at > 15:
        checks.add(Rule.PROBE_FRESHNESS, Outcome.DEFER, "Probe stale; retest when permitted.",
                   ("recovery.probe_at",))
    if facts.last_success_at is not None and facts.last_success_at > now:
        checks.add(Rule.INVALID_INPUT, Outcome.DENY, "Success timestamp cannot be in the future.")
    if request.operation in {Operation.SKIP_TASKS, Operation.EMIT_OUTAGE_ALERT}:
        if checks.present(facts.dependent_task_ids, "recovery.dependent_task_ids"):
            tasks = (request.task_ids if request.operation is Operation.SKIP_TASKS
                     else facts.skipped_task_ids)
            if checks.present(tasks, "recovery.skipped_task_ids"):
                checks.require(bool(tasks) and set(tasks) <= set(facts.dependent_task_ids),
                               Rule.DEPENDENCIES, "recovery.dependent_task_ids",
                               "Only tasks dependent on this service/episode may be skipped.")
    if request.operation is Operation.EMIT_OUTAGE_ALERT:
        if checks.present(facts.skipped_task_ids, "recovery.skipped_task_ids"):
            checks.require(len(set(facts.skipped_task_ids)) >= 26, Rule.ALERT_COUNT,
                           "recovery.skipped_task_ids", "26 distinct skipped tasks required.")
        checks.require(None if facts.alert_emitted is None else not facts.alert_emitted,
                       Rule.ALERT_ONCE, "recovery.alert_emitted", "Episode alert already emitted.")
        if checks.present(facts.threshold_probe_id, "recovery.threshold_probe_id"):
            checks.require(None if facts.probe_id is None else
                           facts.probe_id != facts.threshold_probe_id, Rule.ALERT_PROBE,
                           "recovery.probe_id", "New real probe required after skip threshold.")
        if checks.present(facts.threshold_reached_at, "recovery.threshold_reached_at"):
            if facts.first_failure_at is not None:
                checks.require(facts.threshold_reached_at >= facts.first_failure_at + 600,
                               Rule.ALERT_PROBE, "recovery.threshold_reached_at",
                               "Confirmed skips cannot precede outage confirmation window.")
            checks.require(None if facts.probe_at is None else
                           facts.threshold_reached_at <= facts.probe_at <= now, Rule.ALERT_PROBE,
                           "recovery.probe_at", "Alert probe must follow threshold crossing.")


def evaluate(request: Request, facts: Facts, now: float) -> Decision:
    """Evaluate supplied facts only; does not observe, execute, authenticate, or mutate."""
    checks = _Checks()
    if (not _typed(request, Request) or not _typed(facts, Facts) or not _timestamp(now)
            or request.schema != REQUEST_SCHEMA):
        checks.add(Rule.INVALID_INPUT, Outcome.DENY,
                   "Unknown schema/operation/role or malformed facts/time; no coercion.")
        return checks.decision()
    checks.require(request.role is Role.COORDINATOR, Rule.COORDINATOR_ONLY,
                   "request.role", "Operation requires verified coordinator identity.")
    operation = request.operation
    remote = {
        Operation.READ_SOURCE, Operation.LOOKUP_DICTIONARY, Operation.RENDER_PREVIEW,
        Operation.PREPARE, Operation.PUBLISH, Operation.RECONCILE_SAVE, Operation.RETRY_READ,
    }
    if operation in remote:
        _network(checks, facts.network, now)
    if operation in {
        Operation.RENDER_PREVIEW, Operation.PREPARE, Operation.PUBLISH, Operation.RECONCILE_SAVE,
    }:
        _target(checks, facts.target, account=operation is Operation.PUBLISH)
    if operation in {Operation.PREPARE, Operation.PUBLISH, Operation.RECONCILE_SAVE}:
        _workflow(checks, operation, facts.workflow)
    if operation in {Operation.ACCEPT_SECTION, Operation.ACCEPT_ISSUE}:
        _assignment(checks, facts.assignment)
    if operation is Operation.RETRY_READ:
        _retry(checks, facts.retry, now)
        if facts.retry is not None and facts.retry.operation is Operation.RENDER_PREVIEW:
            _target(checks, facts.target)
    if operation in {
        Operation.CONFIRM_OUTAGE, Operation.SKIP_TASKS, Operation.EMIT_OUTAGE_ALERT,
    }:
        _recovery(checks, request, facts.recovery, now)
    return checks.decision()


def transition(current: Stage, following: Stage) -> bool:
    """Check workflow topology only, never permission/evidence or an execution grant.

    Input changes return planned/assembled/reviewed/prepared work to PINNED for
    targeted revalidation. Unconfirmed/confirmed save jobs cannot be reused.
    """
    if type(current) is not Stage or type(following) is not Stage:
        return False
    forward = {
        Stage.INTAKE: Stage.PINNED, Stage.PINNED: Stage.PLANNED,
        Stage.PLANNED: Stage.ASSEMBLED, Stage.ASSEMBLED: Stage.REVIEWED,
        Stage.REVIEWED: Stage.PREPARED, Stage.PREPARED: Stage.SAVE_UNCONFIRMED,
        Stage.SAVE_UNCONFIRMED: Stage.CONFIRMED,
    }
    invalidatable = {Stage.PLANNED, Stage.ASSEMBLED, Stage.REVIEWED, Stage.PREPARED}
    return forward.get(current) is following or (
        current in invalidatable and following is Stage.PINNED
    )
