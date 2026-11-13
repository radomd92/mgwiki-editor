"""Turn-reducing offline bundles; same evidence, checks and guards, fewer steps."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .artifacts import evidence_path, write_new
from .citations import citation_audit
from .core import GuardError, digest, json_bytes, lint_wikitext, lookup
from .metadata import metadata_audit
from .terminology import audit_mathematical_terms
from .workflow import coverage_report

MAX_BATCH = 50


def _slug(word: str) -> str:
    """Deterministic safe filename token; never a translation or case merge."""
    return hashlib.sha256(word.encode("utf-8")).hexdigest()[:16]


def lookup_batch(
    edition: str,
    words: list[str],
    job: Path,
    output_dir: Path,
    *,
    lookup_fn=None,
) -> dict[str, Any]:
    """Serial per-word lookups, one tool turn; pending 502 evidence retained."""
    lookup_fn = lookup_fn or lookup
    if edition not in {"en", "mg"}:
        raise GuardError("Dictionary edition must be en or mg.")
    if len(words) > MAX_BATCH:
        raise GuardError(f"Batch exceeds {MAX_BATCH} words; split it.")
    if not words or any(not isinstance(word, str) or not word.strip() for word in words):
        raise GuardError("Batch needs nonempty words.")
    identities = [(edition, word.strip()) for word in words]
    if len(set(identities)) != len(identities):
        raise GuardError("Batch words must be distinct; never merge case/accents here.")
    job = job.resolve()
    output_dir = output_dir.resolve()
    if not output_dir.is_relative_to(job) or output_dir == job:
        raise GuardError("Batch output must be a new directory inside the job.")
    if output_dir.exists() or output_dir.is_symlink():
        raise GuardError("Batch output exists; preserve it.")
    results, files = [], {}
    for index, (batch_edition, word) in enumerate(identities):
        name = f"{index:03d}-{batch_edition}-{_slug(word)}.json"
        path = output_dir / name
        reply = lookup_fn(batch_edition, word)
        raw = json_bytes(reply)
        files[path] = raw
        results.append(
            {
                "word": word,
                "file": path.relative_to(job).as_posix(),
                "sha256": digest(raw),
                "status": reply.get("status"),
                "retrieved_at": reply.get("retrieved_at"),
                "url": reply.get("url"),
            }
        )
    write_new(files)
    statuses: dict[str, int] = {}
    for result in results:
        statuses[result["status"] or "unknown"] = statuses.get(result["status"] or "unknown", 0) + 1
    return {
        "schema": 1,
        "status": "evidence_only",
        "edition": edition,
        "output_dir": output_dir.relative_to(job).as_posix(),
        "results": results,
        "status_counts": statuses,
        "limits": "Pending/exhausted 502 replies are retained evidence, not missing words; "
        "resume due lookups later per policy, never in a sleep/poll loop. Statuses "
        "do not verify senses. One HTTP request per word through the shared gate.",
    }


def offline_audit(
    job: Path,
    draft: str,
    output: Path,
    *,
    evidence: list[str] | None = None,
    vocab_audit: bool = False,
) -> dict[str, Any]:
    """Run deterministic local checks in one turn; each full report written separately."""
    job = job.resolve()
    output = output.resolve()
    if not output.is_relative_to(job) or output == job:
        raise GuardError("Audit manifest must be a new file inside the job.")
    if output.exists() or output.is_symlink():
        raise GuardError("Audit manifest exists; preserve it.")
    stem = output.with_suffix("")
    errors = lint_wikitext(_draft_text(job, draft))
    planned: dict[str, Any] = {
        "validate": lambda: {"valid": not errors, "errors": errors},
        "coverage": lambda: coverage_report(job, _inside(job, draft)),
        "citation-audit": lambda: citation_audit(job, draft),
        "metadata-audit": lambda: metadata_audit(job, evidence or [], draft),
    }
    if vocab_audit:
        planned["vocab-audit"] = lambda: audit_mathematical_terms(_inside(job, draft))
    outputs, checks = {}, []
    for name, run in planned.items():
        path = output.parent / f"{stem.name}-{name}.json"
        if path.exists() or path.is_symlink():
            raise GuardError(f"Audit output exists; preserve it: {path}")
        try:
            result = run()
            raw = json_bytes(result)
            outputs[path] = raw
            checks.append(
                {
                    "check": name,
                    "output": path.relative_to(job).as_posix(),
                    "sha256": digest(raw),
                    "bytes": len(raw),
                    "status": "ok",
                }
            )
        except Exception as exc:  # noqa: BLE001 - one failed check must not hide the others
            checks.append(
                {"check": name, "status": "error", "error": type(exc).__name__, "message": str(exc)}
            )
    if outputs:
        write_new(outputs)
    failed = [row["check"] for row in checks if row["status"] == "error"]
    return {
        "schema": 1,
        "status": "reports_only",
        "draft": draft,
        "checks": checks,
        "failed_checks": failed,
        "limits": "Deterministic local reports only; not editorial review or approval. Read "
        "each report before decisions. Errors are retained, never suppressed.",
    }


def _inside(job: Path, name: str) -> Path:
    return evidence_path(job, name)


def _draft_text(job: Path, name: str) -> str:
    return _inside(job, name).read_bytes().decode("utf-8")


def evidence_pin(job: Path, artifacts: list[str], output: Path) -> dict[str, Any]:
    """Pin exact artifact digests before targeted edits; replaces ad-hoc pin scripts."""
    job = job.resolve()
    if not artifacts:
        raise GuardError("Pin needs at least one artifact.")
    output = output.resolve()
    if not output.is_relative_to(job) or output == job:
        raise GuardError("Pin output must be a new file inside the job.")
    if output.exists() or output.is_symlink():
        raise GuardError("Pin output exists; preserve it.")
    pinned = {}
    for name in artifacts:
        path = evidence_path(job, name)
        raw = path.read_bytes()
        pinned[name] = {"sha256": digest(raw), "bytes": len(raw)}
    payload = {"schema": 1, "kind": "artifact_pin", "artifacts": pinned}
    write_new({output: json_bytes(payload)})
    return {
        "schema": 1,
        "status": "pinned",
        "pin": output.relative_to(job).as_posix(),
        "artifacts": pinned,
        "limits": "Exact-byte pin only; not editorial review. Verify before adopting "
        "changes; a changed artifact invalidates dependent checks.",
    }


def evidence_verify(job: Path, pin: str) -> dict[str, Any]:
    """Recheck a pin without modifying artifacts; mismatches are reported, never erased."""
    job = job.resolve()
    path = evidence_path(job, pin)
    payload = json.loads(path.read_bytes())
    artifacts = payload.get("artifacts") if isinstance(payload, dict) else None
    if not isinstance(artifacts, dict) or not artifacts:
        raise GuardError("Invalid artifact pin.")
    mismatches, missing = [], []
    for name, expected in artifacts.items():
        if not isinstance(expected, dict) or not isinstance(expected.get("sha256"), str):
            raise GuardError("Invalid pin entry.")
        try:
            actual = digest(evidence_path(job, name).read_bytes())
        except GuardError:
            missing.append(name)
            continue
        if actual != expected["sha256"]:
            mismatches.append({"artifact": name, "expected": expected["sha256"], "actual": actual})
    unchanged = not mismatches and not missing
    return {
        "schema": 1,
        "pin": path.relative_to(job).as_posix(),
        "unchanged": unchanged,
        "mismatches": mismatches,
        "missing": missing,
        "limits": "Verification only; changed artifacts require fresh review/preparation, "
        "never silent acceptance or pin regeneration.",
    }
