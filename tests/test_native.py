"""Optional Go accelerator integration; skips when the native binary is not built."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mgwiki_editor import cli, native
from mgwiki_editor.core import GuardError

pytestmark = pytest.mark.skipif(
    not native.BINARY.is_file(), reason="run `make native` to build bin/mgwiki-scan"
)


@pytest.fixture
def job(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    directory = tmp_path / "job"
    directory.mkdir()
    (directory / "source.wiki").write_text(
        "[[A]] [[File:One.jpg]] <ref name=keep>x</ref> https://a.example\n",
        encoding="utf-8",
    )
    (directory / "draft.wiki").write_text(
        "[[B]] [[File:Two.jpg]] <ref name=extra>y</ref> https://b.example\n",
        encoding="utf-8",
    )
    return directory


def test_inventory_and_compare(job: Path) -> None:
    inventory = native.inventory(job / "source.wiki")
    assert inventory["files"] == {"One.jpg": 1}
    compared = native.compare(job / "source.wiki", job / "draft.wiki")
    assert compared["missing_files"] == {"One.jpg": 1}
    assert compared["extra_files"] == {"Two.jpg": 1}
    assert compared["missing_link_targets"] == ["A"]


def test_summary_and_search(job: Path, capsys: pytest.CaptureFixture) -> None:
    (job / "same-a.json").write_text("same", encoding="utf-8")
    (job / "same-b.json").write_text("same", encoding="utf-8")
    summary = native.summary(job)
    assert summary["file_count"] == 4
    assert len(summary["duplicate_groups"]) == 1
    found = native.search(job, "A]]", max_hits=1)
    assert found["total_matches"] == 1
    assert found["hits"][0]["path"] == "source.wiki"

    assert cli.main(["native-summary", "--job", str(job)]) == 0
    assert json.loads(capsys.readouterr().out)["file_count"] == 4


def test_paths_outside_working_directory_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(GuardError, match="working directory"):
        native.summary(tmp_path.parent)


def test_missing_binary_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(native, "BINARY", Path("/nonexistent/mgwiki-scan"))
    with pytest.raises(GuardError, match="make native"):
        native.summary(".")
