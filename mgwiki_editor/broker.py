"""Bounded local Unix RPC. Capability authority and credentials stay server-side."""

from __future__ import annotations

import json
import os
import socket
import socketserver
import stat
import struct
from pathlib import Path
from typing import TYPE_CHECKING

from .policy_store import StateError
from .policy_store import shape as _shape

if TYPE_CHECKING:
    from .gateway import Gateway

MAX_MESSAGE = 6_000_000
COMMANDS = (
    "status",
    "init",
    "artifact",
    "submit",
    "read",
    "lookup",
    "countries",
    "service-probe",
    "plan",
    "assign",
    "revoke-assignment",
    "accept-section",
    "assemble",
    "record-issue",
    "accept-issue",
    "review",
    "prepare",
    "attest-proposal",
    "publish",
    "reconcile",
    "task-depend",
    "skip",
    "ack-alert",
    "vocab",
    "vocab-audit",
    "coverage",
    "links-build",
    "dictionary-index",
    "vocabulary-report",
    "links-query",
    "image-info",
    "submit-assigned",
    "resume",
    "artifact-history",
    "category-info",
    "plan-local",
    "template-info",
    "source-expand",
    "render-check",
    "citation-audit",
    "metadata-audit",
    "license-evidence",
    "license-report",
)


def loads(raw: str | bytes):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise StateError("Duplicate protocol field.")
            value[key] = item
        return value

    def invalid_constant(value):
        raise StateError("Non-finite JSON value refused.")

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid_constant)


def message(value: dict) -> bytes:
    raw = (
        json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(",", ":")).encode()
        + b"\n"
    )
    if len(raw) > MAX_MESSAGE:
        raise StateError("Protocol message too large; split artifact/evidence work.")
    return raw


def handle(gateway: Gateway, envelope: dict) -> dict:
    """Also usable in fake-transport integration tests. No admin methods in RPC."""
    try:
        _shape(envelope, {"schema", "capability", "command", "arguments"})
        if type(envelope["schema"]) is not int or envelope["schema"] != 1:
            raise StateError("Unsupported broker protocol schema.")
        if envelope["command"] not in COMMANDS:
            raise StateError("Unknown broker command.")
        return {
            "ok": True,
            **gateway.dispatch(envelope["capability"], envelope["command"], envelope["arguments"]),
        }
    except Exception as exc:
        # Never return arbitrary backend exceptions, tracebacks, request bodies, or tokens.
        result = {
            "ok": False,
            "error": type(exc).__name__,
            "message": str(exc)
            if isinstance(exc, StateError)
            else "Operation failed; work/receipt retained. Inspect status, never replay saves.",
            "next_eligible_at": getattr(exc, "next_eligible_at", None),
        }
        if isinstance(exc, StateError) and hasattr(exc, "decision"):
            result["decision"] = exc.decision
        try:
            cap = gateway.authenticate(envelope.get("capability"))
            result["alerts"] = gateway.recovery.alerts(cap["run"])
        except Exception:
            pass
        return result


class _Handler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        self.request.settimeout(20)
        _, uid, _ = struct.unpack(
            "3i",
            self.request.getsockopt(
                socket.SOL_SOCKET,
                socket.SO_PEERCRED,
                struct.calcsize("3i"),
            ),
        )
        if uid != self.server.allowed_uid:
            self.wfile.write(message({"ok": False, "error": "PeerDenied"}))
            return
        try:
            raw = self.rfile.readline(MAX_MESSAGE + 1)
            if len(raw) > MAX_MESSAGE or not raw.endswith(b"\n"):
                raise StateError("Incomplete/oversized broker request.")
            result = handle(self.server.gateway, loads(raw))
            self.wfile.write(message(result))
        except (ValueError, StateError, OSError):
            self.wfile.write(message({"ok": False, "error": "ProtocolError"}))


class Broker(socketserver.UnixStreamServer):
    """Serial server: no parallel Wikipedia workers, no overwrite of an existing socket."""

    def __init__(self, path: Path, gateway: Gateway, *, allowed_uid: int | None = None) -> None:
        path = Path(path).absolute()
        if path.exists() or path.is_symlink() or any(p.is_symlink() for p in path.parents):
            raise StateError("Broker socket path exists/unsafe; never unlink another service.")
        self.gateway = gateway
        self.allowed_uid = os.getuid() if allowed_uid is None else allowed_uid
        if type(self.allowed_uid) is not int or self.allowed_uid < 0:
            raise StateError("Broker peer UID must be explicit nonnegative integer.")
        self.path, self.created_inode = path, None
        super().__init__(str(path), _Handler)
        self.created_inode = path.stat().st_ino
        os.chmod(path, 0o600)  # This newly created socket only; no existing access-right changes.

    def server_close(self) -> None:
        super().server_close()
        if self.created_inode is not None:
            try:
                current = self.path.lstat()
                if stat.S_ISSOCK(current.st_mode) and current.st_ino == self.created_inode:
                    self.path.unlink()
            except FileNotFoundError:
                pass


def call(path: Path, capability: str, command: str, arguments: dict, *, timeout: int = 600) -> dict:
    envelope = {"schema": 1, "capability": capability, "command": command, "arguments": arguments}
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as stream:
        stream.settimeout(timeout)
        stream.connect(str(path))
        stream.sendall(message(envelope))
        with stream.makefile("rb") as response:
            raw = response.readline(MAX_MESSAGE + 1)
    if len(raw) > MAX_MESSAGE or not raw.endswith(b"\n"):
        raise StateError("Broker response lost/oversized; inspect status, never replay publish.")
    return loads(raw)


def capability_file(path: Path) -> str:
    path = Path(path).absolute()
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise StateError("Symlink capability path refused.")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise StateError("Capability must be a regular protected file.")
        if info.st_mode & 0o077 or info.st_uid != os.getuid():
            raise StateError("Capability must be owner-only and owned by this client UID.")
        value = stream.read(301)
    if not 32 <= len(value.strip()) <= 200:
        raise StateError("Invalid capability file.")
    return value.decode("ascii").strip()
