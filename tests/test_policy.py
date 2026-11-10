"""Pure decision tests: supplied facts only, never live services or publication."""

import builtins
import importlib.util
import json
import socket
import sys
import time
from dataclasses import FrozenInstanceError, replace
from itertools import product
from pathlib import Path

import pytest

from mgwiki_editor import policy
from mgwiki_editor.core import GuardError, sandbox_title
from mgwiki_editor.policy import (
    POLICY_VERSION,
    AssignmentFacts,
    Facts,
    NetworkFacts,
    Operation,
    Outcome,
    ReceiptState,
    RecoveryFacts,
    Request,
    RetryFacts,
    Role,
    Rule,
    RunIntent,
    Stage,
    TargetFacts,
    WorkflowFacts,
    evaluate,
    transition,
)

NOW = 1615
TASKS = tuple(f"section-{number:02d}" for number in range(26))


def good_facts(operation: Operation = Operation.PUBLISH) -> Facts:
    """Controller-like complete fixture; booleans do not prove facts outside this test."""
    stage, receipt = Stage.PREPARED, ReceiptState.ABSENT
    if operation is Operation.PREPARE:
        stage = Stage.REVIEWED
    elif operation is Operation.RECONCILE_SAVE:
        stage, receipt = Stage.SAVE_UNCONFIRMED, ReceiptState.UNCONFIRMED
    return Facts(
        network=NetworkFacts(endpoint_permitted=True, next_request_at=0),
        target=TargetFacts(site="mg.wikipedia.org", title="Mpikambana:Bot-Jagwar/Rano",
                           namespace=2, account="Bot-Jagwar"),
        workflow=WorkflowFacts(
            stage=stage, intent=RunIntent.SANDBOX_EDIT, receipt=receipt,
            required_sections_complete=True, material_blockers=(), review_recorded=True,
            review_inputs_match=True, proposal_matches=True, live_revisions_match=True,
            live_render_matches=True,
        ),
        assignment=AssignmentFacts(assigned_id="section-00", submitted_id="section-00",
                                   output_scope_verified=True, evidence_checked=True),
        retry=RetryFacts(operation=Operation.LOOKUP_DICTIONARY, failure_status=502,
                         backend_missing_page=False, first_failure_at=1100, last_failure_at=1600,
                         retry_after_at=1615, lookup_retries_used=0),
        recovery=RecoveryFacts(
            service_id="dictionary:configured", episode_id="episode-1", history_verified=True,
            clock_verified=True, first_failure_at=1000, probe_id="probe-3", probe_at=1615,
            probe_status=502, probe_is_real_read=True, probe_backend_missing_page=False,
            dependent_task_ids=TASKS, skipped_task_ids=TASKS, threshold_reached_at=1600,
            threshold_probe_id="probe-2", alert_emitted=False,
        ),
    )


def decide(operation: Operation, facts: Facts, now: float = NOW):
    return evaluate(Request(operation, Role.COORDINATOR, task_ids=TASKS), facts, now)


@pytest.mark.parametrize("operation", list(Operation))
def test_complete_applicable_facts_allow_each_operation(operation: Operation) -> None:
    result = decide(operation, good_facts(operation))
    assert result.outcome is Outcome.ALLOW
    assert result.rule_ids == (Rule.ALLOWED.value,)
    assert result.next_eligible_at is None


@pytest.mark.parametrize("operation", list(Operation))
def test_missing_facts_never_allow_operation(operation: Operation) -> None:
    result = decide(operation, Facts())
    assert result.outcome is Outcome.DEFER
    assert result.required_evidence


@pytest.mark.parametrize("operation,role", list(product(Operation, (
    Role.SECTION_WORKER, Role.ISSUE_SOLVER,
))))
def test_workers_cannot_request_coordinator_operations(operation: Operation, role: Role) -> None:
    result = evaluate(Request(operation, role, task_ids=TASKS), good_facts(operation), NOW)
    assert result.outcome is Outcome.DENY
    assert Rule.COORDINATOR_ONLY.value in result.rule_ids


