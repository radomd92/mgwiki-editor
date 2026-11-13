"""Persist bounded 502 retries without sleeping or blocking article publication."""

from __future__ import annotations

import hashlib
import math
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .network import NetworkPolicyError, RequestGate, retry_after_seconds

MAX_RETRIES = 10
RETRY_INTERVAL = 15


class DictionaryRetries:
    """One serial coordinator resumes due lookups; no hidden HTTP or sleep loop."""

    def __init__(
        self,
        path: Path | None = None,
        *,
        clock: Callable[[], float] = time.time,
    ) -> None:
        path = path or RequestGate().path.with_name("dictionary-retries.json")
        self.gate = RequestGate(path=path)
        self.clock = clock

    @staticmethod
    def _key(url: str) -> str:
        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    @staticmethod
    def _records(state: dict[str, Any]) -> dict[str, Any]:
        records = state.setdefault("dictionary_502", {})
        if not isinstance(records, dict):
            raise NetworkPolicyError("Invalid dictionary retry state; no request sent.")
        for row in records.values():
            if (
                not isinstance(row, dict)
                or type(row.get("failures")) is not int
                or not 1 <= row["failures"] <= MAX_RETRIES + 1
                or not isinstance(row.get("next_attempt"), (int, float))
                or not math.isfinite(row["next_attempt"])
                or row["next_attempt"] < 0
                or not isinstance(row.get("result"), dict)
            ):
                raise NetworkPolicyError("Invalid dictionary retry record; no request sent.")
        return records

    def _result(self, row: dict[str, Any]) -> dict[str, Any]:
        result = dict(row["result"])
        exhausted = row["failures"] >= MAX_RETRIES + 1
        result["retry"] = {
            "status": "exhausted" if exhausted else "pending",
            "max_retries": MAX_RETRIES,
            "retries_used": row["failures"] - 1,
            "interval_seconds": RETRY_INTERVAL,
            "next_attempt_unix": None if exhausted else row["next_attempt"],
            "retry_in_seconds": None
            if exhausted
            else max(
                0,
                math.ceil(row["next_attempt"] - self.clock()),
            ),
        }
        return result

    def pending(self, url: str) -> dict[str, Any] | None:
        """Return retained failure before its deadline or after ten failed retries."""
        if not self.gate.path.exists():
            return None
        with self.gate.state() as state:
            row = self._records(state).get(self._key(url))
            if row and (row["failures"] >= MAX_RETRIES + 1 or row["next_attempt"] > self.clock()):
                return self._result(row)
        return None

    def usage(self, url: str) -> int:
        """Read actual persisted budget without clearing it or issuing a request."""
        if not self.gate.path.exists():
            return 0
        with self.gate.state() as state:
            row = self._records(state).get(self._key(url))
            return row["failures"] - 1 if row else 0

    def failure(self, result: dict[str, Any], retry_after: str = "") -> dict[str, Any]:
        """Count actual 502 responses; preserve server deadlines longer than 15s."""
        with self.gate.state() as state:
            records = self._records(state)
            key = self._key(result["url"])
            previous = records.get(key, {})
            failures = min(previous.get("failures", 0) + 1, MAX_RETRIES + 1)
            now = self.clock()
            row = {
                "failures": failures,
                "next_attempt": max(
                    previous.get("next_attempt", 0),
                    now + max(RETRY_INTERVAL, retry_after_seconds(retry_after, now)),
                ),
                "result": result,
            }
            records[key] = row
            return self._result(row)

    def clear(self, url: str) -> None:
        """Success or an explicit missing page ends only this lookup's retry streak."""
        if self.gate.path.exists():
            with self.gate.state() as state:
                self._records(state).pop(self._key(url), None)
