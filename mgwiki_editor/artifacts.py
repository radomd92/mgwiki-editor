"""Shared local evidence paths and exclusive writes; imports never access network."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .core import GuardError, digest


def read_text(path: Path) -> str:
    """Preserve CRLF and final-newline evidence exactly."""
    return path.read_bytes().decode("utf-8")


def evidence_path(job: Path, name: str) -> Path:
    """Resolve an existing job-relative file, rejecting traversal and escaped symlinks."""
    job = job.resolve()
    if not isinstance(name, str) or Path(name).is_absolute():
        raise GuardError("Evidence paths must be job-relative.")
    path = (job / name).resolve()
    if not path.is_relative_to(job) or not path.is_file():
        raise GuardError(f"Missing or unsafe job evidence: {name}")
    return path


@dataclass(frozen=True)
class JSONEvidence:
    """Parsed data and digest from the same exact file read."""

    name: str
    sha256: str
    data: Any


def read_evidence(job: Path, name: str) -> JSONEvidence:
    """Pin JSON without inferring authority or following any URLs it contains."""
    path = evidence_path(job, name)
    raw = path.read_bytes()
    return JSONEvidence(path.relative_to(job.resolve()).as_posix(), digest(raw), json.loads(raw))


def write_new(outputs: dict[Path, bytes]) -> None:
    """Preflight destinations, then create exclusively; never replace existing artifacts."""
    for path in outputs:
        if path.exists() or path.is_symlink():
            raise GuardError(f"Output exists; preserve it: {path}")
        if any(parent.exists() and not parent.is_dir() for parent in path.parents):
            raise GuardError(f"Output parent is not a directory: {path}")
    for path, data in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(data)
