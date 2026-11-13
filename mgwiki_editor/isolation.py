"""Linux bubblewrap launcher builder. Entire tool-execution process must be inside.

No installation, privilege changes, network requests, or launches on import.
Launching only a helper does not isolate unrestricted tools in its parent agent.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .policy_store import StateError


def command(
    executable: list[str],
    *,
    work: Path,
    readonly_code: Path,
    broker_socket: Path | None = None,
    capability: Path | None = None,
    private_roots: tuple[Path, ...] = (),
) -> list[str]:
    tool = shutil.which("bwrap")
    if tool is None:
        raise StateError("bubblewrap unavailable; no permissive sandbox fallback.")
    if not executable or not executable[0].startswith("/"):
        raise StateError("Sandbox executable must be explicit absolute path.")
    work, readonly_code = Path(work).absolute(), Path(readonly_code).absolute()
    if not work.is_dir() or not readonly_code.is_dir():
        raise StateError("Existing dedicated agent work/code directories required.")
    if work == readonly_code or work in readonly_code.parents or readonly_code in work.parents:
        raise StateError("Agent work and trusted code mounts must be disjoint.")
    if work == Path("/") or readonly_code == Path("/"):
        raise StateError("Host root must never be mounted into agent sandbox.")
    for private in private_roots:
        private = Path(private).absolute()
        for mounted in (work, readonly_code):
            if private == mounted or private in mounted.parents or mounted in private.parents:
                raise StateError("Private broker/credential roots must not overlap agent mounts.")
    for path in (work, readonly_code, broker_socket, capability):
        if path is not None and any(p.is_symlink() for p in (Path(path), *Path(path).parents)):
            raise StateError("Symlink sandbox mount refused.")
    if (broker_socket is None) != (capability is None):
        raise StateError("Broker socket/capability mounts must be supplied together.")
    result = [
        tool,
        "--die-with-parent",
        "--new-session",
        "--unshare-all",
        "--unshare-user",
        "--cap-drop",
        "ALL",
        "--disable-userns",
        "--assert-userns-disabled",
        "--clearenv",
        "--setenv",
        "PATH",
        "/usr/bin:/bin",
        "--setenv",
        "HOME",
        "/home/agent",
        "--setenv",
        "PYTHONUTF8",
        "1",
    ]
    # No host root/home/proc/sys/run/credentials/state mount. Runtime binaries/libs only.
    for directory in ("/usr", "/lib", "/lib64", "/bin", "/sbin"):
        if Path(directory).exists():
            target = Path(directory).resolve()
            if Path(directory).is_symlink():
                result += ["--symlink", str(target), directory]
            else:
                result += ["--ro-bind", directory, directory]
    result += [
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--tmpfs",
        "/tmp",
        "--dir",
        "/home/agent",
        "--dir",
        "/run/mgwiki",
        "--ro-bind",
        str(readonly_code),
        "/app",
        "--bind",
        str(work),
        "/work",
        "--chdir",
        "/work",
    ]
    if broker_socket is not None:
        result += [
            "--ro-bind",
            str(broker_socket),
            "/run/mgwiki/broker.sock",
            "--ro-bind",
            str(capability),
            "/run/mgwiki/capability",
            "--setenv",
            "MGWIKI_BROKER_SOCKET",
            "/run/mgwiki/broker.sock",
            "--setenv",
            "MGWIKI_CAPABILITY_FILE",
            "/run/mgwiki/capability",
        ]
    return result + ["--", *executable]


def check(work: Path, code: Path) -> dict:
    """Bounded local namespace probe only; fake destinations, no external connections."""
    import os

    host_net = os.stat("/proc/self/ns/net").st_ino
    script = f"""
import errno, os, socket
assert os.stat('/proc/self/ns/net').st_ino != {host_net}
assert set(name for _, name in socket.if_nameindex()) <= {{'lo'}}
assert os.listdir('/home') == ['agent']
assert not os.path.exists('/run/mgwiki/capability')
assert 'NoNewPrivs:\\t1' in open('/proc/self/status').read()
try:
    open('/app/.isolation-write-probe', 'xb')
except OSError as exc:
    assert exc.errno == errno.EROFS
else:
    raise AssertionError('trusted code unexpectedly writable')
print('isolated-local-probe-ok')
"""
    result = subprocess.run(
        command(["/usr/bin/python3", "-I", "-c", script], work=work, readonly_code=code),
        capture_output=True,
        timeout=10,
        check=False,
        close_fds=True,
        env={"PATH": "/usr/bin:/bin"},
        preexec_fn=_restrict_child,
    )
    return {
        "available": result.returncode == 0,
        "returncode": result.returncode,
        "details": result.stderr.decode("utf-8", errors="replace")[:2000],
        "verified": ["private_mount_pid_network_namespaces", "host_home_hidden"]
        if result.returncode == 0
        else [],
        "limits": "Probe only. Whole OpenCode tool server and provider/control-plane "
        "must also be isolated; deployment not performed.",
    }


def run(executable: list[str], **configuration) -> int:
    """Explicit host-side launch, never invoked by broker RPC or automatically by tests."""
    return subprocess.run(
        command(executable, **configuration),
        check=False,
        close_fds=True,
        env={"PATH": "/usr/bin:/bin"},
        preexec_fn=_restrict_child,
    ).returncode


def _restrict_child() -> None:
    """Standalone launcher child only; do not use from a threaded application."""
    import ctypes
    import resource

    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(38, 1, 0, 0, 0) != 0:  # PR_SET_NO_NEW_PRIVS
        raise OSError(ctypes.get_errno(), "Cannot set no_new_privs; sandbox launch refused.")
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
