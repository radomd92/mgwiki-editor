"""Offline short-citation diagnostics; candidates never establish missing provenance."""

from __future__ import annotations

import re
from pathlib import Path

import mwparserfromhell as mw

from .artifacts import evidence_path
from .core import digest
from .references import reference_inventory, reference_nodes

SHORT = re.compile(r"\b(?:op\.?\s*cit|loc\.?\s*cit|ibid)\b\.?", re.IGNORECASE)
LOCATOR = re.compile(r"^\s*([^\n:;]{1,100}?),?\s+pp?\.\s*\d[\d\s,–—.\-]*$", re.IGNORECASE)


def _inspect(text: str) -> dict:
    nodes, _ = reference_nodes(text)
    bodies = [node["body"] for node in nodes if node["kind"] == "ref" and not node["reuse"]]
    candidates = list(
        dict.fromkeys(
            bodies + [line for line in text.splitlines() if line.lstrip().startswith("*")],
        )
    )
    short = []
    for node in nodes:
        if node["kind"] != "ref" or node["reuse"]:
            continue
        # Child references carry their own provenance, not the parent's note text.
        body = mw.parse(node["body"])
        for tag in list(body.filter_tags()):
            if str(tag.tag).strip().casefold() == "ref":
                body.replace(tag, "")
        plain = body.strip_code()
        marker = SHORT.search(plain)
        locator = LOCATOR.fullmatch(plain) if marker is None else None
        if marker is None and locator is None:
            continue
        prefix = (plain[: marker.start()] if marker else locator.group(1)).rstrip(" ,.'\";:")
        author = re.search(r"([^\W\d_][\w’'-]*)$", prefix, re.UNICODE)
        surname = (
            prefix
            if locator
            else author.group(1)
            if author and marker.group().lower().startswith(("op", "loc"))
            else None
        )
        matches = []
        if surname:
            labels = re.split(r"\s+(?:and|&)\s+", surname)
            for candidate in candidates:
                visible = mw.parse(candidate).strip_code()
                if (
                    SHORT.search(visible) is None
                    and LOCATOR.fullmatch(visible) is None
                    and all(
                        re.search(rf"(?<!\w){re.escape(label)}(?!\w)", candidate, re.IGNORECASE)
                        for label in labels
                    )
                ):
                    matches.append(
                        {
                            "text": candidate,
                            "basis": "same_author_label_only" if locator else "same_surname_only",
                        }
                    )
        short.append(
            {
                "reference": node["raw"],
                "group": node["group"],
                "name": node["name"],
                "shorthand": marker.group() if marker else "author_page_locator",
                "author_label": surname,
                "status": "candidates_require_review" if matches else "needs_evidence",
                "candidates": matches,
            }
        )
    return {
        "empty": not text.strip(),
        "references": reference_inventory(text),
        "short_citations": short,
    }


def citation_audit(job: Path, draft: str = "draft.wiki") -> dict:
    """Read exact scoped source/draft bytes; never fetch, repair, or clear review gates."""
    inputs, results = {}, {}
    for label, name in (("source", "source.wiki"), ("draft", draft)):
        path = evidence_path(job, name)
        raw = path.read_bytes()
        inputs[label] = {"path": path.relative_to(job.resolve()).as_posix(), "sha256": digest(raw)}
        results[label] = _inspect(raw.decode("utf-8"))
    return {
        "schema": 1,
        "status": "review_required",
        "inputs": inputs,
        **results,
        "limits": "Literal native/core #tag references and explicit bibliography entries "
        "only. Surname matches are candidates, never identified works, editions "
        "or quotation antecedents. No repair, external lookup, source-disagreement "
        "classification, citation-gate clearance or publication authorization.",
    }
