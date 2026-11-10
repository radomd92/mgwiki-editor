"""Dictionary error classification/retry tests: fake HTTP, clock, and state only."""

from __future__ import annotations

import io
import json
from pathlib import Path
from urllib.error import HTTPError

import pytest

from mgwiki_editor.core import lookup
from mgwiki_editor.dictionary_retries import DictionaryRetries
from mgwiki_editor.network import NetworkPolicyError


def http_error(body: bytes, *, headers: dict | None = None) -> HTTPError:
    return HTTPError("http://dictionary", 502, "Bad Gateway", headers or {}, io.BytesIO(body))


def test_explicit_backend_nopage_is_missing_not_an_outage(tmp_path: Path) -> None:
    body = json.dumps({"type": "error", "status": 502,
                       "details": {"type": "NoPage", "error": "Page not found"}}).encode()
    policy = DictionaryRetries(tmp_path / "retry.json")

    def opener(*args, **kwargs):
        raise http_error(body)

    result = lookup("en", "cubic model", opener=opener, retries=policy)
    assert result["status"] == "missing"
    assert result["http_status"] == 502
    assert result["missing_reason"] == "backend_NoPage"
    assert result["error_body"] == body.decode()
    assert not policy.gate.path.exists()


@pytest.mark.parametrize("body", [
    b"Bad Gateway", b"not found", b'{"type":"NoPage"}',
    b'{"type":"error","status":502,"details":{"type":"Timeout"}}',
    b'{"type":"error","status":500,"details":{"type":"NoPage"}}',
    b'{"type":"error","status":502,"details":"NoPage"}',
])
def test_other_502s_remain_failed_not_missing(tmp_path: Path, body: bytes) -> None:
    def opener(*args, **kwargs):
        raise http_error(body)

    result = lookup("mg", "term", opener=opener,
                    retries=DictionaryRetries(tmp_path / "retry.json", clock=lambda: 100))
    assert result["status"] == "failed"
    assert result["entries"] == []
    assert result["retry"]["status"] == "pending"
    assert result["retry"]["retry_in_seconds"] == 15


def test_retries_persist_and_stop_after_ten_without_sleep(tmp_path: Path) -> None:
    clock = [100.0]
    path = tmp_path / "retry.json"
    calls = []

    def opener(request, timeout):
        calls.append((clock[0], request.full_url))
        raise http_error(b'{"message":"upstream timeout"}')

    def perform():
        # New process-equivalent policy instance, same persisted budget.
        return lookup("en", "term", opener=opener,
                      retries=DictionaryRetries(path, clock=lambda: clock[0]))

    first = perform()
    assert first["retry"]["retries_used"] == 0
    for number in range(1, 11):
        clock[0] += 14
        pending = perform()
        assert len(calls) == number
        assert pending["retry"]["retry_in_seconds"] == 1
        clock[0] += 1
        retried = perform()
        assert len(calls) == number + 1
        assert retried["retry"]["retries_used"] == number
    assert retried["retry"]["status"] == "exhausted"
    clock[0] += 10000
    assert perform()["retry"]["status"] == "exhausted"
    assert len(calls) == 11  # Initial attempt plus at most ten retries.
    assert all(b[0] - a[0] >= 15 for a, b in zip(calls, calls[1:], strict=False))


def test_retry_after_can_extend_but_not_shorten_interval(tmp_path: Path) -> None:
    clock = [100.0]
    policy = DictionaryRetries(tmp_path / "retry.json", clock=lambda: clock[0])

    def opener(*args, **kwargs):
        raise http_error(b"timeout", headers={"Retry-After": "120"})

    result = lookup("en", "term", opener=opener, retries=policy)
    assert result["retry"]["next_attempt_unix"] == 220
    clock[0] = 219
    assert policy.pending(result["url"])["retry"]["retry_in_seconds"] == 1
    clock[0] = 220
    assert policy.pending(result["url"]) is None


@pytest.mark.parametrize("outcome", ["found", "404", "NoPage"])
def test_recovery_clears_only_this_lookup(tmp_path: Path, outcome: str) -> None:
    clock = [100.0]
    policy = DictionaryRetries(tmp_path / "retry.json", clock=lambda: clock[0])

    def failed(*args, **kwargs):
        raise http_error(b"timeout")

    lookup("en", "term", opener=failed, retries=policy)
    other = lookup("en", "other", opener=failed, retries=policy)
    clock[0] += 15

    def recovered(*args, **kwargs):
        if outcome == "404":
            raise HTTPError("http://dictionary", 404, "Missing", {}, io.BytesIO())
        if outcome == "NoPage":
            raise http_error(b'{"type":"error","status":502,"details":{"type":"NoPage"}}')
        return io.BytesIO(b'[{"language":"en","definitions":["sense"]}]')

    result = lookup("en", "term", opener=recovered, retries=policy)
    assert result["status"] == ("found" if outcome == "found" else "missing")
    records = json.loads(policy.gate.path.read_text())["dictionary_502"]
    assert policy._key(result["url"]) not in records
    assert policy._key(other["url"]) in records


def test_error_body_is_bounded_and_truncated_nopage_not_classified(tmp_path: Path) -> None:
    body = b'{"type":"error","status":502,"details":{"type":"NoPage"}}' + b" " * 70000

    def opener(*args, **kwargs):
        raise http_error(body)

    result = lookup("en", "term", opener=opener,
                    retries=DictionaryRetries(tmp_path / "retry.json"))
    assert result["status"] == "failed"
    assert result["error_body_truncated"] is True
    assert len(result["error_body"].encode()) <= 65536


def test_other_network_policy_failures_are_not_retried(tmp_path: Path) -> None:
    policy = DictionaryRetries(tmp_path / "retry.json")
    calls = []

    def opener(*args, **kwargs):
        calls.append(True)
        raise NetworkPolicyError("Dictionary overloaded (503); shared cooldown 120s. Stop.")

    with pytest.raises(NetworkPolicyError, match="503"):
        lookup("en", "term", opener=opener, retries=policy)
    assert calls == [True]
    assert not policy.gate.path.exists()


def test_corrupt_retry_state_never_sends_request(tmp_path: Path) -> None:
    path = tmp_path / "retry.json"
    path.write_text('{"dictionary_502":{"key":{"failures":99}}}')

    def opener(*args, **kwargs):
        pytest.fail("Corrupt state must not send a request")

    with pytest.raises(NetworkPolicyError, match="Invalid dictionary retry record"):
        lookup("en", "term", opener=opener, retries=DictionaryRetries(path))
