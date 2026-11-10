"""Scoped transport hooks. Observations originate at actual HTTP boundaries only."""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Observation:
    service: str
    id: str
    at: float
    monotonic: float
    boot: str
    status: int | None
    safe_read: bool
    missing: bool = False
    valid_success: bool = False
    retry_after: str = ""


@dataclass(frozen=True)
class Hooks:
    before: Callable[[str, bool, str], None]
    observe: Callable[[Observation], None]
    clock: Callable[[], float] = time.time
    monotonic: Callable[[], float] = time.monotonic
    boot: str = "unknown"
    gate: object | None = None


_hooks: ContextVar[Hooks | None] = ContextVar("mgwiki_transport_hooks", default=None)


def request_gate():
    hooks = _hooks.get()
    return hooks.gate if hooks is not None else None


def boot_id() -> str:
    """Explicit local read; imports never inspect /proc."""
    try:
        return Path("/proc/sys/kernel/random/boot_id").read_text(encoding="ascii").strip()
    except OSError:
        return "unknown"


def service_id(url: str, *, dictionary: bool = False) -> str:
    parsed = urlsplit(url)
    return ("dictionary:" if dictionary else "wiki:") + parsed.netloc.lower()


def before(url: str, *, safe_read: bool, dictionary: bool = False) -> None:
    hooks = _hooks.get()
    if hooks is not None:
        hooks.before(service_id(url, dictionary=dictionary), safe_read, url)


def observe(
    url: str, status: int | None, *, safe_read: bool = True, dictionary: bool = False,
    missing: bool = False, valid_success: bool = False, retry_after: str = "",
) -> None:
    hooks = _hooks.get()
    if hooks is not None:
        hooks.observe(Observation(
            service_id(url, dictionary=dictionary), uuid.uuid4().hex, hooks.clock(),
            hooks.monotonic(), hooks.boot, status, safe_read, missing, valid_success, retry_after,
        ))


@contextmanager
def transport_hooks(hooks: Hooks) -> Iterator[None]:
    token = _hooks.set(hooks)
    try:
        yield
    finally:
        _hooks.reset(token)
