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
