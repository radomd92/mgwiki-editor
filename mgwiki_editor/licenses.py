"""File-rights evidence capsules. No URL access, rights invention or automatic approval."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlsplit

from .artifacts import read_evidence
from .core import GuardError, digest, json_bytes, title

RIGHTS_FIELDS = (
    "LicenseShortName",
    "LicenseUrl",
    "UsageTerms",
    "Copyrighted",
    "NonFree",
    "AttributionRequired",
    "Artist",
    "Credit",
    "Attribution",
    "Restrictions",
    "Permission",
    "CopyrightNotice",
    "License",
)


def file_name(value: str) -> str:
    if not isinstance(value, str):
        raise GuardError("Filename must be an exact string.")
    value = title(value)
    if value.casefold().startswith(("file:", "sary:", "image:", "http://", "https://")):
        raise GuardError("Supply bare filename, not a namespace or URL.")
    return value[:1].upper() + value[1:]


def _value(metadata: dict, field: str):
    row = metadata.get(field)
    return row.get("value") if isinstance(row, dict) else None


def _boolean(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().casefold() in {"true", "false", "1", "0"}:
        return value.strip().casefold() in {"true", "1"}
    return None


def _license(url) -> tuple[str, list[str]]:
    if not isinstance(url, str):
        return "unrecognized", []
    try:
        parsed = urlsplit(url.strip())
        if (
            parsed.scheme not in {"http", "https"}
            or parsed.username
            or parsed.password
            or parsed.hostname not in {"creativecommons.org", "www.creativecommons.org"}
            or parsed.port is not None
            or parsed.query
            or parsed.fragment
        ):
            return "unrecognized", []
    except ValueError:
        return "unrecognized", []
    path = parsed.path.rstrip("/")
    match = re.fullmatch(
        r"/licenses/(by|by-sa|by-nc|by-nd|by-nc-sa|by-nc-nd)/"
        r"(1\.0|2\.0|2\.5|3\.0|4\.0)(?:/deed(?:\.[a-z-]+)?)?",
        path,
    )
    if match:
        kind = match[1]
        if kind not in {"by", "by-sa"}:
            return "nonfree_cc_terms", []
        return "cc_" + kind.replace("-", "_") + "_" + match[2], [
            "attribution",
            "license_notice",
            *(["share_alike_for_adaptations"] if kind == "by-sa" else []),
        ]
    if re.fullmatch(r"/publicdomain/zero/1\.0(?:/deed(?:\.[a-z-]+)?)?", path):
        return "cc0_1.0", []
    if re.fullmatch(r"/publicdomain/mark/1\.0(?:/deed(?:\.[a-z-]+)?)?", path):
        return "public_domain_mark_claim", []
    return "unrecognized", []


def license_evidence(filename: str, response: dict) -> dict:
    """Inspect exact response for requested file, retaining raw fields and restrictions.

    Caller must separately establish origin. Even recognized license is a metadata
    claim, not an editorial determination of copyright, authorship or all rights.
    """
    filename = file_name(filename)
    if not isinstance(response, dict) or any(
        key in response for key in ("continue", "error", "errors", "warnings")
    ):
        raise GuardError("Failed/incomplete file response cannot establish license evidence.")
    query = response.get("query")
    pages = query.get("pages") if isinstance(query, dict) else None
    if not isinstance(pages, list):
        raise GuardError("License evidence requires formatversion=2 file metadata.")
    matching = []
    for page in pages:
        if not isinstance(page, dict):
            raise GuardError("Malformed file metadata page.")
        if page.get("ns") != 6:
            continue
        reported = page.get("title")
        if not isinstance(reported, str) or ":" not in reported:
            raise GuardError("File metadata needs exact reported namespace/title.")
        if file_name(reported.split(":", 1)[1]) == filename:
            matching.append(page)
    if len(matching) != 1:
        raise GuardError("Exact requested file metadata absent or conflicting; never guess a flag.")
    page = matching[0]
    info = page.get("imageinfo", [])
    if not isinstance(info, list) or any(not isinstance(row, dict) for row in info):
        raise GuardError("Malformed file-version metadata.")
    versions = []
    for row in info:
        metadata = row.get("extmetadata", {})
        if not isinstance(metadata, dict):
            raise GuardError("Malformed structured rights metadata.")
        kind, obligations = _license(_value(metadata, "LicenseUrl"))
        nonfree = _boolean(_value(metadata, "NonFree"))
        attribution = _boolean(_value(metadata, "AttributionRequired"))
        if nonfree is True or kind == "nonfree_cc_terms":
            assessment = "not_a_free_reuse_candidate"
        elif kind.startswith("cc_by") and attribution is False:
            assessment = "conflicting_metadata_needs_review"
        elif kind == "public_domain_mark_claim":
            assessment = "public_domain_claim_needs_review"
        elif kind != "unrecognized":
            assessment = "recognized_license_candidate_needs_review"
        elif _boolean(_value(metadata, "Copyrighted")) is False:
            assessment = "public_domain_claim_needs_review"
        else:
            assessment = "insufficient_rights_evidence"
        versions.append(
            {
                "timestamp": row.get("timestamp"),
                "sha1": row.get("sha1"),
                "version_fields_present": bool(
                    isinstance(row.get("timestamp"), str)
                    and row["timestamp"]
                    and isinstance(row.get("sha1"), str)
                    and row["sha1"]
                ),
                "url": row.get("url"),
                "descriptionurl": row.get("descriptionurl"),
                "rights_fields": {
                    field: metadata[field] for field in RIGHTS_FIELDS if field in metadata
                },
                "license_identity": kind,
                "metadata_assessment": assessment,
                "reported_obligations": obligations,
                "restriction_review_required": bool(_value(metadata, "Restrictions")),
                "attribution_text_present": any(
                    _value(metadata, field) for field in ("Artist", "Credit", "Attribution")
                ),
                "license_approved": False,
            }
        )
    return {
        "schema": 1,
        "kind": "license_evidence",
        "filename": filename,
        "reported_title": page["title"],
        "repository": page.get("imagerepository"),
        "local_description_missing": bool(page.get("missing")),
        "availability_reported": bool(info),
        "versions": versions,
        "origin": "unverified_cached_input",
        "response_sha256": digest(json_bytes(response)),
        "response": response,
        "license_approved": False,
        "limits": "Raw metadata claims, not a legal clearance or current availability proof. "
        "Recognized URI does not establish authorship, exact source-call mapping, "
        "jurisdiction, personality/trademark rights or absence of restrictions. "
        "Review attribution, license terms, version and final use separately. "
        "No URLs/images fetched; missing local description can coexist "
        "with shared file.",
    }


def license_report(job: Path, evidence: str, filename: str) -> dict:
    """Build capsule from pinned local API bytes; never claim broker-authenticated origin."""
    pinned = read_evidence(job, evidence)
    data = pinned.data
    if not isinstance(data, dict):
        raise GuardError("License report needs a pinned API response object.")
    response = data.get("response", data)
    result = license_evidence(filename, response)
    result["input"] = {"path": pinned.name, "sha256": pinned.sha256}
    return result
