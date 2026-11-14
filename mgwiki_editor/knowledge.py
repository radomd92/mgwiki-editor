"""Durable, reviewed translation tips; job capture first, explicit promotion later."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .artifacts import evidence_path, write_new
from .core import GuardError, digest, json_bytes, now

STATUSES = {"candidate", "reviewed", "rejected"}
SCOPES = {"general", "article"}
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,80}$")
REQUIRED_TEXT = ("id", "domain", "source_language", "target_language", "problem", "guidance")


def _text(entry: dict[str, Any], key: str) -> str:
    value = entry.get(key)
    if not isinstance(value, str) or not value.strip() or len(value) > 4_000:
        raise GuardError(f"Translation-memory field needs concise text: {key}")
    return value.strip()


def validate_entry(entry: Any) -> dict[str, Any]:
    """Validate one reusable tip without treating the shared store as policy."""
    if not isinstance(entry, dict):
        raise GuardError("Translation-memory entry must be an object.")
    values = {key: _text(entry, key) for key in REQUIRED_TEXT}
    if not ID_PATTERN.fullmatch(values["id"]):
        raise GuardError("Translation-memory ID must be filename-safe.")
    if entry.get("status") not in STATUSES:
        raise GuardError("Translation-memory status must be candidate/reviewed/rejected.")
    if entry.get("scope") not in SCOPES:
        raise GuardError("Translation-memory scope must be general/article.")
    evidence = entry.get("evidence", [])
    if not isinstance(evidence, list) or any(not isinstance(item, str) for item in evidence):
        raise GuardError("Translation-memory evidence must be a list of paths or URLs.")
    sections = entry.get("source_sections", [])
    if not isinstance(sections, list) or any(not isinstance(item, str) for item in sections):
        raise GuardError("Translation-memory source_sections must be a list of strings.")
    return {
        **entry,
        **values,
        "evidence": [item.strip() for item in evidence if item.strip()],
        "source_sections": [item.strip() for item in sections if item.strip()],
    }


def read_memory(job: Path, memory: Path) -> list[dict[str, Any]]:
    """Read one job-local memo; never accept a path outside the job."""
    job = job.resolve()
    memory = memory.resolve()
    if not memory.is_relative_to(job) or not memory.is_file():
        raise GuardError("Translation memory must be a file inside the job.")
    raw = memory.read_bytes()
    data = json.loads(raw.decode("utf-8"))
    if isinstance(data, dict):
        data = data.get("entries")
    if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
        raise GuardError("Translation memory must be a list or an entries wrapper.")
    entries = [validate_entry(row) for row in data]
    identifiers = [entry["id"] for entry in entries]
    if len(identifiers) != len(set(identifiers)):
        raise GuardError("Translation-memory IDs must be unique in one job.")
    return entries


def _evidence_ok(job: Path, item: str) -> bool:
    if re.match(r"^https?://", item):
        return True
    base = item.split("#", 1)[0]
    if not base:
        return False
    try:
        evidence_path(job, base)
    except GuardError:
        return False
    return True


def promote_memory(
    job: Path,
    memory: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Promote reviewed general tips only; never overwrite or edit article content."""
    job = job.resolve()
    entries = read_memory(job, memory)
    eligible = [
        entry for entry in entries if entry["status"] == "reviewed" and entry["scope"] == "general"
    ]
    skipped = [
        {"id": entry["id"], "reason": "not reviewed general guidance"}
        for entry in entries
        if entry["status"] != "reviewed" or entry["scope"] != "general"
    ]
    missing = [
        {"id": entry["id"], "evidence": item}
        for entry in eligible
        for item in entry["evidence"]
        if not _evidence_ok(job, item)
    ]
    if missing:
        raise GuardError("Translation-memory evidence is missing or escapes the job.")
    if not eligible:
        return {
            "schema": 1,
            "status": "nothing_to_promote",
            "job": str(job),
            "memory_sha256": digest(memory.read_bytes()),
            "promoted": [],
            "skipped": skipped,
        }
    output_dir = output_dir.resolve()
    outputs = {}
    for entry in eligible:
        path = output_dir / f"{entry['id']}.json"
        outputs[path] = json_bytes(
            {
                **entry,
                "source_job": job.name,
                "source_memory_sha256": digest(memory.read_bytes()),
                "promoted_at": now(),
            }
        )
    write_new(outputs)
    return {
        "schema": 1,
        "status": "promoted",
        "job": str(job),
        "memory_sha256": digest(memory.read_bytes()),
        "promoted": [path.stem for path in outputs],
        "skipped": skipped,
        "limits": "Advisory reviewed tips only. Not policy, dictionary evidence, source "
        "verification, or publication approval. Article-specific drafts are not copied.",
    }


def knowledge_index(
    root: Path,
    *,
    domain: str | None = None,
    language: str | None = None,
    query: str | None = None,
) -> dict[str, Any]:
    """List compact shared tips; exact filters and substring search only."""
    entries, errors = [], []
    if not root.is_dir():
        raise GuardError("Translation-memory directory is missing.")
    for path in sorted(root.glob("*.json")):
        try:
            entry = validate_entry(json.loads(path.read_text(encoding="utf-8")))
        except (GuardError, json.JSONDecodeError) as exc:
            errors.append({"file": path.name, "error": str(exc)})
            continue
        if domain and entry["domain"] != domain:
            continue
        if language and language not in {entry["source_language"], entry["target_language"]}:
            continue
        haystack = " ".join(
            [entry["domain"], entry["problem"], entry["guidance"], entry.get("scope", "")]
        ).casefold()
        if query and query.casefold() not in haystack:
            continue
        entries.append(
            {
                "id": entry["id"],
                "domain": entry["domain"],
                "source_language": entry["source_language"],
                "target_language": entry["target_language"],
                "scope": entry.get("scope"),
                "problem": entry["problem"],
                "guidance": entry["guidance"],
                "source_job": entry.get("source_job"),
                "promoted_at": entry.get("promoted_at"),
            }
        )
    return {
        "schema": 1,
        "status": "advisory_only",
        "root": str(root),
        "match_count": len(entries),
        "entries": entries,
        "invalid_entries": errors,
        "limits": "Reviewed tips are reminders, not policy or verified facts. Confirm "
        "language, domain and evidence before reuse; never copy article prose.",
    }