@pytest.mark.parametrize("candidate", [
    None, {}, "publish", Request("publish", Role.COORDINATOR),
    Request(Operation.PUBLISH, "coordinator"), Request(Operation.PUBLISH, None),
    Request(Operation.PUBLISH, Role.COORDINATOR, schema=2),
    Request(Operation.PUBLISH, Role.COORDINATOR, schema=True),
    Request(Operation.PUBLISH, Role.COORDINATOR, task_ids=["task"]),
    Request(Operation.PUBLISH, Role.COORDINATOR, task_ids=("",)),
])
def test_unknown_or_untyped_requests_denied_without_coercion(candidate) -> None:
    result = evaluate(candidate, good_facts(), NOW)
    assert result.outcome is Outcome.DENY
    assert result.rule_ids == (Rule.INVALID_INPUT.value,)


@pytest.mark.parametrize("now", [
    None, True, -1, "1615", float("nan"), float("inf"), 10 ** 999, 1e308,
    policy.MAX_TIMESTAMP + 1,
])
def test_invalid_clock_input_denied(now) -> None:
    result = decide(Operation.PUBLISH, good_facts(), now)
    assert result.outcome is Outcome.DENY
    assert result.rule_ids == (Rule.INVALID_INPUT.value,)


@pytest.mark.parametrize("facts", [
    None, {}, Facts(network={"endpoint_permitted": True}),
    Facts(network=NetworkFacts(endpoint_permitted=1, next_request_at=0)),
    Facts(network=NetworkFacts(endpoint_permitted=True, next_request_at=True)),
    Facts(network=NetworkFacts(endpoint_permitted=True, next_request_at=float("nan"))),
    Facts(target=TargetFacts(namespace=True)),
    Facts(workflow=WorkflowFacts(stage="prepared")),
    Facts(workflow=WorkflowFacts(material_blockers=[])),
    Facts(workflow=WorkflowFacts(material_blockers=("",))),
    Facts(retry=RetryFacts(lookup_retries_used=True)),
    Facts(recovery=RecoveryFacts(probe_status="502")),
])
def test_malformed_facts_fail_closed(facts) -> None:
    result = decide(Operation.PUBLISH, facts)
    assert result.outcome is Outcome.DENY
    assert result.rule_ids == (Rule.INVALID_INPUT.value,)


def test_denial_wins_over_deferral_and_does_not_offer_retry_deadline() -> None:
    facts = replace(good_facts(), network=NetworkFacts(False, NOW + 900))
    result = decide(Operation.PUBLISH, facts)
    assert result.outcome is Outcome.DENY
    assert result.next_eligible_at is None
    assert {item.outcome for item in result.findings} == {Outcome.DENY, Outcome.DEFER}


def test_network_deadline_is_lower_bound_not_automatic_permission() -> None:
    facts = replace(good_facts(), network=NetworkFacts(None, NOW + 90))
    result = decide(Operation.READ_SOURCE, facts)
    assert result.outcome is Outcome.DEFER
    assert result.next_eligible_at == NOW + 90
    assert "network.endpoint_permitted" in result.required_evidence
    assert decide(Operation.READ_SOURCE, facts, NOW + 90).outcome is Outcome.DEFER


@pytest.mark.parametrize("offset,expected", [(-1, Outcome.ALLOW), (0, Outcome.ALLOW),
                                              (1, Outcome.DEFER)])
def test_network_deadline_boundary(offset: int, expected: Outcome) -> None:
    facts = replace(good_facts(), network=NetworkFacts(True, NOW + offset))
    assert decide(Operation.READ_SOURCE, facts).outcome is expected


