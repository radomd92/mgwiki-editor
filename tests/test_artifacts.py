"""Shared local artifact helpers reject escaped paths and never overwrite outputs."""

from pathlib import Path

import pytest

from mgwiki_editor.artifacts import evidence_path, read_evidence, read_text, write_new
from mgwiki_editor.core import GuardError, digest


def test_pinned_json_and_text_preserve_exact_bytes(tmp_path: Path) -> None:
    path = tmp_path / "evidence.json"
    raw = b'{"a": 1}\r\n'
    path.write_bytes(raw)
    pinned = read_evidence(tmp_path, "evidence.json")
    assert pinned.name == "evidence.json"
    assert pinned.sha256 == digest(raw)
    assert pinned.data == {"a": 1}
    assert read_text(path) == raw.decode()


def test_evidence_symlink_cannot_escape_job(tmp_path: Path) -> None:
    job = tmp_path / "job"
    job.mkdir()
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    (job / "escape.json").symlink_to(outside)
    with pytest.raises(GuardError, match="unsafe"):
        evidence_path(job, "escape.json")


def test_exclusive_writer_preflights_all_files_and_dangling_symlinks(tmp_path: Path) -> None:
    first, second = tmp_path / "first", tmp_path / "second"
    second.symlink_to(tmp_path / "missing")
    with pytest.raises(GuardError, match="exists"):
        write_new({first: b"new", second: b"replacement"})
    assert not first.exists()
    assert second.is_symlink()
    assert not (tmp_path / "missing").exists()


def test_writer_checks_parent_collision_before_any_write(tmp_path: Path) -> None:
    parent = tmp_path / "not-a-directory"
    parent.write_text("Keep.", encoding="utf-8")
    first = tmp_path / "first"
    with pytest.raises(GuardError, match="parent"):
        write_new({first: b"new", parent / "second": b"new"})
    assert not first.exists()
    assert parent.read_text() == "Keep."
