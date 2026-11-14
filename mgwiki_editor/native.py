"""Optional native accelerator for large local artifacts; never a remote client."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from .core import GuardError

BINARY = Path(__file__).resolve().parents[1] / "bin" / "mgwiki-scan"


def _local_path(value: str | Path) -> Path:
    path = Path(value).resolve()
    root = Path.cwd().resolve()
    if not path.is_relative_to(root):
        raise GuardError("Native scanner paths must stay inside the working directory.")
    return path


def _run(arguments: list[str], *, timeout: int = 120) -> dict[str, Any]:
    if not BINARY.is_file():
        raise GuardError("Native scanner is not built; run `make native`.")
    try:
        completed = subprocess.run(
            [str(BINARY), *arguments],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GuardError(f"Native scanner failed: {exc}") from exc
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise GuardError(f"Native scanner failed: {detail[:500]}")
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise GuardError("Native scanner returned malformed JSON.") from exc
    if not isinstance(result, dict):
        raise GuardError("Native scanner returned an unexpected result.")
    return result


def inventory(path: str | Path) -> dict[str, Any]:
    """Raw regex inventory; Python coverage/validate remain authoritative."""
    file = _local_path(path)
    if not file.is_file():
        raise GuardError("Native inventory needs an existing file.")
    return _run(["inventory", str(file)])


def compare(source: str | Path, draft: str | Path) -> dict[str, Any]:
    """Exact raw set comparison; not editorial coverage approval."""
    source_path = _local_path(source)
    draft_path = _local_path(draft)
    if not source_path.is_file() or not draft_path.is_file():
        raise GuardError("Native compare needs two existing files.")
    return _run(["compare", str(source_path), str(draft_path)])


def summary(path: str | Path) -> dict[str, Any]:
    """Hash, size and duplicate scan for one directory."""
    root = _local_path(path)
    if not root.is_dir():
        raise GuardError("Native summary needs an existing directory.")
    return _run(["summary", str(root)])


def search(path: str | Path, query: str, *, max_hits: int = 200) -> dict[str, Any]:
    """Bounded case-insensitive literal search over local text artifacts."""
    root = _local_path(path)
    if not root.is_dir():
        raise GuardError("Native search needs an existing directory.")
    if not 1 <= max_hits <= 5000:
        raise GuardError("Native search max-hits must be between 1 and 5000.")
    return _run(["search", "-max-hits", str(max_hits), str(root), query])
