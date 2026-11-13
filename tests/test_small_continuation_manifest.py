"""Offline retained-recovery validation; never calls a remote service."""

import importlib.util
import json
from pathlib import Path

import pytest

from mgwiki_editor.core import GuardError

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "runs/biology-health-20261110/small-intestine/continue_research.py"
)


@pytest.fixture
def helper():
    spec = importlib.util.spec_from_file_location("small_continuation", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture_manifest(root, helper):
    old = {
        "edition": "mg",
        "word": "test",
        "url": "http://localhost/wiktionary-pages/mg/test",
        "status": "failed",
    }
    new = {**old, "status": "missing"}
    for name, value in [("old.json", old), ("new.json", new)]:
        (root / name).write_text(json.dumps(value))
    row = {
        "edition": "mg",
        "word": "test",
        "url": old["url"],
        "original_file": "old.json",
        "accepted_file": "new.json",
        "original_sha256": helper.sha((root / "old.json").read_bytes()),
        "accepted_sha256": helper.sha((root / "new.json").read_bytes()),
        "status": "missing",
    }
    manifest = {"plan_sha256": "plan", "source_sha256": "source", "accepted_replies": [row]}
    (root / "selected.json").write_text(json.dumps(manifest))
    return manifest


def test_explicit_manifest_and_original_retained(tmp_path, helper):
    fixture_manifest(tmp_path, helper)
    old = (tmp_path / "old.json").read_bytes()
    assert helper.accepted_recoveries(tmp_path, "plan", "source", "selected.json") == {
        ("mg", "test"): "new.json"
    }
    assert (tmp_path / "old.json").read_bytes() == old


@pytest.mark.parametrize("defect", ["plan", "source", "identity", "hash", "duplicate"])
def test_manifest_fail_closed(tmp_path, helper, defect):
    manifest = fixture_manifest(tmp_path, helper)
    if defect in {"plan", "source"}:
        manifest[defect + "_sha256"] = "changed"
    elif defect == "identity":
        manifest["accepted_replies"][0]["word"] = "other"
    elif defect == "hash":
        (tmp_path / "new.json").write_text("{}")
    else:
        manifest["accepted_replies"] *= 2
    (tmp_path / "selected.json").write_text(json.dumps(manifest))
    with pytest.raises(GuardError):
        helper.accepted_recoveries(tmp_path, "plan", "source", "selected.json")


def test_default_stays_v1_and_path_escape_rejected(tmp_path, helper):
    fixture_manifest(tmp_path, helper)
    with pytest.raises(GuardError):
        helper.accepted_recoveries(tmp_path, "plan", "source")
    with pytest.raises(GuardError):
        helper.accepted_recoveries(tmp_path, "plan", "source", "../selected.json")
