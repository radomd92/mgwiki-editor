"""Actual controller persistence with fake response observations and clocks only."""

from dataclasses import replace
from pathlib import Path

import pytest

from mgwiki_editor.network import RequestGate
from mgwiki_editor.observations import Observation
from mgwiki_editor.policy_store import PolicyStore, StateError
from mgwiki_editor.recovery import Recovery, RecoveryDeferred


@pytest.fixture
def rig(tmp_path: Path):
    now = [1000.0]
    store = PolicyStore(tmp_path / "policy.sqlite")
    store.create()
    gate = RequestGate(tmp_path / "gate.json", clock=lambda: now[0], jitter=lambda *a: 0)
    recovery = Recovery(store, gate, clock=lambda: now[0])
    return recovery, store, gate, now


def response(now, *, service="dictionary:configured", status=502, **kwargs):
    return Observation(service, f"probe-{now[0]}", now[0], now[0], "boot-1", status, True, **kwargs)


def register(recovery, count=26):
    for index in range(count):
        recovery.register_task("run", f"task-{index}", "dictionary:configured")
    return tuple(f"task-{index}" for index in range(count))


def test_5xx_cooldown_persists_and_longer_shared_server_deadline_wins(rig):
    recovery, store, gate, now = rig
    recovery.observe(response(now, retry_after="90"))
    with gate.state() as state:
        assert state["next_request"] == 1090
    with pytest.raises(RecoveryDeferred) as caught:
        Recovery(store, gate, clock=lambda: now[0]).before("dictionary:configured", True)
    assert caught.value.next_eligible_at == 1090
    now[0] = 1090
    recovery.before("dictionary:configured", True, "http://configured/wiktionary-pages/mg/rano")
    gate.backoff("900")
    now[0] = 1600
    with pytest.raises(Exception, match="gate budget"):
        gate.wait()


def test_600_seconds_timer_alone_does_not_skip_then_real_probe_confirms(rig):
    recovery, store, gate, now = rig
    tasks = register(recovery, 25)
    recovery.observe(response(now))
    now[0] = 1600
    with pytest.raises(RecoveryDeferred, match="probe"):
        recovery.before("dictionary:configured", True)
    recovery.before("dictionary:configured", True, probe=True)
    assert recovery.skip("run", tasks, "dictionary:configured")["skipped"] == []
    recovery.observe(response(now))
    result = recovery.skip("run", tasks[:25], "dictionary:configured")
    assert result["distinct_count"] == 25
    assert recovery.alerts("run") == []
    recovery.register_task("run", "task-25", "dictionary:configured")
    tasks += ("task-25",)
    result = recovery.skip("run", tasks, "dictionary:configured")
    assert result["distinct_count"] == 26
    assert recovery.skip("run", tasks, "dictionary:configured")["distinct_count"] == 26
    assert recovery.alerts("run") == []  # Old probe cannot satisfy post-threshold test.
    now[0] = 1615
    recovery.observe(response(now))
    alert = recovery.alerts("run")[0]
    assert alert["text"].startswith("SEVERE SERVICE OUTAGE DETECTED\n\n")
    assert "cause unconfirmed" in alert["text"]
    assert "run/task-25" in alert["text"]
    restarted = Recovery(store, gate, clock=lambda: now[0])
    assert restarted.alerts("run") == [alert]  # Interrupted console delivery is replayable.
    restarted.acknowledge("run", alert["episode"])
    assert recovery.alerts("run") == []
    now[0] = 1630
    recovery.observe(response(now))
    assert recovery.alerts("run") == []


@pytest.mark.parametrize(
    "status,missing,success", [(200, False, True), (404, True, False), (502, True, False)]
)
def test_success_or_exact_missing_ends_episode_and_preserves_history(rig, status, missing, success):
    recovery, store, _, now = rig
    recovery.observe(response(now))
    old = store.get("services", "dictionary:configured")["episode"]
    now[0] += 15
    recovery.observe(response(now, status=status, missing=missing, valid_success=success))
    assert store.get("services", "dictionary:configured")["episode"] is None
    assert store.get("episodes", old)["status"] == "recovered"
    now[0] += 15
    recovery.observe(response(now))
    new = store.get("services", "dictionary:configured")["episode"]
    assert new != old
    assert store.get("episodes", new)["skipped"] == []


@pytest.mark.parametrize("status", [None, 400, 401, 429, 200])
def test_unknown_or_non_5xx_does_not_claim_recovery_or_continuity(rig, status):
    recovery, store, _, now = rig
    recovery.observe(response(now))
    old = store.get("services", "dictionary:configured")["episode"]
    now[0] += 15
    recovery.observe(response(now, status=status))
    assert store.get("episodes", old)["status"] == "unknown"
    with pytest.raises(RecoveryDeferred):
        recovery.skip("run", ("task",), "dictionary:configured")


def test_service_clock_and_dependency_scope_not_fabricated(rig):
    recovery, store, _, now = rig
    tasks = register(recovery)
    recovery.observe(response(now))
    now[0] = 1600
    obs = response(now)
    recovery.observe(replace(obs, monotonic=1001))  # Wall clock jumped, only 1s observed.
    assert recovery.skip("run", tasks, "dictionary:configured")["skipped"] == []
    recovery.observe(response(now, service="wiki:mg.wikipedia.org"))
    now[0] = 2200
    recovery.observe(response(now, service="wiki:mg.wikipedia.org"))
    assert recovery.skip("run", tasks, "wiki:mg.wikipedia.org")["skipped"] == []
    assert all(task["status"] == "pending" for _, task in _rows(store, "tasks"))


def _rows(store, kind):
    with store.transaction() as tx:
        return tx.rows(kind)


def test_boot_change_does_not_forge_ten_minutes_elapsed(rig):
    recovery, _, _, now = rig
    tasks = register(recovery)
    recovery.observe(response(now))
    now[0] = 1600
    recovery.observe(replace(response(now), boot="boot-2"))
    assert recovery.skip("run", tasks, "dictionary:configured")["skipped"] == []


def test_completed_task_cannot_inflate_skips(rig):
    recovery, store, _, now = rig
    register(recovery, 1)
    with store.transaction() as tx:
        task = tx.get("tasks", "run/task-0")
        task["status"] = "complete"
        tx.put("tasks", "run/task-0", task)
    recovery.observe(response(now))
    now[0] = 1600
    recovery.observe(response(now))
    with pytest.raises(StateError, match="Completed"):
        recovery.skip("run", ("task-0",), "dictionary:configured")


def test_multiple_explicit_service_dependencies_preserve_identity(rig):
    recovery, store, _, _ = rig
    recovery.register_task("run", "section", "dictionary:configured")
    recovery.register_task("run", "section", "wiki:mg.wikipedia.org")
    assert store.get("tasks", "run/section")["services"] == [
        "dictionary:configured",
        "wiki:mg.wikipedia.org",
    ]
