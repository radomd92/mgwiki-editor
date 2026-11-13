"""Audit pinned file/template/expansion metadata without network or inferred rights."""

from __future__ import annotations

from pathlib import Path

import mwparserfromhell as mw

from .artifacts import evidence_path, read_evidence
from .core import GuardError, digest
from .wikitext import inventory


def _key(value: str) -> str:
    value = value.replace("_", " ").strip()
    return value[:1].upper() + value[1:]


def metadata_audit(job: Path, files: list[str], draft: str = "draft.wiki") -> dict:
    """Report exact evidence and gaps; field presence never grants a reuse license."""
    if not isinstance(files, list) or any(not isinstance(name, str) for name in files):
        raise GuardError("Metadata evidence must be job-relative filenames.")
    raw = evidence_path(job, draft).read_bytes()
    markup = inventory(raw.decode("utf-8"))
    required = {_key(name) for name in markup["files"]}
    required.update(_key(row["value"]) for row in markup["template_file_candidates"])
    images, templates, expansions, artifacts = {}, {}, [], {}
    for name in files:
        pinned = read_evidence(job, name)
        artifacts[pinned.name] = pinned.sha256
        envelope = pinned.data
        if not isinstance(envelope, dict):
            raise GuardError("Metadata evidence must contain an API response object.")
        response = envelope.get("response", envelope)
        if not isinstance(response, dict) or any(
            key in response for key in ("continue", "error", "errors", "warnings")
        ):
            raise GuardError("Incomplete/failed metadata is not verification.")
        if "expandtemplates" in response:
            text = response["expandtemplates"].get("wikitext")
            if not isinstance(text, str):
                raise GuardError("Expansion evidence needs literal returned wikitext.")
            found = inventory(text)["files"]
            matched = envelope.get("template") in markup["templates"]
            if matched:
                required.update(_key(filename) for filename in found)
            expansions.append(
                {
                    "evidence_file": pinned.name,
                    "files": found,
                    "exact_call_in_draft": matched,
                    "language": envelope.get("language"),
                    "source_sha256": envelope.get("source_sha256"),
                }
            )
            continue
        query = response.get("query")
        if not isinstance(query, dict) or not isinstance(query.get("pages"), list):
            raise GuardError("Metadata needs formatversion=2 query.pages.")
        for page in query["pages"]:
            if not isinstance(page, dict) or not isinstance(page.get("title"), str):
                raise GuardError("Malformed metadata page.")
            if page.get("ns") == 6:
                key = _key(page["title"].split(":", 1)[-1])
                info = page.get("imageinfo", [])
                if not isinstance(info, list) or any(not isinstance(row, dict) for row in info):
                    raise GuardError("Malformed imageinfo metadata.")
                images.setdefault(key, []).append(
                    {
                        "evidence_file": pinned.name,
                        "reported_title": page["title"],
                        "language": envelope.get("language"),
                        "repository": page.get("imagerepository"),
                        "imageinfo": info,
                        # Commons files may have missing=true for the local description page.
                        "availability_reported": bool(info),
                        "rights_fields_present": any(
                            isinstance(row.get("extmetadata"), dict)
                            and any(
                                field in row["extmetadata"]
                                for field in ("LicenseShortName", "UsageTerms")
                            )
                            for row in info
                        ),
                    }
                )
            elif page.get("ns") == 10:
                key = _key(page["title"].split(":", 1)[-1])
                revisions = page.get("revisions", [])
                if not isinstance(revisions, list) or any(
                    not isinstance(row, dict) for row in revisions
                ):
                    raise GuardError("Malformed template revisions.")
                templates.setdefault(key, []).append(
                    {
                        "evidence_file": pinned.name,
                        "reported_title": page["title"],
                        "missing_reported": bool(page.get("missing")),
                        "revision_content_present": any(
                            isinstance(
                                row.get("slots", {}).get("main", {}).get("content"),
                                str,
                            )
                            for row in revisions
                        ),
                        "revisions": revisions,
                    }
                )
    template_rows = []
    for call in markup["templates"]:
        template = mw.parse(call).filter_templates()[0]
        name = str(template.name).strip()
        core = name.startswith("#")
        bare = (
            name.split(":", 1)[-1]
            if name.casefold().startswith(
                ("template:", "endrika:"),
            )
            else name
        )
        template_rows.append(
            {
                "call": call,
                "core_parser_function": core,
                "metadata": [] if core else templates.get(_key(bare), []),
                "parameter_contract_approved": False,
            }
        )
    return {
        "schema": 1,
        "status": "review_required",
        "draft": draft,
        "draft_sha256": digest(raw),
        "artifacts": artifacts,
        "files": [
            {"filename": name, "metadata": images.get(name, []), "license_approved": False}
            for name in sorted(required)
        ],
        "templates": template_rows,
        "expansions": expansions,
        "limits": "Caller-supplied pinned evidence, not fresh availability or authenticated "
        "origin by itself. Conflicting versions retained, never silently selected. "
        "Missing local description pages do not disprove shared-file availability. "
        "Review license restrictions, exact call/file mapping, template contracts "
        "and final guarded render separately. No resource fetch or gate clearance.",
    }
