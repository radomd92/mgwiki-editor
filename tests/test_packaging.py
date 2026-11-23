"""Offline packaging metadata checks for current setuptools compatibility."""

import tomllib
from pathlib import Path


def test_spdx_license_does_not_mix_with_legacy_license_classifiers() -> None:
    path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    project = tomllib.loads(path.read_text(encoding="utf-8"))["project"]

    assert project["license"] == "Apache-2.0"
    assert project["license-files"] == ["LICENSE", "NOTICE"]
    assert not any(value.startswith("License ::") for value in project["classifiers"])
