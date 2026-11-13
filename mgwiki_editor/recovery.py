"""Durable service episodes, dependent tasks and at-least-once alert outbox."""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from dataclasses import asdict

from .dictionary_retries import DictionaryRetries
from .network import NetworkPolicyError, RequestGate, retry_after_seconds
from .observations import Observation
from .policy import (
    Facts,
    NetworkFacts,
    Operation,
    Outcome,
    RecoveryFacts,
    Request,
    RetryFacts,
    Role,
    evaluate,
)
from .policy_store import PolicyStore, StateError, Transaction, identifier


class RecoveryDeferred(NetworkPolicyError):
    def __init__(self, message: str, deadline: float | None = None) -> None:
        super().__init__(message)
        self.next_eligible_at = deadline


class Recovery:
    def __init__(
        self,
        store: PolicyStore,
        gate: RequestGate,
        *,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.store, self.gate, self.clock = store, gate, clock

    def before(
        self,
        service: str,
        safe_read: bool,
        url: str | None = None,
        *,
        probe: bool = False,
    ) -> None:
        record = self.store.get("services", service)
        if not record or not safe_read:
            return
        now = self.clock()
        if record["next_at"] > now:
            raise RecoveryDeferred("Service retry cooldown retained.", record["next_at"])
        if record.get("episode"):
            episode = self.store.get("episodes", record["episode"])
            if episode is None:
                raise StateError("Missing service episode.")
            if now - episode["first_at"] >= 600 and not probe:
                raise RecoveryDeferred("Recovery window elapsed; permitted real probe required.")
            if not probe:
                with self.gate.state() as state:
                    deadline = max(state.get("next_request", 0), record["next_at"])
                dictionary = service.startswith("dictionary:")
                used = (
                    DictionaryRetries(
                        self.gate.path.with_name("dictionary-retries.json"), clock=self.clock
                    ).usage(url)
                    if dictionary and url
                    else None
                )
                latest = episode["latest"]
                facts = Facts(
                    network=NetworkFacts(True, deadline),
                    retry=RetryFacts(
                        Operation.LOOKUP_DICTIONARY if dictionary else Operation.READ_SOURCE,
                        latest["status"],
                        latest["missing"],
                        episode["first_at"],
                        latest["at"],
                        record["next_at"],
                        used,
                    ),
                )
                decision = evaluate(Request(Operation.RETRY_READ, Role.COORDINATOR), facts, now)
                with self.store.transaction() as tx:
                    tx.event(now, "policy_decision", service, decision.as_dict())
                if decision.outcome is not Outcome.ALLOW:
                    raise RecoveryDeferred(
                        "Retry policy requires due deadline/evidence/budget.",
                        decision.next_eligible_at,
                    )

    def observe(self, observation: Observation) -> None:
        """Only transport hooks call this; no caller-supplied probe command accepts observations."""
        obs = asdict(observation)
        now = observation.at
        failed = (
            observation.safe_read
            and observation.status is not None
            and 500 <= observation.status <= 599
            and not observation.missing
        )
        deadline = now + max(15, retry_after_seconds(observation.retry_after, now)) if failed else 0
        if failed:
            # Shared cooldown first. If SQLite then fails, gate stays closed.
            self.gate.defer_until(deadline)
        with self.store.transaction() as tx:
            record = tx.get("services", observation.service) or {"next_at": 0, "episode": None}
            episode = tx.get("episodes", record["episode"]) if record.get("episode") else None
            tx.event(now, "http_observation", observation.service, obs)
            record["latest"] = obs
            if failed:
                if episode is None:
                    episode = {
                        "id": uuid.uuid4().hex,
                        "service": observation.service,
                        "first_at": now,
                        "first_mono": observation.monotonic,
                        "boot": observation.boot,
                        "clock_verified": observation.boot != "unknown",
                        "anchor_at": now,
                        "anchor_mono": observation.monotonic,
                        "anchor_boot": observation.boot,
                        "status": "active",
                        "skipped": [],
                        "threshold_at": None,
                        "threshold_probe": None,
                        "alert_emitted": False,
                    }
                    record["episode"] = episode["id"]
                elapsed = observation.monotonic - episode["anchor_mono"]
                clock_ok = (
                    observation.boot != "unknown"
                    and observation.boot == episode["anchor_boot"]
                    and elapsed >= 0
                    and abs((now - episode["anchor_at"]) - elapsed) <= 5
                )
                if not clock_ok:
                    episode.update(
                        clock_verified=False,
                        anchor_at=now,
                        anchor_mono=observation.monotonic,
                        anchor_boot=observation.boot,
                    )
                elif elapsed >= 600:
                    # Preserve original first failure/history; re-establish a stable observed
                    # 600-second window after restart/clock ambiguity, never invent elapsed time.
                    episode["clock_verified"] = True
                episode["latest"] = obs
                record["next_at"] = max(record["next_at"], deadline)
                self._auto_skip(tx, episode, now)
                tx.put("episodes", episode["id"], episode)
                self._queue_alert(tx, episode, now)
            elif episode is not None and (observation.valid_success or observation.missing):
                episode.update(status="recovered", recovered_at=now)
                tx.put("episodes", episode["id"], episode)
                alert = tx.get("alerts", episode["id"])
                if alert and alert["status"] == "pending":
                    alert["text"] += (
                        f" Service subsequently recovered at {now:.3f}; prior skips retained."
                    )
                    tx.put("alerts", episode["id"], alert)
                record["episode"] = None
            elif episode is not None:
                # Unknown/non-5xx is not proof of recovery or continuous 5xx. Preserve history;
                # next qualifying failure starts a new conservative observation window.
                episode.update(status="unknown", ended_at=now)
                tx.put("episodes", episode["id"], episode)
                record["episode"] = None
            tx.put("services", observation.service, record)

    @staticmethod
    def _facts(episode: dict, dependencies: tuple[str, ...]) -> RecoveryFacts:
        obs = episode["latest"]
        return RecoveryFacts(
            service_id=episode["service"],
            episode_id=episode["id"],
            history_verified=True,
            clock_verified=episode["clock_verified"],
            first_failure_at=episode["first_at"],
            probe_id=obs["id"],
            probe_at=obs["at"],
            probe_status=obs["status"],
            probe_is_real_read=obs["safe_read"],
            probe_backend_missing_page=obs["missing"],
            dependent_task_ids=dependencies,
            skipped_task_ids=tuple(episode["skipped"]),
            threshold_reached_at=episode["threshold_at"],
            threshold_probe_id=episode["threshold_probe"],
            alert_emitted=episode["alert_emitted"],
        )

    def register_task(self, run: str, task: str, service: str) -> None:
        key = identifier(run) + "/" + identifier(task)
        with self.store.transaction() as tx:
            previous = tx.get("tasks", key)
            if previous is None:
                tx.put(
                    "tasks",
                    key,
                    {
                        "run": run,
                        "id": task,
                        "service": service,
                        "services": [service],
                        "status": "pending",
                    },
                    new=True,
                )
                tx.event(self.clock(), "task_registered", run, {"task": task, "service": service})
            elif service not in previous.get("services", [previous["service"]]):
                previous["services"] = [*previous.get("services", [previous["service"]]), service]
                tx.put("tasks", key, previous)
                tx.event(
                    self.clock(), "task_dependency_added", run, {"task": task, "service": service}
                )
            record = tx.get("services", service)
            if record and record.get("episode"):
                episode = tx.get("episodes", record["episode"])
                self._auto_skip(tx, episode, self.clock())
                tx.put("episodes", episode["id"], episode)

    def _auto_skip(self, tx: Transaction, episode: dict, now: float) -> None:
        decision = evaluate(
            Request(Operation.CONFIRM_OUTAGE, Role.COORDINATOR),
            Facts(recovery=self._facts(episode, ())),
            now,
        )
        if decision.outcome is not Outcome.ALLOW:
            return
        episode["status"] = "down"
        tasks = [
            (key, task)
            for key, task in tx.rows("tasks")
            if episode["service"] in task.get("services", [task["service"]])
            and task["status"] != "complete"
        ]
        added: dict[str, list[str]] = {}
        for key, task in tasks:
            if key not in episode["skipped"]:
                episode["skipped"].append(key)
                added.setdefault(task["run"], []).append(key)
            task.update(status="skipped", episode=episode["id"], skipped_at=now)
            tx.put("tasks", key, task)
        if len(episode["skipped"]) >= 26 and episode["threshold_at"] is None:
            episode.update(threshold_at=now, threshold_probe=episode["latest"]["id"])
        for run, keys in added.items():
            tx.event(
                now,
                "tasks_skipped",
                run,
                {"tasks": keys, "episode": episode["id"], "automatic": True},
            )

    def skip(self, run: str, tasks: tuple[str, ...], service: str) -> dict:
        now = self.clock()
        keys = tuple(identifier(run) + "/" + identifier(task) for task in tasks)
        with self.store.transaction() as tx:
            record = tx.get("services", service)
            episode = (
                tx.get("episodes", record["episode"]) if record and record.get("episode") else None
            )
            if episode is None:
                raise RecoveryDeferred("No continuously observed outage episode; nothing skipped.")
            dependencies = tuple(
                key
                for key, value in tx.rows("tasks")
                if service in value.get("services", [value["service"]])
            )
            decision = evaluate(
                Request(Operation.SKIP_TASKS, Role.COORDINATOR, keys),
                Facts(recovery=self._facts(episode, dependencies)),
                now,
            )
            tx.event(now, "policy_decision", run, decision.as_dict())
            if decision.outcome is not Outcome.ALLOW:
                result = {"decision": decision.as_dict(), "skipped": []}
            else:
                for key in keys:
                    task = tx.get("tasks", key)
                    if task["status"] == "complete":
                        raise StateError("Completed task cannot be relabeled skipped.")
                    if key not in episode["skipped"]:
                        episode["skipped"].append(key)
                    task.update(status="skipped", episode=episode["id"], skipped_at=now)
                    tx.put("tasks", key, task)
                if len(episode["skipped"]) >= 26 and episode["threshold_at"] is None:
                    episode.update(threshold_at=now, threshold_probe=episode["latest"]["id"])
                tx.put("episodes", episode["id"], episode)
                tx.event(now, "tasks_skipped", run, {"tasks": list(keys), "episode": episode["id"]})
                result = {
                    "decision": decision.as_dict(),
                    "skipped": list(keys),
                    "episode": episode["id"],
                    "distinct_count": len(episode["skipped"]),
                }
        return result

    def _queue_alert(self, tx: Transaction, episode: dict, now: float) -> None:
        if episode["threshold_at"] is None or tx.get("alerts", episode["id"]) is not None:
            return
        dependencies = tuple(
            key
            for key, task in tx.rows("tasks")
            if episode["service"] in task.get("services", [task["service"]])
        )
        decision = evaluate(
            Request(Operation.EMIT_OUTAGE_ALERT, Role.COORDINATOR),
            Facts(recovery=self._facts(episode, dependencies)),
            now,
        )
        if decision.outcome is not Outcome.ALLOW:
            return
        probe = episode["latest"]
        memos = []
        for run in sorted({task.split("/", 1)[0] for task in episode["skipped"]}):
            state = tx.get("runs", run)
            directory = run + ".intake" if state and not state.get("initialized") else run
            memos.append(f"runs/{directory}/deferred-issues.md")
        duration = (
            probe["monotonic"] - episode["first_mono"]
            if probe["boot"] == episode["boot"]
            else probe["at"] - episode["anchor_at"]
        )
        text = (
            "SEVERE SERVICE OUTAGE DETECTED\n\n"
            f"{episode['service']} returned HTTP {probe['status']} at {probe['at']:.3f}; "
            f"first failure {episode['first_at']:.3f}, verified observation span "
            f"{duration:.1f}s; no intervening success observed. "
            "Restart suspected; cause unconfirmed. "
            f"{len(episode['skipped'])} distinct tasks blocked/skipped: "
            + ", ".join(episode["skipped"])
            + ". Work retained: "
            + ", ".join(memos)
            + ". "
            "Next: permitted service probe after cooldown; never replay uncertain saves."
        )
        tx.put(
            "alerts",
            episode["id"],
            {
                "episode": episode["id"],
                "text": text,
                "tasks": episode["skipped"],
                "status": "pending",
            },
            new=True,
        )
        tx.event(now, "outage_alert_queued", episode["service"], {"episode": episode["id"]})

    def alerts(self, run: str) -> list[dict]:
        with self.store.transaction() as tx:
            return [
                value
                for _, value in tx.rows("alerts")
                if value["status"] == "pending"
                and any(task.startswith(run + "/") for task in value["tasks"])
            ]

    def acknowledge(self, run: str, episode_id: str) -> None:
        with self.store.transaction() as tx:
            alert = tx.get("alerts", identifier(episode_id))
            if alert is None or not any(task.startswith(run + "/") for task in alert["tasks"]):
                raise StateError("Alert outside run scope.")
            alert["status"] = "delivered"
            tx.put("alerts", episode_id, alert)
            episode = tx.get("episodes", episode_id)
            episode["alert_emitted"] = True
            tx.put("episodes", episode_id, episode)
            tx.event(self.clock(), "outage_alert_acknowledged", run, {"episode": episode_id})

    def status(self) -> list[dict]:
        with self.store.transaction() as tx:
            return [
                {
                    "service": key,
                    **value,
                    "outage": tx.get("episodes", value["episode"])
                    if value.get("episode")
                    else None,
                }
                for key, value in tx.rows("services")
            ]
