"""Conservative, process-shared pacing for the harness's approved API transports."""

from __future__ import annotations

import fcntl
import json
import math
import os
import random
import sys
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

REQUEST_INTERVAL = 10
EDIT_INTERVAL = 10
MAX_GATE_WAIT = 10


class NetworkPolicyError(RuntimeError):
    """Network use was blocked, deferred, or exhausted its bounded wait budget."""


def report_progress(event: dict[str, Any]) -> None:
    """Report small machine-readable transport events without query text or credentials."""
    print(json.dumps(event, ensure_ascii=True), file=sys.stderr, flush=True)


def retry_after_seconds(value: str, now: float) -> float:
    """Accept Retry-After delta seconds and HTTP dates without shortening server cooldowns."""
    try:
        seconds = float(value)
    except ValueError:
        try:
            date = parsedate_to_datetime(value)
            if date.tzinfo is None:
                date = date.replace(tzinfo=UTC)
            seconds = date.timestamp() - now
        except (ValueError, TypeError, OverflowError):
            return 0
    return max(0, seconds) if math.isfinite(seconds) else 0


class RequestGate:
    """Share read/write pacing and cooldowns between CLI processes using a locked state file."""

    def __init__(
        self, path: Path | None = None, *, clock: Callable[[], float] = time.time,
        sleep: Callable[[float], None] = time.sleep,
        jitter: Callable[[float, float], float] = random.uniform,
        report: Callable[[dict[str, Any]], None] = report_progress,
    ) -> None:
        """Configure a gate without opening files, sleeping, or making network requests."""
        state_home = Path(os.getenv("XDG_STATE_HOME", str(Path.home() / ".local/state")))
        self.path = path or state_home / "mgwiki-editor/wikimedia-requests.json"
        self.clock, self.sleep, self.jitter = clock, sleep, jitter
        self.report = report

    @contextmanager
    def state(self) -> Iterator[dict[str, Any]]:
        """Lock, validate, and durably update the small shared request state."""
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with self.path.open("a+", encoding="utf-8") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            try:
                stream.seek(0)
                raw = stream.read()
                try:
                    state = json.loads(raw) if raw else {}
                except ValueError as exc:
                    raise NetworkPolicyError(
                        "Corrupt request pacing state; no request sent.",
                    ) from exc
                if not isinstance(state, dict) or any(
                    not isinstance(state.get(key, 0), (int, float))
                    or not math.isfinite(state.get(key, 0)) or state.get(key, 0) < 0
                    for key in ("next_request", "next_write", "failures", "cooldown_until")
                ):
                    raise NetworkPolicyError("Invalid request pacing state; no request sent.")
                yield state
                stream.seek(0)
                stream.truncate()
                json.dump(state, stream, sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)

    def wait(self, *, write: bool = False) -> None:
        """Use the conservative 10-second end of the requested 5–10 second request range."""
        waited = 0.0
        while True:
            with self.state() as state:
                now = self.clock()
                ready = max(
                    state.get("next_request", 0), state.get("next_write", 0) if write else 0,
                )
                delay = max(0, ready - now)
                reason = (
                    "server_cooldown" if state.get("cooldown_until", 0) > now
                    else "shared_request_spacing"
                )
                if not delay:
                    state["next_request"] = now + REQUEST_INTERVAL
                    if write:
                        state["next_write"] = now + EDIT_INTERVAL
                    return
            if delay > MAX_GATE_WAIT - waited:
                self.report({
                    "event": "network_deferred", "reason": reason,
                    "retry_in_seconds": round(delay, 1),
                })
                raise NetworkPolicyError(
                    f"Network wait {delay:.1f}s exceeds the {MAX_GATE_WAIT}-second gate budget "
                    f"({reason}); task deferred, cooldown preserved. Do not poll or retry now.",
                )
            self.report({"event": "network_wait", "reason": reason, "seconds": round(delay, 1)})
            self.sleep(delay)
            waited += delay

    def backoff(self, retry_after: str = "") -> float:
        """Persist exponential cooldown; three consecutive overloads open a 15-minute circuit."""
        with self.state() as state:
            now = self.clock()
            failures = min(int(state.get("failures", 0)) + 1, 8)
            delay = max(30 * 2 ** (failures - 1) + self.jitter(0, 5),
                        retry_after_seconds(retry_after, now))
            if failures >= 3:
                delay = max(delay, 900)
            deadline = max(state.get("next_request", 0), now + delay)
            state.update(failures=failures, next_request=deadline, cooldown_until=deadline)
            return delay

    def success(self) -> None:
        """Reset consecutive failures without cancelling any outstanding shared cooldown."""
        with self.state() as state:
            state["failures"] = 0


def api_url_allowed(url: str) -> bool:
    """Permit required HTTPS Wikipedia APIs and central-auth APIs, not linked web pages."""
    try:
        parsed = urlsplit(url)
        host = parsed.hostname or ""
        port = parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme == "https" and not parsed.username and not parsed.password
        and not parsed.fragment and port in {None, 443} and parsed.path == "/w/api.php"
        and (host.endswith(".wikipedia.org") or host == "login.wikimedia.org")
    )