@pytest.mark.parametrize("field,value", [
    ("site", "en.wikipedia.org"), ("site", "mg.wikipedia.org.example.org"),
    ("namespace", 0), ("namespace", 3),
    ("title", "Rano"), ("title", "Mpikambana:Other/Rano"),
    ("title", "Mpikambana:Bot-Jagwar/"), ("title", "Mpikambana:Bot-Jagwar/Rano_madio"),
    ("title", "Mpikambana:Bot-Jagwar/ Rano"), ("title", "Mpikambana:Bot-Jagwar/Rano#A"),
    ("title", "Mpikambana:Bot-Jagwar/[[Rano]]"), ("title", "Mpikambana:Bot-Jagwar/:Rano"),
    ("title", "Mpikambana:Bot-Jagwar/USER:Other/Rano"),
    ("title", "Mpikambana:Bot-Jagwar/" + "x" * 221),
    ("account", "Other"), ("account", "bot-jagwar"),
])
def test_publish_requires_fixed_account_and_exact_canonical_sandbox(field, value) -> None:
    facts = good_facts()
    facts = replace(facts, target=replace(facts.target, **{field: value}))
    result = decide(Operation.PUBLISH, facts)
    assert result.outcome is Outcome.DENY
    assert (Rule.ACCOUNT if field == "account" else Rule.SANDBOX).value in result.rule_ids


@pytest.mark.parametrize("article", [
    "Rano", " Rano_madio ", "Star Trek: Voyager", "Équation", "A\u0301", "x" * 220,
    "", "USER:Other/Rano", ":Rano", "Rano#A", "[[Rano]]", "Rano\nX", "x" * 221,
])
def test_target_predicate_agrees_with_existing_title_constructor(article: str) -> None:
    facts = good_facts()
    try:
        target = sandbox_title(article)
    except GuardError:
        target = "Mpikambana:Bot-Jagwar/" + article
        expected = Outcome.DENY
    else:
        expected = Outcome.ALLOW
    facts = replace(facts, target=replace(facts.target, title=target))
    assert decide(Operation.PUBLISH, facts).outcome is expected


@pytest.mark.parametrize("field", ["site", "title", "namespace", "account"])
def test_missing_target_fact_defers(field: str) -> None:
    facts = good_facts()
    facts = replace(facts, target=replace(facts.target, **{field: None}))
    assert decide(Operation.PUBLISH, facts).outcome is Outcome.DEFER


@pytest.mark.parametrize("intent", [RunIntent.DRAFT_ONLY, RunIntent.DEVELOPMENT])
def test_nonpublishing_intent_allows_preparation_but_denies_publication(intent: RunIntent) -> None:
    facts = good_facts(Operation.PREPARE)
    facts = replace(facts, workflow=replace(facts.workflow, intent=intent))
    assert decide(Operation.PREPARE, facts).outcome is Outcome.ALLOW
    facts = replace(facts, workflow=replace(facts.workflow, stage=Stage.PREPARED))
    result = decide(Operation.PUBLISH, facts)
    assert result.outcome is Outcome.DENY
    assert Rule.INTENT.value in result.rule_ids


@pytest.mark.parametrize("field,rule", [
    ("required_sections_complete", Rule.SECTIONS), ("review_recorded", Rule.REVIEW),
    ("review_inputs_match", Rule.REVIEW_INPUTS), ("proposal_matches", Rule.PROPOSAL),
    ("live_revisions_match", Rule.LIVE_REVISIONS), ("live_render_matches", Rule.LIVE_RENDER),
])
@pytest.mark.parametrize("value,outcome", [(False, Outcome.DENY), (None, Outcome.DEFER)])
def test_publish_requires_every_relevant_positive_check(field, rule, value, outcome) -> None:
    facts = good_facts()
    facts = replace(facts, workflow=replace(facts.workflow, **{field: value}))
    result = decide(Operation.PUBLISH, facts)
    assert result.outcome is outcome
    assert rule.value in result.rule_ids


def test_source_disagreements_do_not_become_blockers_or_clear_material_meaning() -> None:
    facts = good_facts()
    facts = replace(facts, workflow=replace(facts.workflow, open_source_issue_ids=("SRC-01",)))
    assert decide(Operation.PUBLISH, facts).outcome is Outcome.ALLOW
    facts = replace(facts, workflow=replace(facts.workflow, material_blockers=("unknown meaning",)))
    result = decide(Operation.PUBLISH, facts)
    assert result.outcome is Outcome.DENY
    assert Rule.BLOCKERS.value in result.rule_ids
    facts = replace(facts, workflow=replace(facts.workflow, material_blockers=None))
    assert decide(Operation.PUBLISH, facts).outcome is Outcome.DEFER


