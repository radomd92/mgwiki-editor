"""Offline transport and cross-process-state tests; never contact Wikimedia."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request

import pytest

from mgwiki_editor import network
from mgwiki_editor.network import (
    NetworkPolicyError,
    NoRedirect,
    RequestGate,
    api_url_allowed,
    guarded_send,
    no_interactive_input,
    retry_after_seconds,
)


class Clock:
    """Advance virtual time instead of sleeping in tests."""

    def __init__(self) -> None:
        """Start at a fixed epoch with an empty sleep log."""
        self.now = 1_000_000.0
        self.sleeps: list[float] = []

    def time(self) -> float:
        """Return virtual wall time."""
        return self.now

    def sleep(self, seconds: float) -> None:
        """Advance the virtual clock and record the requested wait."""
        self.sleeps.append(seconds)
        self.now += seconds


@pytest.fixture
def gate(tmp_path: Path) -> tuple[RequestGate, Clock]:
    """Use a private shared-state file and deterministic zero jitter."""
    clock = Clock()
    return RequestGate(tmp_path / "requests.json", clock=clock.time,
                       sleep=clock.sleep, monotonic=clock.time, jitter=lambda *args: 0), clock


def response(status: int = 200, *, error: str = "", retry_after: str = "") -> SimpleNamespace:
    """Construct an offline requests-like response."""
    return SimpleNamespace(
        status_code=status, headers={"Retry-After": retry_after},
        json=lambda: {"error": {"code": error}} if error else {"query": {}},
    )


def test_state_shared_between_gate_instances(gate: tuple[RequestGate, Clock]) -> None:
    """Separate CLI processes coordinate through the same file, not per-site memory."""
    first, clock = gate
    second = RequestGate(first.path, clock=clock.time, sleep=clock.sleep,
                         monotonic=clock.time, jitter=lambda *args: 0)
    first.wait()
    second.wait()
    assert clock.sleeps == [10]
    assert json.loads(first.path.read_text())["next_request"] == clock.now + 10


def test_edits_remain_ten_seconds_apart_with_reads_between(
    gate: tuple[RequestGate, Clock],
) -> None:
    """Reads cannot erase a pending edit cooldown."""
    limiter, clock = gate
    start = clock.now
    limiter.wait(write=True)
    limiter.wait()
    limiter.wait(write=True)
    assert clock.now - start == 20
    assert clock.sleeps == [10, 10]


def test_ten_second_spacing_reserves_jitter_for_backoff(tmp_path: Path) -> None:
    """Ordinary request gaps are 10 seconds; overload backoff still includes jitter."""
    clock = Clock()
    limiter = RequestGate(tmp_path / "requests.json", clock=clock.time,
                          sleep=clock.sleep, monotonic=clock.time, jitter=lambda *args: 0.5)
    limiter.wait()
    limiter.wait()
    assert clock.sleeps == [10]
    assert limiter.backoff() == 30.5


@pytest.mark.parametrize("value, expected", [
    ("120", 120), ("2.5", 2.5), ("-1", 0), ("nonsense", 0), ("inf", 0), ("nan", 0),
])
def test_retry_after_seconds(value: str, expected: float) -> None:
    """Handle malformed headers conservatively without defeating base backoff."""
    assert retry_after_seconds(value, 1_000_000) == expected


def test_retry_after_http_date() -> None:
    """Honor date-form cooldowns as well as delta seconds."""
    now = datetime(2026, 11, 3, 12, 0, tzinfo=UTC).timestamp()
    assert retry_after_seconds("Tue, 03 Nov 2026 12:05:00 GMT", now) == 300


def test_long_server_cooldown_is_not_shortened(gate: tuple[RequestGate, Clock]) -> None:
    """A 1-hour Retry-After stops instead of retrying after a local maximum wait."""
    limiter, clock = gate
    assert limiter.backoff("3600") == 3600
    with pytest.raises(NetworkPolicyError, match="10-second gate budget"):
        limiter.wait()
    assert clock.sleeps == []
    assert json.loads(limiter.path.read_text())["next_request"] == clock.now + 3600


def test_backoff_and_circuit_breaker(gate: tuple[RequestGate, Clock]) -> None:
    """Repeated overload opens a persistent circuit, not an endless retry loop."""
    limiter, clock = gate
    assert limiter.backoff() == 30
    assert limiter.backoff() == 60
    assert limiter.backoff() >= 900
    with pytest.raises(NetworkPolicyError):
        limiter.wait()
    assert clock.sleeps == []


def test_success_does_not_clear_another_process_cooldown(gate: tuple[RequestGate, Clock]) -> None:
    """Late successful responses cannot cancel already observed server overload."""
    limiter, clock = gate
    limiter.backoff("120")
    limiter.success()
    with pytest.raises(NetworkPolicyError, match="task deferred"):
        limiter.wait()
    assert clock.sleeps == []
    assert json.loads(limiter.path.read_text())["cooldown_until"] == clock.now + 120


@pytest.mark.parametrize("state", ["not json", "[]", '{"next_request": -1}',
                                   '{"next_request": "tomorrow"}'])
def test_corrupt_pacing_state_fails_closed(
    gate: tuple[RequestGate, Clock], state: str,
) -> None:
    """A broken shared file must not silently reset request budgets."""
    limiter, clock = gate
    limiter.path.write_text(state)
    with pytest.raises(NetworkPolicyError):
        limiter.wait()
    assert not clock.sleeps


@pytest.mark.parametrize("url", [
    "https://mg.wikipedia.org/w/api.php", "https://en.wikipedia.org/w/api.php?action=query",
    "https://login.wikimedia.org/w/api.php",
])
def test_required_api_origins_allowed(url: str) -> None:
    """Only required APIs are transport exceptions to the external-link boundary."""
    assert api_url_allowed(url)


@pytest.mark.parametrize("url", [
    "https://example.org/w/api.php", "https://mg.wikipedia.org/wiki/Water",
    "https://mg.wikipedia.org.evil.example/w/api.php", "http://mg.wikipedia.org/w/api.php",
    "https://user:pass@mg.wikipedia.org/w/api.php", "https://mg.wikipedia.org:8443/w/api.php",
    "https://upload.wikimedia.org/image.png",
    "https://mg.wikipedia.org:notaport/w/api.php", "https://mg.wikipedia.org/w/api.php#external",
])
def test_external_urls_blocked_without_request(url: str, gate: tuple[RequestGate, Clock]) -> None:
    """Do not fetch references, images or lookalike hosts through a helper."""
    limiter, clock = gate
    calls = []
    send = guarded_send(lambda *args, **kwargs: calls.append(args), limiter)
    with pytest.raises(NetworkPolicyError, match="approved Wikimedia API"):
        send(SimpleNamespace(url=url, body=None))
    assert not calls and not clock.sleeps
    assert not limiter.path.exists()


@pytest.mark.parametrize("status,error", [
    (429, ""), (503, ""), (200, "maxlag"), (200, "ratelimited"),
])
def test_overload_stops_without_resubmission(
    status: int, error: str, gate: tuple[RequestGate, Clock],
) -> None:
    """No write or read is automatically replayed after an overload response."""
    limiter, clock = gate
    calls = []

    def send(*args, **kwargs):
        calls.append(kwargs)
        return response(status, error=error, retry_after="90")

    guarded = guarded_send(send, limiter)
    with pytest.raises(NetworkPolicyError, match="No automatic resubmission"):
        guarded(SimpleNamespace(url="https://mg.wikipedia.org/w/api.php", body="action=edit"))
    assert len(calls) == 1 and calls[0]["allow_redirects"] is False
    assert json.loads(limiter.path.read_text())["next_request"] == clock.now + 90


def test_transport_does_not_follow_redirect(gate: tuple[RequestGate, Clock]) -> None:
    """Even a successful API redirect is not permission to navigate elsewhere."""
    limiter, clock = gate
    guarded = guarded_send(lambda *args, **kwargs: response(302), limiter)
    with pytest.raises(NetworkPolicyError, match="redirect not followed"):
        guarded(SimpleNamespace(url="https://mg.wikipedia.org/w/api.php", body=None))


def test_actual_edit_parameters_apply_write_budget(gate: tuple[RequestGate, Clock]) -> None:
    """Prepared form bodies, including byte bodies, trigger edit spacing."""
    limiter, clock = gate
    guarded = guarded_send(lambda *args, **kwargs: response(), limiter)
    prepared = SimpleNamespace(
        url="https://mg.wikipedia.org/w/api.php", body=b"action=edit&text=Rano",
    )
    guarded(prepared)
    guarded(prepared)
    assert clock.sleeps == [10]


def test_dictionary_redirect_rejected() -> None:
    """No implicit URL navigation via urllib's default redirect behavior."""
    with pytest.raises(NetworkPolicyError, match="redirect not followed"):
        NoRedirect().redirect_request(None, None, 302, "redirect", {}, "https://example.org")


