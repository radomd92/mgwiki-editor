"""Local protocol/descriptor tests with fake gateway/client; no external network."""

import io
import json
import os
import socket
import subprocess
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from mgwiki_editor import control, isolation, secure_files
from mgwiki_editor.broker import Broker, call, capability_file, loads, message
from mgwiki_editor.policy_store import StateError


@pytest.mark.parametrize("raw", ['{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}'])
def test_protocol_rejects_ambiguous_or_nonfinite_data(raw):
    with pytest.raises(StateError):
        loads(raw)


def test_protocol_message_bounded(monkeypatch):
    monkeypatch.setattr("mgwiki_editor.broker.MAX_MESSAGE", 40)
    with pytest.raises(StateError, match="large"):
        message({"content": "x" * 100})


def test_unix_rpc_roundtrip_serial_fake_gateway_and_exclusive_socket(tmp_path):
    class Fake:
        def dispatch(self, token, command, arguments):
            assert token == "capability"
            return {"result": {"command": command, "arguments": arguments}, "alerts": []}

    path = tmp_path / "broker.sock"
    with Broker(path, Fake()) as server:
        assert path.stat().st_mode & 0o777 == 0o600
        with pytest.raises(StateError, match="exists"):
            Broker(path, Fake())
        worker = threading.Thread(target=server.handle_request)
        worker.start()
        response = call(path, "capability", "status", {})
        worker.join(timeout=2)
        assert not worker.is_alive()
        assert response["ok"] is True
        assert response["result"]["command"] == "status"
    assert not path.exists()


def test_unix_peer_identity_checked_before_dispatch(tmp_path):
    class Fake:
        def dispatch(self, *args):
            pytest.fail("Wrong peer reached gateway")

    path = tmp_path / "broker.sock"
    with Broker(path, Fake(), allowed_uid=os.getuid() + 1) as server:
        worker = threading.Thread(target=server.handle_request)
        worker.start()
        with socket.socket(socket.AF_UNIX) as stream:
            stream.connect(str(path))
            response = loads(stream.recv(1024))
        worker.join(timeout=2)
        assert response == {"ok": False, "error": "PeerDenied"}


def test_stdio_mcp_exposes_closed_commands_no_admin_and_routes_to_scoped_client(monkeypatch):
    seen = []

    def fake_client(path, capfile, command, args):
        seen.append((command, args))
        return {"ok": True, "result": {"stage": "pinned"}}

    monkeypatch.setattr(control, "client", fake_client)
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "mgwiki", "arguments": {"action": "status", "arguments": {}}},
        },
        {"jsonrpc": "2.0", "id": 4, "method": "execute", "params": {"command": "curl"}},
    ]
    output = io.StringIO()
    control.mcp(
        Path("socket"),
        Path("capfile"),
        input_stream=io.StringIO("\n".join(json.dumps(r) for r in requests)),
        output_stream=output,
    )
    responses = [loads(line) for line in output.getvalue().splitlines()]
    assert len(responses) == 4
    schema = responses[1]["result"]["tools"][0]["inputSchema"]
    assert "provision" not in schema["properties"]["action"]["enum"]
    assert "execute" not in schema["properties"]["action"]["enum"]
    assert seen == [("status", {})]
    assert "error" in responses[-1]