@pytest.mark.parametrize("operation", [Operation.PREPARE, Operation.PUBLISH])
@pytest.mark.parametrize("receipt", [ReceiptState.UNCONFIRMED, ReceiptState.CONFIRMED])
def test_any_previous_save_attempt_prevents_reprepare_and_resubmit(operation, receipt) -> None:
    facts = good_facts(operation)
    facts = replace(facts, workflow=replace(facts.workflow, receipt=receipt))
    result = decide(operation, facts)
    assert result.outcome is Outcome.DENY
    assert Rule.NO_REPLAY.value in result.rule_ids


@pytest.mark.parametrize("operation,expected", [
    (Operation.PREPARE, Stage.REVIEWED), (Operation.PUBLISH, Stage.PREPARED),
    (Operation.RECONCILE_SAVE, Stage.SAVE_UNCONFIRMED),
])
def test_operations_require_correct_stage(operation: Operation, expected: Stage) -> None:
    facts = good_facts(operation)
    for stage in Stage:
        changed = replace(facts, workflow=replace(facts.workflow, stage=stage))
        result = decide(operation, changed)
        assert result.outcome is (Outcome.ALLOW if stage is expected else Outcome.DENY)


def test_read_only_reconciliation_does_not_require_clearing_editorial_blockers() -> None:
    facts = good_facts(Operation.RECONCILE_SAVE)
    facts = replace(facts, target=replace(facts.target, account=None), workflow=WorkflowFacts(
        stage=Stage.SAVE_UNCONFIRMED, receipt=ReceiptState.UNCONFIRMED,
        material_blockers=("unknown meaning",), intent=RunIntent.DRAFT_ONLY,
    ))
    assert decide(Operation.RECONCILE_SAVE, facts).outcome is Outcome.ALLOW
    for receipt in (None, ReceiptState.ABSENT, ReceiptState.CONFIRMED):
        changed = replace(facts, workflow=replace(facts.workflow, receipt=receipt))
        assert decide(Operation.RECONCILE_SAVE, changed).outcome is not Outcome.ALLOW


@pytest.mark.parametrize("operation", [Operation.ACCEPT_SECTION, Operation.ACCEPT_ISSUE])
@pytest.mark.parametrize("field,value,rule", [
    ("submitted_id", "other-section", Rule.ASSIGNMENT),
    ("output_scope_verified", False, Rule.ASSIGNMENT),
    ("evidence_checked", False, Rule.ASSIGNMENT_EVIDENCE),
])
def test_acceptance_requires_matching_assignment_scope_and_evidence(operation, field, value, rule):
    facts = good_facts()
    facts = replace(facts, assignment=replace(facts.assignment, **{field: value}))
    result = decide(operation, facts)
    assert result.outcome is Outcome.DENY
    assert rule.value in result.rule_ids


def test_accepting_issue_proposal_does_not_grant_publication() -> None:
    facts = Facts(assignment=good_facts().assignment)
    assert decide(Operation.ACCEPT_ISSUE, facts).outcome is Outcome.ALLOW
    assert decide(Operation.PUBLISH, facts).outcome is Outcome.DEFER


@pytest.mark.parametrize("operation", [Operation.PUBLISH, Operation.PREPARE,
                                        Operation.RECONCILE_SAVE, Operation.RETRY_READ])
def test_retry_cannot_disguise_a_write_or_reconciliation_as_safe_read(operation: Operation) -> None:
    facts = good_facts()
    facts = replace(facts, retry=replace(facts.retry, operation=operation))
    result = decide(Operation.RETRY_READ, facts)
    assert result.outcome is Outcome.DENY
    assert Rule.SAFE_RETRY.value in result.rule_ids


