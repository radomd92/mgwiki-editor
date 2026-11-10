"""Read-only mathematical-term audit; substitutions require contextual editorial review."""

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

from .core import digest
from .vocabulary import VOCABULARY_DATABASE, search_key, vocabulary


def prose_parts(code: Wikicode, path: str = "body") -> Iterator[tuple[str, str]]:
    """Visit prose and displayed labels; never scan identifiers, refs or template metadata."""
    for index, node in enumerate(code.nodes):
        location = f"{path}/{index}"
        if isinstance(node, Text):
            yield location, str(node)
        elif isinstance(node, Heading):
            yield from prose_parts(node.title, location + "/heading")
        elif isinstance(node, Wikilink) and node.text is not None:
            yield from prose_parts(node.text, location + "/link-label")
        elif isinstance(node, ExternalLink) and node.title is not None:
            yield from prose_parts(node.title, location + "/link-label")
        elif isinstance(node, Tag) and str(node.tag).casefold() in {
            "b", "i", "strong", "em", "span", "div", "p", "small", "sub", "sup",
        } and node.contents is not None:
            yield from prose_parts(node.contents, location + "/text")


def folded_spans(text: str) -> tuple[str, list[int]]:
    """Normalize search text while mapping every resulting character to original prose."""
    characters = []
    offsets = []
    for offset, char in enumerate(text):
        folded = unicodedata.normalize("NFKD", char.casefold().replace("’", "'"))
        for part in folded:
            if unicodedata.combining(part):
                continue
            if part.isspace():
                part = " "
                if characters and characters[-1] == " ":
                    continue
            characters.append(part)
            offsets.append(offset)
    return "".join(characters), offsets


def audit_mathematical_terms(
    draft: Path, *, cache: Path = VOCABULARY_DATABASE,
) -> dict[str, Any]:
    """Report possible untranslated French math terms with SQLite evidence; never edit a draft."""
    lookup = vocabulary(cache=cache)
    candidates: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in lookup["entries"]:
        # Parentheses qualify a sense; they are not normally part of prose.
        # Commas separate source-listed forms, not invented translations.
        head = entry["french"].split("(", 1)[0]
        for label in head.split(","):
            key = search_key(label.strip().rstrip("."))
            if key:
                candidates[key].append(entry)
    terms = sorted(candidates, key=lambda key: (-len(key), key))
    pattern = re.compile(r"(?<!\w)(?:" + "|".join(re.escape(term) for term in terms) + r")(?!\w)")
    raw = draft.read_bytes()
    matches = []
    for location, text in prose_parts(mwparserfromhell.parse(raw.decode("utf-8"))):
        folded, offsets = folded_spans(text)
        for match in pattern.finditer(folded):
            start, end = offsets[match.start()], offsets[match.end() - 1] + 1
            while end < len(text) and unicodedata.combining(text[end]):
                end += 1
            matches.append({
                "location": location, "term": text[start:end], "normalized_term": match[0],
                "context": text[max(0, start - 60):end + 60],
                "candidates": candidates[match[0]], "status": "requires_context_review",
            })
    return {
        "schema": 1, "draft_path": str(draft), "draft_sha256": digest(raw),
        "database_path": lookup["database_path"], "database_sha256": lookup["database_sha256"],
        "source": lookup["source"], "match_count": len(matches), "matches": matches,
        "limits": (
            "Possible French matches only; not proof of untranslated text or full coverage. "
            "Review English/other terms, plurals, templates, tables, galleries, file captions, "
            "unlabelled links and protected quotations separately. No automatic replacements. "
            "Keep source attribution, inspect qualifiers/flags and select the intended sense."
        ),
    }