def test_alert_printed_before_ack_and_lost_ack_does_not_replay_save(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(control, "capability_file", lambda path: "token")

    def fake_call(path, token, command, args):
        calls.append(command)
        if command == "ack-alert":
            assert "SEVERE SERVICE OUTAGE DETECTED" in capsys.readouterr().err
            raise OSError("ack lost")
        return {
            "ok": True,
            "alerts": [
                {
                    "episode": "episode",
                    "text": "SEVERE SERVICE OUTAGE DETECTED\n\nFake test assessment.",
                }
            ],
        }

    monkeypatch.setattr(control, "call", fake_call)
    response = control.client(Path("socket"), Path("cap"), "status", {})
    assert response["ok"] is True
    assert response["delivery_warnings"][0]["status"] == "pending_replay"
    assert calls == ["status", "ack-alert"]


@pytest.mark.parametrize(
    "name",
    [
        "../outside",
        "/etc/passwd",
        "a/../../x",
        "a//x",
        "a/./x",
        "a\\x",
    ],
)
def test_broker_files_cannot_escape_root(tmp_path, name):
    with pytest.raises(StateError):
        secure_files.write(tmp_path, name, b"no")


def test_secure_files_preserve_bytes_and_reject_overwrites_symlinks_and_fifo(tmp_path):
    first = b"source\r\nexact\n"
    digest = secure_files.write(tmp_path, "a/file.wiki", first)
    assert secure_files.read(tmp_path, "a/file.wiki") == first
    with pytest.raises(FileExistsError):
        secure_files.write(tmp_path, "a/file.wiki", b"changed")
    with pytest.raises(StateError, match="changed"):
        secure_files.write(tmp_path, "a/file.wiki", b"changed", expected="wrong")
    secure_files.write(tmp_path, "a/file.wiki", b"changed", expected=digest)
    (tmp_path / "link").symlink_to(tmp_path / "a", target_is_directory=True)
    with pytest.raises(OSError):
        secure_files.read(tmp_path, "link/file.wiki")
    os.mkfifo(tmp_path / "fifo")
    with pytest.raises(StateError, match="regular"):
        secure_files.read(tmp_path, "fifo")


def test_capability_file_is_bounded_regular_and_no_symlink(tmp_path):
    path = tmp_path / "cap"
    path.write_text("x" * 43)
    path.chmod(0o600)
    assert capability_file(path) == "x" * 43
    path.write_text("x" * 301)
    with pytest.raises(StateError):
        capability_file(path)
    link = tmp_path / "link"
    link.symlink_to(path)
    with pytest.raises(StateError):
        capability_file(link)


def test_capability_rejects_world_readable_file_without_changing_permissions(tmp_path):
    path = tmp_path / "cap"
    path.write_text("x" * 43)
    path.chmod(0o644)
    with pytest.raises(StateError, match="owner-only"):
        capability_file(path)
    assert path.stat().st_mode & 0o777 == 0o644


def test_doctor_checks_descriptors_never_reads_token_or_connects(tmp_path, monkeypatch):
    path, cap = tmp_path / "socket", tmp_path / "cap"
    cap.write_text("secret never read")
    cap.chmod(0o600)
    with socket.socket(socket.AF_UNIX) as listener:
        listener.bind(str(path))
        path.chmod(0o600)
        monkeypatch.setattr(control, "client", lambda *a: pytest.fail("Doctor contacted broker"))
        monkeypatch.setattr(Path, "read_bytes", lambda *a: pytest.fail("Doctor read token"))
        result = control.doctor(path, cap)
        assert result["local_prerequisites_present"]
        assert not result["deployment_verified"]
        assert "secret" not in json.dumps(result)
        cap.chmod(0o644)
        assert not control.doctor(path, cap)["local_prerequisites_present"]


def test_doctor_missing_configuration_is_failure_without_setup(monkeypatch, capsys):
    monkeypatch.delenv("MGWIKI_BROKER_SOCKET", raising=False)
    monkeypatch.delenv("MGWIKI_CAPABILITY_FILE", raising=False)
    assert control.main(["doctor"]) == 1
    result = json.loads(capsys.readouterr().out)
    assert all(row["status"] == "missing_configuration" for row in result["checks"])
    assert result["deployment_verified"] is False


def test_sandbox_builder_never_shares_net_host_home_or_credential_state(tmp_path, monkeypatch):
    work, code = tmp_path / "work", tmp_path / "code"
    work.mkdir()
    code.mkdir()
    monkeypatch.setattr(isolation.shutil, "which", lambda name: "/usr/bin/bwrap")
    args = isolation.command(
        ["/usr/bin/python3", "-I", "-c", "pass"], work=work, readonly_code=code
    )
    assert "--unshare-all" in args and "--clearenv" in args and "--cap-drop" in args
    assert "--share-net" not in args and "--unshare-user-try" not in args
    assert "--ro-bind" in args and "--new-session" in args
    assert "/home/rado" not in args and "/home/jagwar" not in args
    assert args[-4:] == ["/usr/bin/python3", "-I", "-c", "pass"]
    monkeypatch.setattr(isolation.shutil, "which", lambda name: None)
    with pytest.raises(StateError, match="no permissive"):
        isolation.command(["/usr/bin/true"], work=work, readonly_code=code)


def test_sandbox_probe_reports_failure_without_claiming_enforcement(tmp_path, monkeypatch):
    monkeypatch.setattr(isolation, "command", lambda *args, **kwargs: ["fake-bwrap"])
    monkeypatch.setattr(
        isolation.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stderr=b"namespace forbidden"),
    )
    result = isolation.check(tmp_path, tmp_path)
    assert result["available"] is False
    assert result["verified"] == []
    assert "deployment not performed" in result["limits"]


def test_stdio_protocol_handles_bad_data_without_executing_or_crashing(monkeypatch):
    monkeypatch.setattr(control, "client", lambda *a: pytest.fail("Invalid data reached broker"))
    output = io.StringIO()
    control.mcp(
        Path("socket"),
        Path("cap"),
        input_stream=io.StringIO('not JSON\n[]\n{"jsonrpc":"2.0","id":1,"method":"eval"}\n'),
        output_stream=output,
    )
    assert len(output.getvalue().splitlines()) == 3
    assert all("error" in loads(line) for line in output.getvalue().splitlines())


def test_client_import_needs_only_standard_library_and_has_no_effects():
    root = Path(__file__).resolve().parents[1]
    script = f"""
import sys, socket, pathlib, builtins, time
sys.path.insert(0, {str(root)!r})
def forbidden(*args, **kwargs):
    raise AssertionError('import attempted effect')
socket.socket = forbidden
socket.create_connection = forbidden
pathlib.Path.open = forbidden
builtins.open = forbidden
time.sleep = forbidden
import mgwiki_editor.control
assert 'mgwiki_editor.core' not in sys.modules
assert 'pywikibot' not in sys.modules
assert 'mwparserfromhell' not in sys.modules
"""
    result = subprocess.run(
        [sys.executable, "-I", "-c", script], capture_output=True, timeout=10, check=False
    )
    assert result.returncode == 0, result.stderr.decode()