def test_preview_post_is_read_only_but_still_requires_sandbox_target() -> None:
    facts = good_facts()
    facts = replace(facts, retry=replace(facts.retry, operation=Operation.RENDER_PREVIEW))
    assert decide(Operation.RETRY_READ, facts).outcome is Outcome.ALLOW
    facts = replace(facts, target=replace(facts.target, title="Mainspace"))
    assert decide(Operation.RETRY_READ, facts).outcome is Outcome.DENY


@pytest.mark.parametrize("status", [200, 404, 429, 499, 600])
def test_non_5xx_not_classified_as_restart_retry(status: int) -> None:
    facts = good_facts()
    facts = replace(facts, retry=replace(facts.retry, failure_status=status))
    result = decide(Operation.RETRY_READ, facts)
    assert result.outcome is Outcome.DENY
    assert Rule.RETRY_CLASS.value in result.rule_ids


@pytest.mark.parametrize("status", [500, 502, 503, 599])
def test_all_genuine_5xx_allow_due_safe_retry_without_shortening_shared_deadline(status: int):
    facts = good_facts()
    facts = replace(facts, retry=replace(facts.retry, failure_status=status),
                    network=replace(facts.network, next_request_at=2000))
    result = decide(Operation.RETRY_READ, facts)
    assert result.outcome is Outcome.DEFER
    assert result.next_eligible_at == 2000


def test_backend_nopage_not_an_outage_retry() -> None:
    facts = good_facts()
    facts = replace(facts, retry=replace(facts.retry, backend_missing_page=True))
    result = decide(Operation.RETRY_READ, facts)
    assert result.outcome is Outcome.DENY
    assert Rule.RETRY_CLASS.value in result.rule_ids


def test_retry_waits_15_seconds_from_failed_response_and_honors_later_deadlines() -> None:
    facts = good_facts()
    assert decide(Operation.RETRY_READ, facts, 1614).next_eligible_at == 1615
    assert decide(Operation.RETRY_READ, facts, 1615).outcome is Outcome.ALLOW
    facts = replace(facts, retry=replace(facts.retry, retry_after_at=1800),
                    network=replace(facts.network, next_request_at=1700))
    assert decide(Operation.RETRY_READ, facts).next_eligible_at == 1800


@pytest.mark.parametrize("used,expected", [(-1, Outcome.DENY), (0, Outcome.ALLOW),
                                            (9, Outcome.ALLOW), (10, Outcome.DENY),
                                            (11, Outcome.DENY), (None, Outcome.DEFER)])
def test_dictionary_budget_is_ten_retries_after_initial_attempt(used, expected) -> None:
    facts = good_facts()
    facts = replace(facts, retry=replace(facts.retry, lookup_retries_used=used))
    assert decide(Operation.RETRY_READ, facts).outcome is expected


@pytest.mark.parametrize("first,last", [(1620, 1600), (1100, 1620)])
def test_inconsistent_retry_timestamps_denied(first, last) -> None:
    facts = good_facts()
    facts = replace(facts, retry=replace(facts.retry, first_failure_at=first, last_failure_at=last))
    assert decide(Operation.RETRY_READ, facts).outcome is Outcome.DENY


def test_retry_window_ends_at_600_seconds_without_fabricating_outage() -> None:
    facts = good_facts()
    assert decide(Operation.RETRY_READ, facts, 1699).outcome is Outcome.ALLOW
    result = decide(Operation.RETRY_READ, facts, 1700)
    assert result.outcome is Outcome.DEFER
    assert Rule.RETRY_WINDOW.value in result.rule_ids
    assert "recovery" in result.required_evidence


@pytest.mark.parametrize("offset,expected", [(599, Outcome.DEFER), (600, Outcome.ALLOW)])
def test_outage_requires_real_failed_probe_at_or_after_600_seconds(offset, expected):
    facts = good_facts()
    facts = replace(facts, recovery=replace(facts.recovery, probe_at=1000 + offset))
    result = decide(Operation.CONFIRM_OUTAGE, facts, 1000 + offset)
    assert result.outcome is expected
    if expected is Outcome.DEFER:
        assert Rule.OUTAGE_TIME.value in result.rule_ids
        assert result.next_eligible_at == 1600


