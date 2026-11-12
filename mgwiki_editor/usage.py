"""Offline OpenCode session-counter snapshots; no server or provider calls."""

from __future__ import annotations

from typing import Any

from .core import GuardError


def session_usage(data: Any, *, sessions: list[str] | None = None) -> dict[str, Any]:
    """Sum unique root sessions or explicit IDs; never silently mix parents/children."""
    if isinstance(data, dict):
        data = data.get("data")
    if not isinstance(data, list):
        raise GuardError("Usage input must be a session list or API data-list response.")
    selected = set(sessions or [])
    seen, rows = {}, []
    for row in data:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            raise GuardError("Usage sessions need exact IDs.")
        if row.get("parentID") is not None and not isinstance(row["parentID"], str):
            raise GuardError("Usage parentID must be a session ID or null.")
        ident = row["id"]
        if ident in seen:
            if row != seen[ident]:
                raise GuardError("Conflicting usage snapshots for the same session.")
            continue
        seen[ident] = row
        if (selected and ident not in selected) or (not selected and row.get("parentID")):
            continue
        tokens = row.get("tokens")
        if not isinstance(tokens, dict) or not isinstance(tokens.get("cache"), dict):
            raise GuardError("Usage snapshot lacks token/cache counters.")
        counters = {key: tokens.get(key) for key in ("input", "output", "reasoning")}
        counters.update(cache_read=tokens["cache"].get("read"),
                        cache_write=tokens["cache"].get("write"))
        if any(type(value) is not int or value < 0 for value in counters.values()):
            raise GuardError("Usage counters must be nonnegative integers.")
        rows.append({"id": ident, "parentID": row.get("parentID"), **counters})
    if selected - {row["id"] for row in rows}:
        raise GuardError("Requested session missing from usage snapshot.")
    included = {row["id"] for row in rows}
    for row in rows:
        ancestors = {row["id"]}
        parent = row["parentID"]
        while parent is not None:
            if parent in ancestors:
                raise GuardError("Cyclic usage session ancestry.")
            if parent in included:
                raise GuardError("Do not aggregate ancestor/child usage; semantics unverified.")
            ancestors.add(parent)
            parent = seen.get(parent, {}).get("parentID")
    keys = ("input", "output", "reasoning", "cache_read", "cache_write")
    totals = {key: sum(row[key] for row in rows) for key in keys}
    denominator = totals["input"] + totals["output"] + totals["cache_read"]
    return {
        "schema": 1, "view": "session_counter_snapshot", "sessions": rows, "totals": totals,
        "cache_read_fraction": totals["cache_read"] / denominator if denominator else None,
        "limits": "Only supplied snapshots/selected sessions; not complete project usage or an "
                  "invoice. Reasoning separate, not added to output. Parent/child aggregation "
                  "semantics unverified. No provider cost inferred. Compare same scope/model "
                  "before/after; never skip editorial/save guards to meet a token budget.",
    }
