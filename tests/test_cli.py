"""CLI contract tests using offline gateway stubs only."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from mgwiki_editor import cli
from mgwiki_editor.core import GuardError


def test_cli_validate(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Report lint success/failure with matching exit status."""
    draft = tmp_path / "draft.wiki"
    draft.write_text("'''Rano''' dia ranoka.\n", encoding="utf-8")
    assert cli.main(["validate", "--draft", str(draft)]) == 0
    assert json.loads(capsys.readouterr().out)["valid"] is True
    draft.write_text("**Markdown**", encoding="utf-8")
    assert cli.main(["validate", "--draft", str(draft)]) == 1
    assert json.loads(capsys.readouterr().out)["errors"]


def test_cli_read_and_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
) -> None:
    """Persist JSON evidence without overwriting existing evidence."""
    calls = []

    class Stub:
        """Capture the exact read request."""

        def snapshot(self, *args, **kwargs):
            calls.append((args, kwargs))
            return {"text": "Rano", "revision_id": 1}

    monkeypatch.setattr(cli, "Wiki", Stub)
    output = tmp_path / "read.json"
    arguments = ["read", "--lang", "mg", "--title", "Mpikambana:Bot-Jagwar/Rano",
                 "--sandbox", "--output", str(output)]
    assert cli.main(arguments) == 0
    assert calls == [(("mg", "Mpikambana:Bot-Jagwar/Rano"), {"sandbox": True})]
    assert json.loads(output.read_text())["revision_id"] == 1
    assert cli.main(arguments) == 1
    assert "Output exists" in capsys.readouterr().err


