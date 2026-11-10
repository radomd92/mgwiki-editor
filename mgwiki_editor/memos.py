"""Offline dictionary indexes and sense-specific vocabulary reconciliation reports."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from .artifacts import evidence_path, read_evidence
from .core import GuardError, digest


def vocabulary_records(data: Any) -> list[dict[str, Any]]:
    """Accept existing worker wrappers, without inferring definitions or review statuses."""
    if isinstance(data, dict):
        data = data.get("terms", data.get("entries"))
    if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
        raise GuardError("Vocabulary must be a list or a terms/entries wrapper.")
    return data


def _lookup_identity(data: dict[str, Any]) -> tuple[str, str]:
    """404 replies may omit word/edition; accept only their exact recorded lookup URL."""
    edition, word = data.get("edition"), data.get("word")
    url = data.get("url")
    if url:
        if not isinstance(url, str):
            raise GuardError("Malformed dictionary evidence URL.")
        parsed = urlsplit(url)
        if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                or parsed.username or parsed.password or parsed.query or parsed.fragment):
            raise GuardError("Malformed dictionary evidence URL.")
        parts = parsed.path.split("/")
        if len(parts) == 4 and parts[1] == "wiktionary-pages" and parts[2] in {"en", "mg"}:
            url_edition, url_word = parts[2], unquote(parts[3])
            if ((edition is not None and edition != url_edition)
                    or (word is not None and (not isinstance(word, str)
                                              or word.strip() != url_word))):
                raise GuardError("Dictionary evidence identity disagrees with its recorded URL.")
            edition, word = url_edition, url_word
    if edition not in {"en", "mg"} or not isinstance(word, str) or not word.strip():
        raise GuardError("Dictionary evidence needs an exact edition/word or recorded lookup URL.")
    return edition, word.strip()


def dictionary_index(job: Path, files: list[str]) -> dict[str, Any]:
    """Index all explicit replies, including misses/failures; never pick a winning sense."""
    grouped = defaultdict(list)
    artifacts = {}
    for filename in files:
        pinned = read_evidence(job, filename)
        if pinned.name in artifacts:
            continue
        artifacts[pinned.name] = pinned.sha256
        data = pinned.data
        if not isinstance(data, dict) or not isinstance(data.get("status"), str):
            raise GuardError("Dictionary evidence needs its original status.")
        edition, word = _lookup_identity(data)
        entries = data.get("entries", [])
        if not isinstance(entries, list):
            raise GuardError("Malformed dictionary evidence entries.")
        grouped[edition, word].append({
            "file": pinned.name, "sha256": pinned.sha256, "status": data["status"],
            "retrieved_at": data.get("retrieved_at"), "entry_count": len(entries),
        })
    return {"schema": 1, "status": "indexed_only", "artifacts": dict(sorted(artifacts.items())),
            "lookups": [{"edition": edition, "word": word,
                         "responses": sorted(responses, key=lambda row: row["file"])}
                        for (edition, word), responses in sorted(grouped.items())],
            "limits": "Exact lookup identities only; case, accents, plurals and senses not merged. "
                      "Found, missing, malformed and failed replies do not verify a translation."}


def vocabulary_report(job: Path, filename: str, lookups: list[str]) -> dict[str, Any]:
    """Report exact sense groups, inconsistent choices and evidence needs without editing memo."""
    pinned = read_evidence(job, filename)
    records = vocabulary_records(pinned.data)
    dictionary = dictionary_index(job, lookups)
    artifacts = {**dictionary["artifacts"], pinned.name: pinned.sha256}
    groups = defaultdict(list)
    unclassified, unresolved, issues = [], [], []
    uncertain = set()
    for index, record in enumerate(records):
        fields = ("source_language", "source_term", "source_sense", "domain")
        key = tuple(record.get(field, "") for field in fields)
        if any(not isinstance(value, str) for value in key):
            raise GuardError("Vocabulary identity fields must be strings.")
        if not all(key[:3]):
            unclassified.append(index)
        else:
            groups[key].append(index)
        status = record.get("status")
        if status is not None and not isinstance(status, str):
            raise GuardError("Vocabulary status must be a string when present.")
        if status not in {"verified", "descriptive"}:
            unresolved.append(index)
        if record.get("source_language") == "en" and status != "verified":
            term = record.get("source_term", "").strip().casefold()
            if term:
                uncertain.add(term)
        evidence = record.get("evidence_files", [])
        if not isinstance(evidence, list) or any(not isinstance(name, str) for name in evidence):
            raise GuardError("Vocabulary evidence_files must be a list of job-relative paths.")
        for name in evidence:
            path = evidence_path(job, name)
            artifacts[path.relative_to(job.resolve()).as_posix()] = digest(path.read_bytes())
        required = ("source_sense", "chosen_expression", "english_definition",
                    "definition_origin", "malagasy_definition", "reason")
        missing = [field for field in required if not record.get(field)]
        if not evidence:
            missing.append("evidence_files")
        if missing:
            issues.append({"record_index": index, "missing_fields": missing})
    sense_groups = []
    for key, indices in sorted(groups.items()):
        variants = [records[index] for index in indices]
        choices = [record.get("chosen_expression") for record in variants]
        # Equality only: no source-term aliasing, substring matching or silent first-wins merge.
        fields = ("chosen_expression", "english_definition", "malagasy_definition", "status")
        inconsistent = [field for field in fields
                        if any(record.get(field) != variants[0].get(field) for record in variants)]
        sense_groups.append({"identity": dict(zip(
            ("source_language", "source_term", "source_sense", "domain"), key, strict=True,
        )), "record_indices": indices, "chosen_expressions": choices,
            "reconciliation_fields": inconsistent})
    return {"schema": 1, "status": "review_required", "artifacts": dict(sorted(artifacts.items())),
            "records": records, "sense_groups": sense_groups, "dictionary": dictionary,
            "unclassified_record_indices": unclassified, "unresolved_record_indices": unresolved,
            "missing_fields": issues, "distinct_uncertain_english_terms": len(uncertain),
            "unknown_vocabulary_memo_required": len(uncertain) > 100,
            "limits": "Records/statuses unchanged. Dictionary index is not sense verification. "
                      "Unclassified language/term/sense records excluded from grouping. "
                      "Count excludes only explicitly verified English terms; names/idioms and "
                      "source disagreements need coordinator classification. No memo created, "
                      "approval granted, source issue erased, or publication attempted."}