def test_dictionary_uses_shared_gate_and_no_redirects(
    gate: tuple[RequestGate, Clock], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Dictionary calls do not bypass pacing or follow reference URLs."""
    limiter, clock = gate
    handlers = []
    monkeypatch.setattr(network, "RequestGate", lambda: limiter)

    def opener(*items):
        handlers.extend(items)
        return SimpleNamespace(open=lambda *args, **kwargs: "dictionary-response")

    monkeypatch.setattr(network, "build_opener", opener)
    request = Request("http://192.168.1.155:8000/wiktionary-pages/mg/rano")
    assert network.dictionary_open(request, timeout=20) == "dictionary-response"
    assert any(isinstance(handler, NoRedirect) for handler in handlers)
    assert limiter.path.exists() and not clock.sleeps


def test_dictionary_overload_cools_shared_gate(
    gate: tuple[RequestGate, Clock], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Repeated dictionary overload must not cause upstream polling storms."""
    limiter, clock = gate
    monkeypatch.setattr(network, "RequestGate", lambda: limiter)

    def fail(*args, **kwargs):
        raise HTTPError("http://dictionary", 429, "slow", {"Retry-After": "120"}, None)

    monkeypatch.setattr(network, "build_opener", lambda *args: SimpleNamespace(open=fail))
    with pytest.raises(NetworkPolicyError, match="Dictionary overloaded"):
        network.dictionary_open(Request("http://dictionary/wiktionary-pages/mg/rano"), timeout=20)
    assert json.loads(limiter.path.read_text())["next_request"] == clock.now + 120


@pytest.mark.parametrize("missing", [False, True])
def test_successful_dictionary_result_resets_overload_streak_without_erasing_cooldown(
    gate: tuple[RequestGate, Clock], monkeypatch: pytest.MonkeyPatch, missing: bool,
) -> None:
    limiter, clock = gate
    limiter.backoff("120")
    clock.now += 120
    monkeypatch.setattr(network, "RequestGate", lambda: limiter)
    deadline = clock.now + 60

    def open_response(*args, **kwargs):
        # Another worker can record a new cooldown while this request is in flight.
        with limiter.state() as state:
            state["next_request"] = state["cooldown_until"] = deadline
        if missing:
            raise HTTPError("http://dictionary", 404, "missing", {}, None)
        return "dictionary-response"

    monkeypatch.setattr(network, "build_opener", lambda *args: SimpleNamespace(open=open_response))
    if missing:
        with pytest.raises(HTTPError) as error:
            network.dictionary_open(
                Request("http://dictionary/wiktionary-pages/mg/rano"), timeout=20)
        assert error.value.code == 404
    else:
        assert network.dictionary_open(
            Request("http://dictionary/wiktionary-pages/mg/rano"), timeout=20) == (
            "dictionary-response"
        )
    state = json.loads(limiter.path.read_text())
    assert state["failures"] == 0
    assert state["next_request"] == state["cooldown_until"] == deadline
    clock.now = deadline
    assert limiter.backoff() == 30  # A new streak, not a second consecutive overload.


def test_no_password_or_captcha_prompt() -> None:
    """Credential problems block rather than soliciting terminal input."""
    with pytest.raises(NetworkPolicyError, match="Interactive input disabled"):
        no_interactive_input("Password", password=True)


@pytest.mark.parametrize("failure", ["timeout", "http504", "api_error", "invalid_json"])
def test_uncertain_edits_never_replay(
    failure: str, gate: tuple[RequestGate, Clock],
) -> None:
    """Prevent Pywikibot from retrying failed/uncertain edit requests."""
    limiter, clock = gate
    calls = []

    def send(*args, **kwargs):
        calls.append(args)
        if failure == "timeout":
            raise TimeoutError("Response lost")
        if failure == "http504":
            return response(504)
        if failure == "api_error":
            return response(error="readonly")

        def invalid_json():
            raise ValueError("Bad JSON")

        return SimpleNamespace(status_code=200, headers={}, json=invalid_json)

    guarded = guarded_send(send, limiter)
    with pytest.raises(NetworkPolicyError, match="resubmission"):
        guarded(SimpleNamespace(url="https://mg.wikipedia.org/w/api.php", body="action=edit"))
    assert len(calls) == 1 and not clock.sleeps


def test_installed_transport_uses_fatal_error_not_retryable_generic_exception(
    gate: tuple[RequestGate, Clock], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise the installed Pywikibot boundary, not only the isolated wrapper."""
    import pywikibot
    from pywikibot import config
    from pywikibot.comms import http
    from pywikibot.exceptions import FatalServerError

    limiter, clock = gate
    calls = []

    def send(*args, **kwargs):
        calls.append(args)
        return response(429, retry_after="60")

    adapter = SimpleNamespace(max_retries="unsafe")
    session = SimpleNamespace(send=send, adapters={"https://": adapter})
    monkeypatch.setattr(http, "session", session)
    monkeypatch.setattr(network, "RequestGate", lambda: limiter)
    network.install_wikimedia_transport()
    first = session.send
    network.install_wikimedia_transport()
    assert session.send is first
    with pytest.raises(FatalServerError, match="No automatic resubmission"):
        session.send(SimpleNamespace(url="https://mg.wikipedia.org/w/api.php", body="action=edit"))
    assert len(calls) == 1
    assert pywikibot.input is no_interactive_input
    assert adapter.max_retries.total == 0
    assert config.minthrottle == config.maxthrottle == config.put_throttle == 0
    assert config.max_retries == 0


def test_native_process_multiplicity_cannot_add_minutes_of_sleep(
    gate: tuple[RequestGate, Clock], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only the shared limiter, not native process-scaled throttle, owns normal delays."""
    from pywikibot.comms import http
    from pywikibot.throttle import Throttle

    limiter, clock = gate
    monkeypatch.setattr(http, "session", SimpleNamespace(send=lambda *args, **kwargs: response()))
    monkeypatch.setattr(network, "RequestGate", lambda: limiter)
    network.install_wikimedia_transport()
    throttle = Throttle("")
    throttle.process_multiplicity = 100
    assert throttle.waittime() == 0
    assert throttle.waittime(write=True) == 0
    limiter.wait()
    limiter.wait()
    assert clock.sleeps == [10]


def test_competing_worker_cannot_extend_wait_past_ten_minutes(
    tmp_path: Path,
) -> None:
    """A moving shared deadline gets one cumulative budget, never a renewed timeout."""
    clock = Clock()
    events = []
    limiter = RequestGate(tmp_path / "requests.json", clock=clock.time,
                          sleep=clock.sleep, monotonic=clock.time, report=events.append)
    limiter.wait()

    def competing_sleep(seconds):
        clock.sleep(seconds)
        # Another process reserves the slot just before this worker wakes.
        with limiter.state() as state:
            state["next_request"] = clock.now + 10

    limiter.sleep = competing_sleep
    with pytest.raises(NetworkPolicyError, match="task deferred"):
        limiter.wait()
    assert clock.sleeps == [10] * 60
    assert [event["event"] for event in events] == ["network_wait"] * 60 + ["network_deferred"]
    assert events[-1]["budget_seconds"] == 600
    assert events[-1]["waited_seconds"] == 600


def test_competing_workers_can_finish_after_several_spacing_waits(tmp_path: Path) -> None:
    """Transient contention between independent jobs is pacing, not a failed request."""
    clock = Clock()
    limiter = RequestGate(tmp_path / "requests.json", clock=clock.time,
                          sleep=clock.sleep, monotonic=clock.time, report=lambda event: None)
    limiter.wait()

    def competing_sleep(seconds):
        clock.sleep(seconds)
        if len(clock.sleeps) <= 3:
            with limiter.state() as state:
                state["next_request"] = clock.now + 10

    limiter.sleep = competing_sleep
    limiter.wait(write=True)
    assert clock.sleeps == [10] * 4
    state = json.loads(limiter.path.read_text())
    assert state["next_request"] == state["next_write"] == clock.now + 10


@pytest.mark.parametrize("delay, allowed", [(600, True), (600.1, False)])
def test_spacing_budget_boundary(gate: tuple[RequestGate, Clock], delay, allowed) -> None:
    """Exactly ten minutes is allowed; a longer queue preserves its deadline and defers."""
    limiter, clock = gate
    deadline = clock.now + delay
    with limiter.state() as state:
        state["next_request"] = deadline
    if allowed:
        limiter.wait()
        assert clock.sleeps == [delay]
    else:
        with pytest.raises(NetworkPolicyError, match="600-second gate budget"):
            limiter.wait()
        assert clock.sleeps == []
        assert json.loads(limiter.path.read_text())["next_request"] == deadline


def test_new_server_cooldown_interrupts_contention_wait(tmp_path: Path) -> None:
    """The longer contention budget cannot turn server backoff into an automatic retry."""
    clock = Clock()
    events = []
    limiter = RequestGate(tmp_path / "requests.json", clock=clock.time,
                          sleep=clock.sleep, monotonic=clock.time,
                          jitter=lambda *args: 0, report=events.append)
    limiter.wait()

    def overload_during_wait(seconds):
        clock.sleep(seconds)
        limiter.backoff("120")

    limiter.sleep = overload_during_wait
    with pytest.raises(NetworkPolicyError, match="10-second gate budget.*server_cooldown"):
        limiter.wait()
    assert clock.sleeps == [10]
    assert events[-1]["reason"] == "server_cooldown"
    assert json.loads(limiter.path.read_text())["cooldown_until"] == clock.now + 120


def test_oversleep_cannot_reserve_slot_after_budget(tmp_path: Path) -> None:
    """Account for actual monotonic elapsed time, not only requested sleep durations."""
    clock = Clock()
    limiter = RequestGate(tmp_path / "requests.json", clock=clock.time,
                          sleep=clock.sleep, monotonic=clock.time, report=lambda event: None)
    limiter.wait()
    deadline = json.loads(limiter.path.read_text())["next_request"]
    limiter.sleep = lambda seconds: clock.sleep(601)
    with pytest.raises(NetworkPolicyError, match="600-second gate budget"):
        limiter.wait()
    assert json.loads(limiter.path.read_text())["next_request"] == deadline


def test_wall_clock_rollback_cannot_restart_contention_budget(tmp_path: Path) -> None:
    """A wall-clock correction does not grant another ten minutes of queue waiting."""
    clock = Clock()
    wall = [clock.now]
    limiter = RequestGate(tmp_path / "requests.json", clock=lambda: wall[0],
                          monotonic=clock.time, report=lambda event: None)
    limiter.wait()

    def rollback(seconds):
        clock.sleep(seconds)
        wall[0] -= 1

    limiter.sleep = rollback
    with pytest.raises(NetworkPolicyError, match="600-second gate budget"):
        limiter.wait()
    assert sum(clock.sleeps) <= 600
    assert clock.now > wall[0]


def test_transport_progress_reports_real_requests_without_sensitive_values(
    gate: tuple[RequestGate, Clock],
) -> None:
    """Diagnostics distinguish pacing from actual work without leaking query/body data."""
    limiter, clock = gate
    events = []
    guarded = guarded_send(lambda *args, **kwargs: response(), limiter, report=events.append)
    guarded(SimpleNamespace(url="https://mg.wikipedia.org/w/api.php?title=SECRET",
                            body="action=edit&token=SECRET&text=SECRET"))
    assert [event["phase"] for event in events] == ["start", "response"]
    assert "SECRET" not in json.dumps(events)


def test_native_failed_request_does_not_enter_retry_sleep_loop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The actual native wait method must fail before its first retry sleep."""
    import pywikibot
    from pywikibot import config
    from pywikibot.data.api import Request as APIRequest
    from pywikibot.exceptions import ApiTimeoutError

    sleeps = []
    monkeypatch.setattr(config, "max_retries", 0)
    monkeypatch.setattr(pywikibot, "sleep", lambda delay: sleeps.append(delay))
    request = object.__new__(APIRequest)
    with pytest.raises(ApiTimeoutError, match="Maximum retries"):
        request.wait()
    assert sleeps == []


def test_pywikibot_request_layer_does_not_retry_fatal_policy_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate the real native retry boundary with an offline fake HTTP request."""
    from pywikibot.comms import http
    from pywikibot.data.api import Request as APIRequest
    from pywikibot.exceptions import FatalServerError

    waits = []

    def fail(*args, **kwargs):
        raise FatalServerError("Overload: no replay")

    monkeypatch.setattr(http, "request", fail)
    fake = SimpleNamespace(site=object(), wait=lambda: waits.append(True))
    with pytest.raises(FatalServerError, match="no replay"):
        APIRequest._http_request(fake, True, "/w/api.php", None, None, "action=query")
    assert waits == []
