"""Offline terminology/draft consistency audit; reports candidates, never edits."""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import mwparserfromhell
from mwparserfromhell.nodes import ExternalLink, Heading, Tag, Text, Wikilink
from mwparserfromhell.wikicode import Wikicode

from .core import GuardError, digest, read_json
from .memos import vocabulary_records

QUOTED = re.compile(r'"[^"\n]*"|“[^”\n]*”|«[^»\n]*»|‘[^’\n]*’')
BARE_URL = re.compile(r"https?://\S+")
SKIPPED_TAGS = {
    "ref",
    "references",
    "nowiki",
    "math",
    "chem",
    "code",
    "pre",
    "syntaxhighlight",
    "source",
    "gallery",
    "timeline",
}
INLINE_TAGS = {"b", "strong", "span", "div", "p", "small", "sub", "sup"}


def folded(value: str) -> str:
    """Case/diacritic-insensitive search form; original evidence stays unchanged."""
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def count_phrase(text: str, phrase: str) -> int:
    target = folded(phrase).strip()
    if not target:
        return 0
    pattern = r"(?<!\w)" + re.escape(target) + r"(?!\w)"
    return len(re.findall(pattern, folded(text)))


def _parts(
    code: Wikicode, path: str = "body", *, foreign: bool = False
) -> Iterator[tuple[str, str, bool]]:
    """Visit displayed prose; skip references, templates and non-prose tags."""
    for index, node in enumerate(code.nodes):
        location = f"{path}/{index}"
        if isinstance(node, Text):
            yield location, str(node), foreign
        elif isinstance(node, Heading):
            yield from _parts(node.title, location + "/heading", foreign=foreign)
        elif isinstance(node, Wikilink) and node.text is not None:
            yield from _parts(node.text, location + "/link-label", foreign=foreign)
        elif isinstance(node, ExternalLink) and node.title is not None:
            yield from _parts(node.title, location + "/link-label", foreign=foreign)
        elif isinstance(node, Tag):
            name = str(node.tag).casefold()
            if name in SKIPPED_TAGS:
                continue
            if name in {"i", "em"} and node.contents is not None:
                yield from _parts(node.contents, location + "/foreign-term", foreign=True)
            elif name in INLINE_TAGS and node.contents is not None:
                yield from _parts(node.contents, location + "/text", foreign=foreign)


def _masked(text: str) -> str:
    masked = QUOTED.sub(lambda match: " " * len(match.group()), text)
    return BARE_URL.sub(lambda match: " " * len(match.group()), masked)


def audit_terminology(job: Path, draft: Path) -> dict[str, Any]:
    """Reconcile vocabulary decisions with the assembled draft for editorial review."""
    job = job.resolve()
    draft = draft.resolve()
    if not draft.is_relative_to(job) or draft == job:
        raise GuardError("Draft must be a file inside the job.")
    vocabulary_path = job / "vocabulary.json"
    if not vocabulary_path.is_file():
        raise GuardError("Job has no vocabulary.json; no terminology audit.")
    vocabulary_bytes = vocabulary_path.read_bytes()
    draft_bytes = draft.read_bytes()
    records = vocabulary_records(read_json(vocabulary_path))
    code = mwparserfromhell.parse(draft_bytes.decode("utf-8"))

    prose = []
    unprotected = []
    foreign_terms = []
    for location, text, italic in _parts(code):
        prose.append(text)
        if italic:
            foreign_terms.append((location, text))
        else:
            unprotected.append((location, _masked(text)))
    prose_text = "\n".join(prose)
    unprotected_text = "\n".join(text for _, text in unprotected)

    unresolved, missing_expression, missing_fields = [], [], []
    by_identity: dict[tuple[str, str, str], list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    source_hits = []
    for index, record in enumerate(records):
        term = record.get("source_term")
        expression = record.get("chosen_expression")
        status = record.get("status")
        missing = [
            field
            for field in ("source_term", "source_sense", "chosen_expression", "malagasy_definition")
            if not record.get(field)
        ]
        if missing:
            missing_fields.append({"record_index": index, "missing_fields": missing})
        if status not in {"verified", "descriptive"}:
            unresolved.append({"record_index": index, "source_term": term, "status": status})
        if isinstance(expression, str) and expression.strip():
            if count_phrase(prose_text, expression) == 0:
                missing_expression.append(
                    {
                        "record_index": index,
                        "source_term": term,
                        "chosen_expression": expression,
                        "status": status,
                    }
                )
        if isinstance(term, str) and term.strip() and record.get("source_language", "en") == "en":
            count = count_phrase(unprotected_text, term)
            if count:
                source_hits.append(
                    {
                        "record_index": index,
                        "source_term": term,
                        "count": count,
                        "chosen_expression": expression,
                        "status": "review_required",
                    }
                )
        identity = (
            str(record.get("source_term", "")),
            str(record.get("source_sense", "")),
            str(record.get("domain", "")),
        )
        if all(identity):
            by_identity[identity].append((index, record))

    choice_variants, definition_variants = [], []
    for identity, rows in sorted(by_identity.items()):
        choice_map: dict[str, str] = {}
        for _, record in rows:
            expression = record.get("chosen_expression")
            if expression:
                choice_map.setdefault(folded(str(expression)).strip(), str(expression))
        definitions = sorted(
            {
                str(record.get("malagasy_definition"))
                for _, record in rows
                if record.get("malagasy_definition")
            }
        )
        base = {
            "source_term": identity[0],
            "source_sense": identity[1],
            "domain": identity[2],
            "record_indices": [index for index, _ in rows],
        }
        if len(choice_map) > 1:
            choice_variants.append({**base, "chosen_expressions": sorted(choice_map.values())})
        if len(definitions) > 1:
            definition_variants.append({**base, "definition_count": len(definitions)})

    return {
        "schema": 1,
        "job": str(job),
        "draft_path": str(draft.relative_to(job)),
        "draft_sha256": digest(draft_bytes),
        "vocabulary_path": str(vocabulary_path.relative_to(job)),
        "vocabulary_sha256": digest(vocabulary_bytes),
        "record_count": len(records),
        "foreign_term_spans": len(foreign_terms),
        "finding_count": (
            len(unresolved)
            + len(missing_expression)
            + len(missing_fields)
            + len(source_hits)
            + len(choice_variants)
            + len(definition_variants)
        ),
        "unresolved_records": unresolved,
        "missing_expression_records": missing_expression,
        "missing_field_records": missing_fields,
        "source_term_hits": source_hits,
        "choice_variants": choice_variants,
        "definition_variants": definition_variants,
        "limits": (
            "Exact folded phrase matching only; inflection, synonyms and context are editorial. "
            "Foreign-term italics, quotations, references, templates, identifiers and URLs are "
            "skipped for untranslated-source hits. Names/acronyms may appear in source form "
            "legitimately. Not vocabulary verification, translation review or publication approval."
        ),
    }
