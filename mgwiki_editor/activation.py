"""Trusted-host activation using an EXISTING scoped grant. Never provisions authority."""

from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path

from . import isolation, secure_files
from .broker import call, capability_file, loads
from .policy_store import StateError
from .policy_store import shape as _shape


def _path(value) -> Path:
    if not isinstance(value, str) or not Path(value).is_absolute() or ".." in Path(value).parts:
        raise StateError("Activation paths must be explicit absolute paths.")
    path = Path(value)
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise StateError("Symlink activation path refused.")
    return path


def _protected(root: Path, name: str) -> bytes:
    with secure_files.parent(root, name) as (directory, leaf):
        fd = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise StateError("Activation config must be an owner-only regular host file.")
            raw = stream.read(65_537)
            if len(raw) > 65_536:
                raise StateError("Activation config exceeds the bounded host specification.")
            return raw


def activate(config: Path, *, check_only: bool = False) -> dict:
    """Authenticate exact host-declared scope, then launch approved isolated tool process.

    Callable by trusted standalone host launcher only, never broker/MCP. Config is
    a host declaration, not proof that an arbitrary executable integrates all tools.
    """
    config = _path(str(config.absolute()))
    raw = _protected(config.parent, config.name)
    spec = loads(raw)
    _shape(
        spec,
        {
            "work",
            "code",
            "socket",
            "capability_file",
            "private_roots",
            "executable",
            "run",
            "manifest",
            "tool_scope",
        },
    )
    if spec["tool_scope"] != "whole_tool_process":
        raise StateError("Activation must declare complete tool-process isolation, not one helper.")
    _shape(
        spec["manifest"],
        {"intent", "source_language", "source_title", "article_title"},
        {"existing_title"},
    )
    if spec["manifest"]["intent"] not in {"development", "draft_only", "sandbox_edit"}:
        raise StateError("Activation requires an explicit original run intent.")
    if not isinstance(spec["run"], str) or not spec["run"]:
        raise StateError("Activation requires exact trusted run identity.")
    if (
        not isinstance(spec["executable"], list)
        or not spec["executable"]
        or any(not isinstance(arg, str) or "\x00" in arg for arg in spec["executable"])
    ):
        raise StateError("Activation executable needs explicit arguments, never shell text.")
    work, code = _path(spec["work"]), _path(spec["code"])
    socket, capfile = _path(spec["socket"]), _path(spec["capability_file"])
    if not isinstance(spec["private_roots"], list) or not spec["private_roots"]:
        raise StateError("Activation requires explicit hidden broker/credential roots.")
    private = tuple(_path(value) for value in spec["private_roots"])
    if any(not root.is_dir() for root in private):
        raise StateError("Activation private roots must be existing host directories.")
    for path in (config, socket, capfile):
        if not any(path.is_relative_to(root) for root in private):
            raise StateError("Config/socket/capability must reside under declared private roots.")
    configuration = {
        "work": work,
        "readonly_code": code,
        "broker_socket": socket,
        "capability": capfile,
        "private_roots": private,
    }
    # Validate mounts before reading grant or contacting broker. No bypass on failure.
    isolation.command(spec["executable"], **configuration)
    sockinfo = socket.lstat()
    if (
        not stat.S_ISSOCK(sockinfo.st_mode)
        or sockinfo.st_uid != os.getuid()
        or sockinfo.st_mode & 0o077
    ):
        raise StateError("Activation needs existing owner-only broker socket owned by this UID.")
    token = capability_file(capfile)
    response = call(socket, token, "status", {}, timeout=10)
    result = response.get("result")
    if (
        response.get("ok") is not True
        or not isinstance(result, dict)
        or result.get("run") != spec["run"]
        or result.get("manifest") != spec["manifest"]
        or result.get("intent") != spec["manifest"]["intent"]
    ):
        raise StateError("Broker identity/intent differs from protected activation specification.")
    current = socket.lstat()
    if capability_file(capfile) != token or (current.st_dev, current.st_ino) != (
        sockinfo.st_dev,
        sockinfo.st_ino,
    ):
        raise StateError("Activation grant/socket changed during authentication.")
    report = {
        "schema": 1,
        "config_sha256": hashlib.sha256(raw).hexdigest(),
        "run": spec["run"],
        "intent": result["intent"],
        "status": "authenticated_configuration_checked_not_launched",
        "whole_tool_integration": "host_declared_not_automatically_proven",
        "capabilities_provisioned": False,
        "account_verified": False,
        "limits": "Existing grant only; no setup, privilege/credential changes, source "
        "requests, article attestations or save. Host must ensure approved "
        "executable contains ALL tool execution and approved control-plane IPC.",
    }
    if not check_only:
        report["returncode"] = isolation.run(spec["executable"], **configuration)
        report["status"] = "isolated_process_exited"
    return report
