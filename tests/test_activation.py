"""Trusted-start checks with temporary files/fake RPC; no real grant or deployment."""

import copy
import json
import socket

import pytest

from mgwiki_editor import activation, control, isolation
from mgwiki_editor.policy_store import StateError


@pytest.fixture
def setup(tmp_path, monkeypatch):
    work, code, private = (tmp_path / name for name in ("work", "runtime", "private"))
    for path in (work, code, private):
        path.mkdir(mode=0o700)
    config, capfile, sockpath = (private / name for name in ("activation.json", "run.cap", "sock"))
    capfile.write_text("x" * 43)
    capfile.chmod(0o600)
    server = socket.socket(socket.AF_UNIX)
    server.bind(str(sockpath))
    sockpath.chmod(0o600)
    manifest = {"intent": "development", "source_language": "en", "source_title": "Water",
                "article_title": "Rano"}
    spec = {"work": str(work), "code": str(code), "private_roots": [str(private)],
            "socket": str(sockpath), "capability_file": str(capfile), "run": "water",
            "manifest": manifest, "executable": ["/app/bin/approved-tools"],
            "tool_scope": "whole_tool_process"}
    config.write_text(json.dumps(spec))
    config.chmod(0o600)
    monkeypatch.setattr(isolation.shutil, "which", lambda name: "/usr/bin/bwrap")
    calls, launches = [], []
    def request(path, token, action, args, *, timeout):
        calls.append((path, token, action, args, timeout))
        return {"ok": True, "result": {"run": "water", "intent": "development",
                                       "manifest": copy.deepcopy(manifest)}}
    monkeypatch.setattr(activation, "call", request)
    monkeypatch.setattr(isolation, "run", lambda executable, **kw: launches.append(
        (executable, kw)) or 0)
    yield config, spec, capfile, calls, launches
    server.close()


def rewrite(config, spec):
    config.write_text(json.dumps(spec))


def test_check_authenticates_exact_run_intent_without_launch_or_token_disclosure(setup):
    config, spec, capfile, calls, launches = setup
    result = activation.activate(config, check_only=True)
    assert result["status"] == "authenticated_configuration_checked_not_launched"
    assert not result["capabilities_provisioned"] and not result["account_verified"]
    assert not launches and len(calls) == 1
    assert calls[0][2:] == ("status", {}, 10)
    assert capfile.read_text() not in json.dumps(result)


def test_activation_launches_only_isolated_declared_process_with_existing_grant(setup):
    config, spec, capfile, calls, launches = setup
    result = activation.activate(config)
    assert result["status"] == "isolated_process_exited" and result["returncode"] == 0
    assert launches[0][0] == spec["executable"]
    assert launches[0][1]["capability"] == capfile
    assert not result["capabilities_provisioned"]


@pytest.mark.parametrize("change", [
    {"run": "different"}, {"tool_scope": "only_a_helper"}, {"executable": "shell text"},
    {"private_roots": []}, {"capability_file": "relative.cap"},
    {"extra": "never printed secret"},
])
def test_invalid_or_mismatched_host_config_never_launches(setup, change):
    config, spec, _, _, launches = setup
    spec.update(change)
    rewrite(config, spec)
    with pytest.raises(StateError):
        activation.activate(config)
    assert not launches


def test_unprotected_config_not_fixed_or_read_as_trusted(setup):
    config, _, _, calls, launches = setup
    config.chmod(0o644)
    with pytest.raises(StateError, match="owner-only"):
        activation.activate(config)
    assert config.stat().st_mode & 0o777 == 0o644
    assert not calls and not launches


def test_runtime_work_private_overlap_refused_before_broker_request(setup):
    config, spec, _, calls, launches = setup
    spec["work"] = spec["code"]
    rewrite(config, spec)
    with pytest.raises(StateError, match="disjoint"):
        activation.activate(config)
    assert not calls and not launches


def test_denied_expired_capability_never_launches(setup, monkeypatch):
    config, _, _, _, launches = setup
    monkeypatch.setattr(activation, "call", lambda *a, **kw: {"ok": False, "error": "Expired"})
    with pytest.raises(StateError, match="identity/intent"):
        activation.activate(config)
    assert not launches


def test_grant_replaced_during_authentication_refused(setup, monkeypatch):
    config, _, capfile, _, launches = setup
    original = activation.call
    def replaced(*args, **kwargs):
        response = original(*args, **kwargs)
        capfile.write_text("y" * 43)
        return response
    monkeypatch.setattr(activation, "call", replaced)
    with pytest.raises(StateError, match="changed"):
        activation.activate(config)
    assert not launches


def test_activation_not_exposed_to_mcp_and_cli_preserves_child_failure(monkeypatch, capsys):
    from mgwiki_editor.broker import COMMANDS

    assert "activate" not in COMMANDS
    monkeypatch.setattr(activation, "activate", lambda *a, **kw: {
        "returncode": 7, "status": "isolated_process_exited"})
    assert control.main(["activate", "--config", "fake-private-config"]) == 1
    assert json.loads(capsys.readouterr().out)["returncode"] == 7