def test_cli_lookup(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    """Dispatch only a read-only dictionary request."""
    monkeypatch.setattr(cli, "lookup", lambda edition, word: {"edition": edition, "word": word})
    assert cli.main(["lookup", "--edition", "mg", "--word", "rano"]) == 0
    assert json.loads(capsys.readouterr().out) == {"edition": "mg", "word": "rano"}


@pytest.mark.parametrize("refresh", [False, True])
def test_cli_country_cache(
    refresh: bool, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
) -> None:
    """Refresh is explicit, while ordinary reads request only local cached data."""
    calls = []

    def countries(wiki, *, refresh):
        calls.append(refresh)
        return {"titles": ["Etazonia"]}

    monkeypatch.setattr(cli, "country_names", countries)
    arguments = ["countries", "--refresh"] if refresh else ["countries"]
    assert cli.main(arguments) == 0
    assert calls == [refresh]
    assert json.loads(capsys.readouterr().out)["titles"] == ["Etazonia"]


def test_cli_init(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    """Return a compact draft-only initialization result, not an apparent save."""
    monkeypatch.setattr(cli, "initialize", lambda *args: {
        "destination": "Mpikambana:Bot-Jagwar/Rano", "source": {"url": "permanent-source"},
    })
    assert cli.main(["init", "--source-lang", "en", "--source-title", "Water",
                     "--article-title", "Rano", "--job", "runs/test"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "draft_only"


@pytest.mark.parametrize("command", ["prepare", "publish"])
def test_cli_proposal_dispatch(
    command: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
) -> None:
    """Publish forwards the full approval argument rather than guessing approval."""
    monkeypatch.setattr(cli, "prepare", lambda *args: {"digest": "abc"})
    monkeypatch.setattr(cli, "publish", lambda wiki, job, approval: {"digest": approval})
    args = [command, "--job", "runs/test"]
    if command == "publish":
        args.extend(["--approve", "abc"])
    assert cli.main(args) == 0
    assert json.loads(capsys.readouterr().out)["digest"] == "abc"


def test_cli_reports_remote_failures(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
) -> None:
    """Do not report success after failed guards or uncertain live operations."""
    def fail(*args):
        raise GuardError("No approval")

    monkeypatch.setattr(cli, "publish", fail)
    assert cli.main(["publish", "--job", "runs/test", "--approve", "x"]) == 1
    assert json.loads(capsys.readouterr().err)["message"] == "No approval"


def test_cli_defaults_to_autonomous_publish(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
) -> None:
    """Autonomous publication requires no user approval argument or prompt."""
    calls = []

    def publish(wiki, job, approval):
        calls.append((job, approval))
        return {"mode": "autonomous"}

    monkeypatch.setattr(cli, "publish", publish)
    assert cli.main(["publish", "--job", "runs/test"]) == 0
    assert calls == [(Path("runs/test"), None)]
    assert json.loads(capsys.readouterr().out)["mode"] == "autonomous"


def test_cli_unicode_output_on_latin1_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    """A completed Unicode result must not become a spurious console encoding failure."""
    result = {"titles": ["Jibotỳ"], "definition": "A singer’s voice — soprano"}
    monkeypatch.setattr(cli, "country_names", lambda *args, **kwargs: result)
    buffer = io.BytesIO()
    stream = io.TextIOWrapper(buffer, encoding="latin-1")
    with monkeypatch.context() as context:
        context.setattr(cli.sys, "stdout", stream)
        status = cli.main(["countries"])
        stream.flush()
    assert status == 0
    assert json.loads(buffer.getvalue()) == result


def test_cli_unicode_errors_on_latin1_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    """Error reporting must also preserve non-Latin-1 characters without raising."""
    def fail(*args, **kwargs):
        raise GuardError("Jibotỳ — unavailable")

    monkeypatch.setattr(cli, "country_names", fail)
    buffer = io.BytesIO()
    stream = io.TextIOWrapper(buffer, encoding="latin-1")
    with monkeypatch.context() as context:
        context.setattr(cli.sys, "stderr", stream)
        status = cli.main(["countries"])
        stream.flush()
    assert status == 1
    assert json.loads(buffer.getvalue())["message"] == "Jibotỳ — unavailable"


def test_configured_broker_routes_publish_without_direct_wiki_or_fallback(monkeypatch, capsys):
    from mgwiki_editor import control

    monkeypatch.setenv("MGWIKI_BROKER_SOCKET", "/broker/socket")
    monkeypatch.setenv("MGWIKI_CAPABILITY_FILE", "/broker/cap")
    monkeypatch.setattr(cli, "Wiki", lambda: pytest.fail("Broker profile bypassed"))
    calls = []
    def client(socket, capfile, command, args):
        calls.append((command, args))
        return ({"ok": True, "result": {"run": "water"}} if command == "status" else
                {"ok": False, "decision": {"outcome": "DENY"}})
    monkeypatch.setattr(control, "client", client)
    assert cli.main(["publish", "--job", "runs/water"]) == 1
    assert [command for command, _ in calls] == ["status", "publish"]
    assert json.loads(capsys.readouterr().out)["decision"]["outcome"] == "DENY"


def test_incomplete_broker_settings_fail_closed_without_wiki(monkeypatch, capsys):
    monkeypatch.setenv("MGWIKI_BROKER_SOCKET", "/broker/socket")
    monkeypatch.delenv("MGWIKI_CAPABILITY_FILE", raising=False)
    monkeypatch.setattr(cli, "Wiki", lambda: pytest.fail("Incomplete broker config bypassed"))
    assert cli.main(["read", "--lang", "en", "--title", "Water"]) == 1
    assert "no fallback" in capsys.readouterr().err


def test_broker_job_identity_mismatch_blocks_before_publish(monkeypatch, capsys):
    from mgwiki_editor import control

    monkeypatch.setenv("MGWIKI_BROKER_SOCKET", "/broker/socket")
    monkeypatch.setenv("MGWIKI_CAPABILITY_FILE", "/broker/cap")
    monkeypatch.setattr(control, "client", lambda *args: {"ok": True, "result": {"run": "water"}})
    assert cli.main(["publish", "--job", "runs/other"]) == 1
    assert "does not match" in capsys.readouterr().err


@pytest.mark.parametrize("command", ["citation-audit", "metadata-audit"])
def test_new_offline_checks_route_through_configured_broker(monkeypatch, capsys, command):
    from mgwiki_editor import control

    monkeypatch.setenv("MGWIKI_BROKER_SOCKET", "/broker/socket")
    monkeypatch.setenv("MGWIKI_CAPABILITY_FILE", "/broker/cap")
    monkeypatch.setattr(cli, "Wiki", lambda: pytest.fail("Configured broker bypassed"))
    calls = []
    def client(socket, capfile, action, arguments):
        calls.append((action, arguments))
        return {"ok": True, "result": {"run": "water"}}
    monkeypatch.setattr(control, "client", client)
    assert cli.main([command, "--job", "runs/water"]) == 0
    assert calls[0] == ("status", {})
    assert calls[1][0] == command


def test_license_report_routes_through_configured_broker_without_direct_read(monkeypatch):
    from mgwiki_editor import control

    monkeypatch.setenv("MGWIKI_BROKER_SOCKET", "/broker/socket")
    monkeypatch.setenv("MGWIKI_CAPABILITY_FILE", "/broker/cap")
    monkeypatch.setattr(cli, "license_report", lambda *a: pytest.fail("Broker bypassed"))
    calls = []
    def client(socket, capfile, action, arguments):
        calls.append((action, arguments))
        return {"ok": True, "result": {"run": "water"}}
    monkeypatch.setattr(control, "client", client)
    assert cli.main(["license-report", "--job", "runs/water", "--evidence", "evidence/file.json",
                     "--filename", "Exact.svg"]) == 0
    assert calls[-1] == ("license-report", {"evidence": "evidence/file.json",
                                           "filename": "Exact.svg"})


def test_license_capture_respects_explicit_broker_without_direct_fallback(monkeypatch, capsys):
    from mgwiki_editor import control

    monkeypatch.setenv("MGWIKI_BROKER_SOCKET", "/broker/socket")
    monkeypatch.setenv("MGWIKI_CAPABILITY_FILE", "/broker/cap")
    monkeypatch.setattr(cli, "Wiki", lambda: pytest.fail("Configured broker bypassed"))
    calls = []
    def client(socket, capfile, action, arguments):
        calls.append((action, arguments))
        return {"ok": False, "decision": {"outcome": "DENY"}}

    monkeypatch.setattr(control, "client", client)
    assert cli.main(["license-evidence", "--filename", "Exact.svg"]) == 1
    assert calls == [("license-evidence", {"filename": "Exact.svg"})]
    assert json.loads(capsys.readouterr().out)["decision"]["outcome"] == "DENY"