def guarded_send(
    send: Callable[..., Any], gate: RequestGate, *,
    report: Callable[[dict[str, Any]], None] = report_progress,
) -> Callable[..., Any]:
    """Guard actual HTTP attempts, including Pywikibot's own retries, not just CLI calls."""
    def request(prepared: Any, **kwargs: Any) -> Any:
        if not api_url_allowed(prepared.url):
            raise NetworkPolicyError(
                "Only approved Wikimedia API URLs are allowed by this transport.",
            )
        parameters = parse_qs(urlsplit(prepared.url).query)
        if prepared.body:
            body = (
                prepared.body.decode("utf-8") if isinstance(prepared.body, bytes) else prepared.body
            )
            parameters.update(parse_qs(body))
        write = parameters.get("action") == ["edit"]
        gate.wait(write=write)
        # Never print titles, request bodies, arbitrary action values, or tokens.
        action = parameters.get("action", [""])[0]
        action = action if action in {"query", "parse", "edit", "login", "clientlogin"} else "api"
        report({"event": "wikimedia_request", "phase": "start",
                "host": urlsplit(prepared.url).hostname, "action": action})
        # Never follow a response redirect, even to a URL named in wiki content.
        kwargs["allow_redirects"] = False
        try:
            response = send(prepared, **kwargs)
        except Exception as exc:
            report({"event": "wikimedia_request", "phase": "failed", "action": action})
            if write:
                raise NetworkPolicyError(
                    "Edit transport failed; save is unconfirmed. No automatic resubmission.",
                ) from exc
            raise
        report({"event": "wikimedia_request", "phase": "response",
                "action": action, "status": response.status_code})
        if 300 <= response.status_code < 400:
            raise NetworkPolicyError("API redirect not followed; no external link was opened.")
        error = ""
        if response.status_code == 200:
            try:
                payload = response.json()
                api_error = payload.get("error", {}) if isinstance(payload, dict) else {}
                error = (
                    api_error.get("code", "") if isinstance(api_error, dict) else "invalid_error"
                )
            except ValueError as exc:
                if write:
                    raise NetworkPolicyError(
                        "Edit response is not JSON; save unconfirmed. No automatic resubmission.",
                    ) from exc
        if response.status_code in {429, 503} or error in {"maxlag", "ratelimited"}:
            delay = gate.backoff(response.headers.get("Retry-After", ""))
            raise NetworkPolicyError(
                f"Wikimedia overloaded ({error or response.status_code}); "
                f"shared cooldown {delay:.0f}s. No automatic resubmission.",
            )
        if write and (response.status_code >= 400 or error):
            raise NetworkPolicyError(
                f"Edit returned {error or response.status_code}; no automatic resubmission.",
            )
        if response.status_code == 200:
            gate.success()
        return response

    return request


def no_interactive_input(*args: Any, **kwargs: Any) -> str:
    """Fail closed instead of asking for passwords, captcha, or other terminal input."""
    raise NetworkPolicyError("Interactive input disabled; retain draft and report blocked state.")


def install_wikimedia_transport() -> None:
    """Install idempotent pacing before Site creation can contact Wikimedia."""
    import pywikibot
    from pywikibot import config
    from pywikibot.comms import http
    from pywikibot.exceptions import FatalServerError
    from urllib3.util.retry import Retry

    config.maxlag = 5
    # Native retry waits can silently add 30/60/... seconds per failed call.
    # Fail the command instead; persisted cooldowns govern later attempts.
    config.max_retries = 0
    config.retry_wait = max(config.retry_wait, 30)
    config.retry_max = max(config.retry_wait, min(config.retry_max, 300))
    config.socket_timeout = (10, 30)
    config.solve_captcha = False
    for name in ("input", "input_choice", "input_list_choice", "input_yn"):
        setattr(pywikibot, name, no_interactive_input)
    # Hidden adapter retries would occur underneath the paced send boundary.
    for adapter in getattr(http.session, "adapters", {}).values():
        adapter.max_retries = Retry(total=0, connect=0, read=False, redirect=0, status=0)
    if not getattr(http.session, "_mgwiki_guard", False):
        guarded = guarded_send(http.session.send, RequestGate())

        def send_without_replay(prepared: Any, **kwargs: Any) -> Any:
            try:
                return guarded(prepared, **kwargs)
            except NetworkPolicyError as exc:
                # Pywikibot retries arbitrary Exception instances, but not this
                # documented fatal transport exception. Never replay an edit.
                raise FatalServerError(str(exc)) from exc

        http.session.send = send_without_replay
        http.session._mgwiki_guard = True
    # The shared transport gate is the sole normal pacing authority. Native
    # delays are process-multiplied and can add minutes of duplicate sleeping.
    # Set these only after the guarded transport is installed successfully.
    config.minthrottle = 0
    config.maxthrottle = 0
    config.put_throttle = 0


class NoRedirect(HTTPRedirectHandler):
    """Keep dictionary responses from navigating to external URLs."""

    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        """Reject redirect traversal rather than opening another URL."""
        raise NetworkPolicyError("Dictionary redirect not followed.")


def dictionary_open(request: Request, *, timeout: int) -> Any:
    """Pace real dictionary calls too; they can trigger upstream Wikimedia reads."""
    gate = RequestGate()
    gate.wait()
    # No proxy discovery: the explicitly configured LAN dictionary is the only origin.
    try:
        return build_opener(ProxyHandler({}), NoRedirect()).open(request, timeout=timeout)
    except HTTPError as exc:
        if exc.code in {429, 503}:
            delay = gate.backoff(exc.headers.get("Retry-After", ""))
            raise NetworkPolicyError(
                f"Dictionary overloaded ({exc.code}); shared cooldown {delay:.0f}s. Stop.",
            ) from exc
        raise
