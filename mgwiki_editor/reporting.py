"""Small model-facing views; complete reports remain immutable local evidence."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .core import digest


def report_summary(command: str, result: dict[str, Any], output: Path) -> dict[str, Any]:
    """Describe a persisted result without replaying prose, records, or evidence maps."""
    raw = output.read_bytes()
    signals = {
        key: value for key, value in result.items()
        if isinstance(value, (bool, int, float))
        or key in {"status", "decision", "outcome"} and isinstance(value, str)
    }
    counts = {key: len(value) for key, value in result.items()
              if isinstance(value, (list, dict))}
    return {
        "schema": 1, "view": "summary_only", "command": command,
        "artifact": {"path": str(output), "sha256": digest(raw), "bytes": len(raw)},
        "signals": signals, "counts": counts,
        "limits": "Full result saved, not editorial approval. Read relevant report details/raw "
                  "evidence before decisions; counts do not establish complete review.",
    }