@pytest.mark.parametrize("field,value,rule", [
    ("probe_is_real_read", False, Rule.OUTAGE_PROBE),
    ("probe_backend_missing_page", True, Rule.OUTAGE_PROBE),
    ("probe_status", 200, Rule.OUTAGE_PROBE), ("probe_status", 404, Rule.OUTAGE_PROBE),
    ("probe_status", 429, Rule.OUTAGE_PROBE),
    ("history_verified", False, Rule.OUTAGE_HISTORY),
    ("clock_verified", False, Rule.OUTAGE_HISTORY),
    ("last_success_at", 1200, Rule.OUTAGE_HISTORY),
    ("probe_at", NOW + 1, Rule.INVALID_INPUT),
    ("last_success_at", NOW + 1, Rule.INVALID_INPUT),
])
@pytest.mark.parametrize("operation", [Operation.CONFIRM_OUTAGE, Operation.SKIP_TASKS,
                                        Operation.EMIT_OUTAGE_ALERT])
def test_outage_skips_and_alert_never_accept_cached_unknown_recovered_or_future_probes(
    field, value, rule, operation,
):
    facts = good_facts()
    facts = replace(facts, recovery=replace(facts.recovery, **{field: value}))
    result = decide(operation, facts)
    assert result.outcome is Outcome.DENY
    assert rule.value in result.rule_ids


def test_outage_cannot_be_confirmed_using_only_elapsed_time() -> None:
    facts = good_facts()
    facts = replace(facts, recovery=replace(facts.recovery, probe_at=None, probe_id=None,
                                            probe_status=None, probe_is_real_read=None))
    result = decide(Operation.CONFIRM_OUTAGE, facts, 9999)
    assert result.outcome is Outcome.DEFER
    assert "recovery.probe_at" in result.required_evidence


@pytest.mark.parametrize("age,expected", [(15, Outcome.ALLOW), (15.01, Outcome.DEFER)])
def test_probe_freshness_boundary(age, expected) -> None:
    facts = good_facts()
    result = decide(Operation.SKIP_TASKS, facts, NOW + age)
    assert result.outcome is expected
    if expected is Outcome.DEFER:
        assert Rule.PROBE_FRESHNESS.value in result.rule_ids


def test_only_tasks_dependent_on_same_service_may_be_skipped() -> None:
    facts = good_facts()
    for tasks in ((), ("unrelated-service-task",), TASKS + ("unrelated",)):
        result = evaluate(Request(Operation.SKIP_TASKS, Role.COORDINATOR, tasks), facts, NOW)
        assert result.outcome is Outcome.DENY
        assert Rule.DEPENDENCIES.value in result.rule_ids


@pytest.mark.parametrize("tasks,expected", [
    (TASKS[:25], Outcome.DENY), (TASKS, Outcome.ALLOW),
    (TASKS[:25] + TASKS[:25], Outcome.DENY), (TASKS + TASKS, Outcome.ALLOW),
])
def test_severe_alert_counts_distinct_tasks_26_not_25(tasks, expected) -> None:
    facts = good_facts()
    facts = replace(facts, recovery=replace(facts.recovery, skipped_task_ids=tasks))
    result = decide(Operation.EMIT_OUTAGE_ALERT, facts)
    assert result.outcome is expected
    if expected is Outcome.DENY:
        assert Rule.ALERT_COUNT.value in result.rule_ids


@pytest.mark.parametrize("field,value,rule", [
    ("probe_id", "probe-2", Rule.ALERT_PROBE),
    ("threshold_reached_at", NOW + 1, Rule.ALERT_PROBE),
    ("threshold_reached_at", 1599, Rule.ALERT_PROBE),
    ("alert_emitted", True, Rule.ALERT_ONCE),
    ("dependent_task_ids", TASKS[:25], Rule.DEPENDENCIES),
])
def test_severe_alert_needs_new_probe_after_threshold_and_not_already_emitted(field, value, rule):
    facts = good_facts()
    facts = replace(facts, recovery=replace(facts.recovery, **{field: value}))
    result = decide(Operation.EMIT_OUTAGE_ALERT, facts)
    assert result.outcome is Outcome.DENY
    assert rule.value in result.rule_ids


