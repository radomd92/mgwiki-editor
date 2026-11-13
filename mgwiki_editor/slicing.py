"""Bounded local JSON slices; large evidence never enters model context whole."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .artifacts import read_evidence
from .core import GuardError


def _resolve_array(data: Any, key: str | None) -> tuple[str, list[Any]]:
    """Address one array exactly; never guess a key or copy the whole document."""
    if not key:
        if isinstance(data, list):
            return "", data
        raise GuardError("JSON root is not an array; pass --key.")
    current = data
    walked: list[str] = []
    for part in key.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            raise GuardError(f"JSON key path not found: {key}")
        walked.append(part)
    if not isinstance(current, list):
        raise GuardError("JSON key path does not address an array.")
    return ".".join(walked), current


def json_slice(
    job: Path,
    filename: str,
    *,
    key: str | None = None,
    offset: int = 0,
    limit: int = 20,
    fields: list[str] | None = None,
) -> dict[str, Any]:
    """Return one bounded page of a job-relative JSON array, pinning the source hash."""
    if type(offset) is not int or offset < 0:
        raise GuardError("JSON slice needs offset >= 0.")
    if type(limit) is not int or not 1 <= limit <= 100:
        raise GuardError("JSON slice needs limit between 1 and 100.")
    if fields is not None and any(not isinstance(name, str) or not name for name in fields):
        raise GuardError("JSON slice fields must be nonempty names.")
    pinned = read_evidence(job, filename)
    address, items = _resolve_array(pinned.data, key)
    selected = items[offset : offset + limit]
    projected = []
    for item in selected:
        if fields and isinstance(item, dict):
            projected.append({name: item[name] for name in fields if name in item})
        else:
            projected.append(item)
    end = offset + len(projected)
    size = (Path(job).resolve() / pinned.name).stat().st_size
    omitted = sorted(
        {name for item in selected if isinstance(item, dict) for name in item} - set(fields or ())
    )
    return {
        "schema": 1,
        "view": "bounded_slice",
        "source": {"path": pinned.name, "sha256": pinned.sha256, "bytes": size},
        "key": address,
        "total_items": len(items),
        "offset": offset,
        "next_offset": end if end < len(items) else None,
        "items": projected,
        "selected_fields": sorted(set(fields)) if fields else [],
        "omitted_fields": omitted,
        "limits": "Bounded slice of one pinned source; not validation, review, or approval. "
        "Read the relevant raw evidence before decisions. Source file unchanged; "
        "no content inferred, merged, or completed.",
    }
