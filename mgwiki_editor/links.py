"""Cached interlanguage evidence and conservative, opt-in link adaptation."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import mwparserfromhell as mw

from .artifacts import read_evidence
from .core import GuardError, title
from .wikitext import FILE_PREFIXES


def _key(value: str) -> str:
    return value.replace("_", " ").strip()


def _local_title(value: str, mainspace: dict[str, set[str]]) -> str:
    value = title(value)
    if ":" in value and value not in mainspace:
        raise GuardError("Colon target needs pinned Malagasy namespace-0 page evidence.")
    return value


def build_link_map(
    job: Path, files: list[str], source_language: str, *, local_files: list[str] | None = None,
) -> dict[str, Any]:
    """Combine explicit cached formatversion=2 langlink batches, never fetch metadata.

    Redirect chains use only recorded edges. Section/interwiki redirects stay unresolved.
    Conflicting snapshots, continuation and cycles require coordinator reconciliation.
    """
    if (not files or not isinstance(source_language, str) or source_language == "mg"
            or not re.fullmatch(r"[a-z][a-z0-9-]{0,19}", source_language)):
        raise GuardError("Supply cached evidence and a non-Malagasy source language.")
    if (job / "job.json").exists():
        state = read_evidence(job, "job.json").data
        source = state.get("source") if isinstance(state, dict) else None
        if not isinstance(source, dict) or source.get("language") != source_language:
            raise GuardError("Link-map language must match the pinned job source.")
    pages: dict[str, dict[str, Any]] = {}
    edges: dict[str, tuple[str, bool]] = {}
    edge_files: dict[str, set[str]] = {}
    artifacts = {}
    local_artifacts = {}
    mainspace: dict[str, set[str]] = {}
    local_identities = {}
    for filename in local_files or []:
        pinned = read_evidence(job, filename)
        local_artifacts[pinned.name] = pinned.sha256
        envelope = pinned.data
        if isinstance(envelope, dict) and envelope.get("language", "mg") != "mg":
            raise GuardError("Namespace evidence must come from Malagasy Wikipedia.")
        response = envelope.get("response", envelope) if isinstance(envelope, dict) else None
        if (not isinstance(response, dict) or any(
            key in response for key in ("continue", "error", "errors", "warnings")
        )):
            raise GuardError("Incomplete/failed Malagasy namespace evidence.")
        query = response.get("query", {})
        if not isinstance(query, dict) or not isinstance(query.get("pages"), list):
            raise GuardError("Malagasy namespace evidence needs formatversion=2 query.pages.")
        for page in query["pages"]:
            if not isinstance(page, dict) or not isinstance(page.get("title"), str):
                raise GuardError("Malformed Malagasy namespace evidence.")
            if type(page.get("ns")) is not int:
                raise GuardError("Malagasy namespace evidence needs an explicit namespace ID.")
            local_title = title(page["title"])
            identity = (page["ns"], bool(page.get("missing", False)))
            if local_title in local_identities and local_identities[local_title] != identity:
                raise GuardError(f"Conflicting Malagasy namespace evidence: {local_title}")
            local_identities[local_title] = identity
            if page["ns"] == 0 and not page.get("missing", False):
                mainspace.setdefault(local_title, set()).add(pinned.name)
    for filename in files:
        pinned = read_evidence(job, filename)
        if pinned.name in local_artifacts:
            raise GuardError("Source and Malagasy namespace evidence must be separate snapshots.")
        artifacts[pinned.name] = pinned.sha256
        envelope = pinned.data
        response = envelope.get("response", envelope) if isinstance(envelope, dict) else None
        if (not isinstance(response, dict) or "continue" in response or "error" in response
                or "errors" in response or "warnings" in response):
            raise GuardError("Incomplete/failed langlink evidence; preserve and reconcile it.")
        query = response.get("query", {})
        if not isinstance(query, dict) or not isinstance(query.get("pages"), list):
            raise GuardError("Langlink evidence needs formatversion=2 query.pages.")
        for page in query["pages"]:
            if (not isinstance(page, dict) or not isinstance(page.get("title"), str)
                    or not page["title"].strip()
                    or page.get("ns") != 0):
                raise GuardError("Langlink evidence must identify source mainspace pages.")
            key = _key(page["title"])
            langlinks = page.get("langlinks", [])
            if not isinstance(langlinks, list) or any(not isinstance(p, dict) for p in langlinks):
                raise GuardError("Malformed language-link evidence.")
            targets = set()
            for link in langlinks:
                if link.get("lang") == "mg":
                    if not isinstance(link.get("title"), str):
                        raise GuardError("Malformed Malagasy language-link title.")
                    targets.add(_local_title(link["title"], mainspace))
            if len(targets) > 1 or (page.get("missing", False) and targets):
                raise GuardError(f"Conflicting Malagasy targets: {key}")
            row = {"mg": next(iter(targets), None), "missing": bool(page.get("missing", False)),
                   "evidence_files": [pinned.name]}
            for target in targets:
                if ":" in target:
                    row["evidence_files"] = sorted(
                        set(row["evidence_files"]) | mainspace[target],
                    )
            if key in pages:
                if (pages[key]["mg"], pages[key]["missing"]) != (row["mg"], row["missing"]):
                    raise GuardError(f"Conflicting cached topic evidence: {key}")
                row["evidence_files"] = sorted(set(
                    pages[key]["evidence_files"] + row["evidence_files"],
                ))
            pages[key] = row
        for kind in ("normalized", "redirects"):
            changes = query.get(kind, [])
            if not isinstance(changes, list):
                raise GuardError("Malformed redirect/normalization evidence.")
            for change in changes:
                if (not isinstance(change, dict) or not isinstance(change.get("from"), str)
                        or not isinstance(change.get("to"), str)):
                    raise GuardError("Malformed redirect/normalization edge.")
                origin, target = _key(change["from"]), _key(change["to"])
                if origin == target and kind == "normalized":
                    continue  # Underscore/space normalization already represented by _key.
                edge = (target, bool(change.get("tofragment") or change.get("tointerwiki")))
                if origin in edges and edges[origin] != edge:
                    raise GuardError(f"Conflicting cached redirect evidence: {origin}")
                edges[origin] = edge
                edge_files.setdefault(origin, set()).add(pinned.name)

    mappings = dict(pages)
    for origin in sorted(edges):
        cursor, seen, used, special = origin, set(), set(), False
        while cursor in edges:
            if cursor in seen:
                raise GuardError(f"Cached redirect cycle: {origin}")
            seen.add(cursor)
            used.update(edge_files[cursor])
            cursor, flag = edges[cursor]
            special |= flag
        terminal = pages.get(cursor, {})
        used.update(terminal.get("evidence_files", []))
        mapped = {"mg": None if special else terminal.get("mg"),
                  "missing": terminal.get("missing", False), "evidence_files": sorted(used),
                  "canonical_source": cursor}
        if special:
            mapped["reason"] = "section_or_interwiki_redirect_requires_review"
        elif not terminal:
            mapped["reason"] = "redirect_target_evidence_missing"
        if origin in pages:
            if (pages[origin]["mg"], pages[origin]["missing"]) != (
                mapped["mg"], mapped["missing"],
            ):
                raise GuardError(f"Conflicting direct/redirect topic evidence: {origin}")
            mapped["evidence_files"] = sorted(used | set(pages[origin]["evidence_files"]))
        mappings[origin] = mapped
    result = {"schema": 1, "status": "cached_candidates_only", "source_language": source_language,
            "target_language": "mg", "artifacts": dict(sorted(artifacts.items())),
            "mappings": dict(sorted(mappings.items())),
            "limits": "Cached langlinks only; not current revisions or independent topic review. "
                      "No target, anchor, country spelling, or Commons/license guesses."}
    if local_artifacts:
        result["local_artifacts"] = dict(sorted(local_artifacts.items()))
    return result


def load_link_map(job: Path, filename: str) -> tuple[dict[str, Any], dict[str, str]]:
    """Rebuild derived mappings from pinned inputs; reject stale or edited assertions."""
    pinned = read_evidence(job, filename)
    data = pinned.data
    if (not isinstance(data, dict) or data.get("schema") != 1
            or not isinstance(data.get("artifacts"), dict) or not data["artifacts"]
            or not isinstance(data.get("local_artifacts", {}), dict)):
        raise GuardError("Link map needs a cached-evidence artifact manifest.")
    rebuilt = build_link_map(
        job, sorted(data["artifacts"]), data.get("source_language", ""),
        local_files=sorted(data.get("local_artifacts", {})),
    )
    if data != rebuilt:
        raise GuardError("Link map or pinned evidence changed; rebuild and review it.")
    return data["mappings"], {
        **data["artifacts"], **data.get("local_artifacts", {}), pinned.name: pinned.sha256,
    }


def adapt_links(text: str, mapping: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    """Map prose links/captions only; preserve protected metadata and original labels.

    Caller supplies a map validated by load_link_map. No automatic plain-text relinking,
    name/country substitutions, foreign anchor guesses or template/citation rewriting.
    """
    code = mw.parse(text)
    decisions = []
    local = {row["mg"] for row in mapping.values() if row.get("mg")}

    def record(link, action, destination=None, evidence=()):
        decisions.append({"source": str(link), "source_target": str(link.title).strip(),
                          "action": action, "destination": destination,
                          "evidence_files": list(evidence)})

    def protected(node):
        for link in node.__children__():
            for item in link.filter_wikilinks():
                record(item, "protected_unchanged")

    def walk(part):
        for node in list(part.nodes):
            if isinstance(node, mw.nodes.Wikilink):
                target = str(node.title).strip()
                bare = target.lstrip(":")
                if bare.casefold().startswith(FILE_PREFIXES):
                    record(node, "file_target_unchanged")
                    if node.text is not None:
                        walk(node.text)
                elif bare.casefold().startswith(("sokajy:", "category:")):
                    record(node, "category_unchanged" if target.startswith(":") else
                           "category_made_inert")
                    if not target.startswith(":"):
                        raw = str(node.title)
                        prefix = len(raw) - len(raw.lstrip())
                        node.title = raw[:prefix] + ":" + raw[prefix:]
                elif target.startswith("#"):
                    record(node, "same_page_anchor_requires_review")
                else:
                    base, separator, _ = target.partition("#")
                    if _key(base) not in mapping and _key(base) in local:
                        record(node, "local_anchor_requires_review" if separator else
                               "local_target_unchanged", _key(base))
                        continue
                    row = mapping.get(_key(base), {})
                    destination = row.get("mg")
                    label = str(node.text) if node.text is not None else target
                    replacement = (f"[[{destination}|{label}]]" if label != destination else
                                   f"[[{destination}]]") if destination else label
                    record(node, ("mapped_anchor_omitted" if separator else "mapped") if
                           destination else "plain_text_no_verified_target", destination,
                           row.get("evidence_files", []))
                    part.replace(node, replacement, recursive=False)
            elif isinstance(node, mw.nodes.Heading):
                walk(node.title)
            elif isinstance(node, mw.nodes.Tag) and str(node.tag).casefold() in {
                "b", "strong", "span", "div", "p", "small", "sub", "sup", "table", "tr", "td", "th",
            } and node.contents is not None:
                walk(node.contents)
            elif isinstance(node, mw.nodes.Tag) and str(node.tag).casefold() == "gallery":
                lines = []
                for line in str(node.contents).splitlines(keepends=True):
                    filename, separator, caption = line.partition("|")
                    parsed = mw.parse(caption)
                    walk(parsed)
                    lines.append(filename + separator + str(parsed))
                node.contents = "".join(lines)
            elif not isinstance(node, mw.nodes.Text):
                protected(node)

    walk(code)
    return str(code), decisions