@pytest.mark.parametrize("field", [
    "episode_id", "service_id", "probe_id", "probe_at", "history_verified", "clock_verified",
    "probe_status", "probe_is_real_read", "probe_backend_missing_page", "first_failure_at",
    "threshold_reached_at", "threshold_probe_id", "skipped_task_ids", "dependent_task_ids",
    "alert_emitted",
])
def test_missing_service_episode_or_alert_evidence_never_allows_alert(field) -> None:
    facts = good_facts()
    facts = replace(facts, recovery=replace(facts.recovery, **{field: None}))
    assert decide(Operation.EMIT_OUTAGE_ALERT, facts).outcome is not Outcome.ALLOW


def test_old_success_before_episode_does_not_count_as_recovery() -> None:
    facts = good_facts()
    facts = replace(facts, recovery=replace(facts.recovery, last_success_at=999))
    assert decide(Operation.CONFIRM_OUTAGE, facts).outcome is Outcome.ALLOW


def test_decisions_are_immutable_deterministic_and_json_compatible() -> None:
    facts = good_facts()
    request = Request(Operation.PUBLISH, Role.COORDINATOR)
    before = repr((request, facts))
    first = evaluate(request, facts, NOW)
    assert first == evaluate(request, facts, NOW)
    assert repr((request, facts)) == before
    assert first.policy_version == POLICY_VERSION
    encoded = first.as_dict()
    assert json.loads(json.dumps(encoded, allow_nan=False)) == encoded
    encoded["findings"][0]["reason"] = "changed"
    assert first.as_dict()["findings"][0]["reason"] != "changed"
    for obj, field in ((request, "schema"), (facts, "network"), (facts.network, "next_request_at"),
                       (first, "policy_version"), (first.findings[0], "reason")):
        with pytest.raises(FrozenInstanceError):
            setattr(obj, field, "changed")


def test_import_and_evaluation_do_not_open_data_files_read_clocks_sleep_or_use_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*args, **kwargs):
        pytest.fail("Pure policy attempted external side effect")

    spec = importlib.util.spec_from_file_location("_pure_policy_test", policy.__file__)
    fresh = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, fresh)
    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(time, "time", forbidden)
    monkeypatch.setattr(time, "sleep", forbidden)
    spec.loader.exec_module(fresh)
    result = fresh.evaluate(
        fresh.Request(fresh.Operation.READ_SOURCE, fresh.Role.COORDINATOR),
        fresh.Facts(network=fresh.NetworkFacts(True, 0)), NOW,
    )
    assert result.outcome is fresh.Outcome.ALLOW


def test_workflow_topology_has_no_shortcuts_or_save_replay() -> None:
    forward = list(Stage)
    allowed = set(zip(forward[:-1], forward[1:], strict=True))
    allowed |= {(stage, Stage.PINNED) for stage in (
        Stage.PLANNED, Stage.ASSEMBLED, Stage.REVIEWED, Stage.PREPARED,
    )}
    for current, following in product(Stage, repeat=2):
        assert transition(current, following) is ((current, following) in allowed)
    assert transition("prepared", Stage.SAVE_UNCONFIRMED) is False
    assert transition(Stage.SAVE_UNCONFIRMED, "confirmed") is False


def test_rule_inventory_covers_all_predicate_ids_and_declares_runtime_limitations() -> None:
    path = Path(__file__).resolve().parents[1] / "docs/policy-enforcement.md"
    inventory = path.read_text(encoding="utf-8")
    for rule in Rule:
        assert f"`{rule.value}`" in inventory
    for required in (
        "Connected to scoped broker execution", "Types are not capabilities",
        "predicate status does not imply mandatory runtime enforcement",
        "review", "editorial", "RequestGate", "planned",
    ):
        assert required in inventory
