"""Reusable local section planning, assembly and coverage; no editorial attestations."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any

import mwparserfromhell as mw

from .artifacts import evidence_path, read_text, write_new
from .core import GuardError, digest, json_bytes, read_json
from .links import adapt_links, load_link_map
from .memos import vocabulary_records
from .wikitext import (
    convert_citations,
    convert_related_hatnotes,
    inventory,
    promote_article_categories,
    reference_inventory,
)


def _editable_job(job: Path) -> None:
    """Local workflow never amends prepared jobs or uncertain save attempts."""
    for name in ("proposal.json", "receipt.json"):
        path = job / name
        if path.exists() or path.is_symlink():
            raise GuardError("Prepared/save-attempt job: use a fresh job, not local reassembly.")


def heading_ranges(source: str, level: int = 2) -> list[dict[str, Any]]:
    """Split at top-level parsed headings; keep lead, appendices and every source byte."""
    if not 1 <= level <= 6:
        raise GuardError("Heading level must be between 1 and 6.")
    boundaries = [(0, "lead")]
    offset = 0
    for node in mw.parse(source).nodes:
        if isinstance(node, mw.nodes.Heading) and node.level <= level:
            if offset == 0:
                boundaries[0] = (0, str(node.title).strip())
            else:
                boundaries.append((offset, str(node.title).strip()))
        offset += len(str(node))
    ranges = []
    for index, (start, heading) in enumerate(boundaries):
        end = boundaries[index + 1][0] if index + 1 < len(boundaries) else len(source)
        # Heading boundaries occur at line starts; an empty source is rejected by caller.
        slug = re.sub(r"[^\w-]+", "-", heading.casefold()).strip("-")[:60] or "section"
        ranges.append({"id": f"{index:02d}-{slug}", "heading": heading,
                       "start": source[:start].count("\n") + 1,
                       "end": source[:end].count("\n") + int(end > 0 and source[end-1] != "\n")})
    return ranges


def group_ranges(source: str, ranges: list[dict[str, Any]], max_bytes: int) -> list[dict[str, Any]]:
    """Merge adjacent short sections into one worker assignment; keep every source byte.

    Fewer, coherent assignments reduce repeated fixed policy context per article.
    The first section's safe ID names the group; merged headings stay in the source
    fragment, so no heading, byte, or line range is dropped or reordered.
    """
    if type(max_bytes) is not int or not 0 <= max_bytes <= 50_000:
        raise GuardError("Group size must be an integer between 0 and 50000 bytes.")
    if max_bytes == 0:
        return ranges
    lines = source.splitlines(keepends=True)
    sizes = [len("".join(lines[row["start"] - 1:row["end"]]).encode("utf-8")) for row in ranges]
    groups: list[dict[str, Any]] = []
    for row, size in zip(ranges, sizes, strict=True):
        previous = groups[-1] if groups else None
        if previous is not None and previous["group_bytes"] + size <= max_bytes:
            previous["end"] = row["end"]
            previous["group_bytes"] += size
            previous["headings"].append(row["heading"])
            previous["merged_ids"].append(row["id"])
            continue
        groups.append({**row, "group_bytes": size,
                       "headings": [row["heading"]], "merged_ids": [row["id"]]})
    return groups


def _ranges(source: str, ranges: Any) -> list[dict[str, Any]]:
    """Require ordered, complete, disjoint coverage; omissions need separate editorial work."""
    if not isinstance(ranges, list) or not ranges:
        raise GuardError("Section ranges must be a nonempty JSON list.")
    count = len(source.splitlines(keepends=True))
    cursor = 1
    seen = set()
    for row in ranges:
        if not isinstance(row, dict):
            raise GuardError("Invalid section range.")
        ident, start, end = (row.get(key) for key in ("id", "start", "end"))
        if (not isinstance(ident, str) or not re.fullmatch(r"[\w-]+", ident)
                or ident in seen or type(start) is not int or type(end) is not int
                or start != cursor or not start <= end <= count):
            raise GuardError("Sections need unique safe IDs and contiguous inclusive line ranges.")
        seen.add(ident)
        cursor = end + 1
    if cursor != count + 1:
        raise GuardError("Section ranges must cover the complete source, including appendices.")
    return ranges


def plan_sections(
    job: Path, *, ranges: Path | None = None, level: int = 2,
    group_max_bytes: int = 0,
) -> dict[str, Any]:
    """Create exclusive worker inputs and portable plan; leave all existing artifacts alone."""
    job = job.resolve()
    _editable_job(job)
    source = read_text(job / "source.wiki")
    if not source.strip():
        raise GuardError("Cannot plan an empty source.")
    if (job / "sections").is_symlink():
        raise GuardError("Section parent must not be a symlink.")
    rows = _ranges(source, read_json(ranges) if ranges else heading_ranges(source, level))
    headings = len(rows)
    rows = group_ranges(source, rows, group_max_bytes)
    lines = source.splitlines(keepends=True)
    plan = []
    outputs = {}
    for row in rows:
        directory = f"sections/{row['id']}"
        if (job / directory).exists() or (job / directory).is_symlink():
            raise GuardError(f"Section directory exists; preserve it: {directory}")
        fragment = "".join(lines[row["start"] - 1:row["end"]]).encode("utf-8")
        outputs[job / directory / "source.wiki"] = fragment
        plan.append({**row, "directory": directory, "source_sha256": digest(fragment),
                     "status": "pending"})
    pinned = {"source.wiki": digest(source.encode("utf-8"))}
    for name in ("job.json", "existing.wiki", "sandbox.wiki"):
        if (job / name).is_file():
            pinned[name] = digest((job / name).read_bytes())
    outputs[job / "section-plan.json"] = json_bytes(plan)
    outputs[job / "section-inputs.json"] = json_bytes({"schema": 1, "artifacts": pinned})
    outputs[job / "source-inventory.json"] = json_bytes(inventory(source))
    write_new(outputs)
    return {"job": str(job), "sections": len(plan), "source_sections": headings,
            "group_max_bytes": group_max_bytes, "status": "planned",
            "editorial_review": "pending", "source_sha256": pinned["source.wiki"]}


def _load_plan(job: Path) -> list[dict[str, Any]]:
    inputs = read_json(job / "section-inputs.json")
    if (not isinstance(inputs, dict) or inputs.get("schema") != 1
            or not isinstance(inputs.get("artifacts"), dict)
            or "source.wiki" not in inputs["artifacts"]):
        raise GuardError("Invalid section input manifest; create a fresh plan.")
    for name, expected in inputs["artifacts"].items():
        if digest(evidence_path(job, name).read_bytes()) != expected:
            raise GuardError(f"Pinned section input changed: {name}")
    plan = _ranges(read_text(job / "source.wiki"), read_json(job / "section-plan.json"))
    lines = read_text(job / "source.wiki").splitlines(keepends=True)
    for row in plan:
        if row.get("directory") != f"sections/{row['id']}":
            raise GuardError("Section directory must match its job-relative ID.")
        raw = evidence_path(job, row["directory"] + "/source.wiki").read_bytes()
        expected = "".join(lines[row["start"] - 1:row["end"]]).encode("utf-8")
        if raw != expected or digest(raw) != row.get("source_sha256"):
            raise GuardError(f"Section source changed: {row['id']}")
        if row.get("status") in {"blocked", "failed"}:
            raise GuardError(f"Section incomplete: {row['id']}")
    return plan


def _worker_vocabulary(job: Path, directory: Path, ident: str) -> list[dict[str, Any]]:
    records = vocabulary_records(read_json(directory / "vocabulary.json"))
    for record in records:
        files = record.get("evidence_files", [])
        if not isinstance(files, list) or any(not isinstance(name, str) for name in files):
            raise GuardError(f"Invalid vocabulary evidence: {ident}")
        evidence = set()
        for name in files:
            # Worker evidence paths are section-relative, including ../../evidence/...
            path = (directory / name).resolve()
            if Path(name).is_absolute() or not path.is_relative_to(job) or not path.is_file():
                raise GuardError(f"Missing or unsafe worker evidence: {ident}: {name}")
            evidence.add(path.relative_to(job).as_posix())
        evidence.update((directory / name).relative_to(job).as_posix()
                        for name in ("source.wiki", "section.wiki", "notes.wiki"))
        record["evidence_files"] = sorted(evidence)
        record["section_id"] = ident
    return records


def assemble_sections(
    job: Path, *, output: Path | None = None, native_citations: bool = False,
    link_map: str | None = None,
) -> dict[str, Any]:
    """Assemble a NEW candidate directory, never replace draft/vocabulary/review/proposal."""
    job = job.resolve()
    output = output or job / "assembly"
    if output.exists() or output.is_symlink():
        raise GuardError("Assembly output exists; choose a new candidate directory.")
    output = output.resolve()
    if not output.is_relative_to(job) or output == job:
        raise GuardError("Assembly output must be a new directory inside the job.")
    _editable_job(job)
    plan = _load_plan(job)
    pieces, notes, vocabulary, conversions, hatnotes = [], [], [], [], []
    category_conversions = []
    artifacts = {"section-plan.json": digest((job / "section-plan.json").read_bytes()),
                 "section-inputs.json": digest((job / "section-inputs.json").read_bytes())}
    mapping, link_decisions = None, []
    if link_map is not None:
        mapping, link_artifacts = load_link_map(job, link_map)
        artifacts.update(link_artifacts)
    for row in plan:
        directory = job / row["directory"]
        for name in ("section.wiki", "notes.wiki", "vocabulary.json"):
            path = evidence_path(job, row["directory"] + "/" + name)
            artifacts[path.relative_to(job).as_posix()] = digest(path.read_bytes())
        fragment = read_text(directory / "section.wiki")
        handoff = read_text(directory / "notes.wiki")
        if not fragment.strip() or not handoff.strip():
            raise GuardError(f"Empty section or handoff: {row['id']}")
        # Map before citation conversion: original citation metadata stays protected.
        if mapping is not None:
            fragment, decisions = adapt_links(fragment, mapping)
            link_decisions.extend({"section_id": row["id"], **item} for item in decisions)
        fragment, converted_hatnotes = convert_related_hatnotes(fragment, mapping)
        hatnotes.extend({"section_id": row["id"], **item} for item in converted_hatnotes)
        fragment, converted_categories = promote_article_categories(fragment)
        category_conversions.extend({"section_id": row["id"], **item}
                                    for item in converted_categories)
        if native_citations:
            fragment, converted = convert_citations(fragment)
            conversions.extend({"section_id": row["id"], **item} for item in converted)
        pieces.append(fragment)
        # Preserve worker notes verbatim; only generated headings use Markdown.
        notes.append(f"## {row['id']}\n\n{handoff}")
        vocabulary.extend(_worker_vocabulary(job, directory, row["id"]))
        row["status"] = "assembled_pending_coordinator_review"
    draft = pieces[0]
    for fragment in pieces[1:]:
        # Insert separators without stripping significant preformatted indentation,
        # trailing spaces, or newlines from any accepted worker fragment.
        if not draft.endswith("\n"):
            draft += "\n"
        if not draft.endswith("\n\n"):
            draft += "\n"
        draft += fragment
    if not draft.endswith("\n"):
        draft += "\n"
    references = reference_inventory(draft)
    if references["undefined"] or references["conflicts"]:
        raise GuardError("Unresolved/conflicting named references; reconcile worker sections.")
    for record in vocabulary:
        for name in record["evidence_files"]:
            artifacts[name] = digest(evidence_path(job, name).read_bytes())
    outputs = {
        output / "draft.wiki": draft.encode("utf-8"),
        output / "section-handoffs.md": ("\n\n".join(notes) + "\n").encode("utf-8"),
        output / "worker-vocabulary.json": json_bytes(vocabulary),
        output / "integrated-section-plan.json": json_bytes(plan),
        output / "citation-conversions.json": json_bytes(conversions),
        output / "related-hatnote-conversions.json": json_bytes(hatnotes),
        output / "category-conversions.json": json_bytes(category_conversions),
        output / "link-decisions.json": json_bytes(link_decisions),
        output / "inventory.json": json_bytes(inventory(draft)),
        output / "assembly.json": json_bytes({
            "schema": 1, "status": "candidate_only", "editorial_review": "pending",
            "draft_sha256": digest(draft.encode("utf-8")), "inputs": artifacts,
            "evidence_path_base": "job", "native_citations": native_citations,
            "link_map": link_map,
        }),
    }
    write_new(outputs)
    return {"output": str(output), "sections": len(plan), "vocabulary_entries": len(vocabulary),
            "status": "candidate_only", "editorial_review": "pending"}


def coverage_report(job: Path, draft: Path) -> dict[str, Any]:
    """Report differences only; source disagreements and omissions remain editorial decisions."""
    source_bytes = (job / "source.wiki").read_bytes()
    draft_bytes = draft.read_bytes()
    source = inventory(source_bytes.decode("utf-8"))
    candidate = inventory(draft_bytes.decode("utf-8"))
    expected, actual = Counter(source["files"]), Counter(candidate["files"])
    return {
        "schema": 1, "status": "review_required", "source_sha256": digest(source_bytes),
        "draft_sha256": digest(draft_bytes),
        "missing_files": dict(expected - actual), "extra_files": dict(actual - expected),
        "missing_source_urls": sorted(set(source["urls"]) - set(candidate["urls"])),
        "source": source, "draft": candidate,
        "limits": "Raw-markup comparison only. Template filenames are candidates; transclusions "
                  "not expanded. No Commons/license verification, semantic link matching, "
                  "translation review, omission authorization, or publication approval.",
    }
