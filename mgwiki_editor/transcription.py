"""Offline Malagasy transcription audit; reports candidates, never rewrites prose."""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import mwparserfromhell
from mwparserfromhell.nodes import ExternalLink, Heading, Tag, Text, Wikilink
from mwparserfromhell.wikicode import Wikicode

from .core import digest

# Quotations, titles and identifiers may legitimately keep foreign geminates.
QUOTED = re.compile(r'"[^"\n]*"|“[^”\n]*”|«[^»\n]*»|‘[^’\n]*’')
BARE_URL = re.compile(r"https?://\S+")
WORD = re.compile(r"[^\W\d_]+", re.UNICODE)
GEMINATE = re.compile(r"([bcdfghjklmnpqrstvwxz])\1", re.IGNORECASE)

INLINE_TAGS = {"b", "strong", "span", "div", "p", "small", "sub", "sup"}
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


def transcribable_parts(code: Wikicode, path: str = "body") -> Iterator[tuple[str, str]]:
    """Visit new-prose text only; skip references, foreign-term italics and titles."""
    for index, node in enumerate(code.nodes):
        location = f"{path}/{index}"
        if isinstance(node, Text):
            yield location, str(node)
        elif isinstance(node, Heading):
            yield from transcribable_parts(node.title, location + "/heading")
        elif isinstance(node, Wikilink) and node.text is not None:
            yield from transcribable_parts(node.text, location + "/link-label")
        elif isinstance(node, ExternalLink) and node.title is not None:
            yield from transcribable_parts(node.title, location + "/link-label")
        elif isinstance(node, Tag):
            name = str(node.tag).casefold()
            if name in SKIPPED_TAGS or name in {"i", "em"}:
                continue
            if name in INLINE_TAGS and node.contents is not None:
                yield from transcribable_parts(node.contents, location + "/text")


def audit_transcription(draft: Path) -> dict[str, Any]:
    """Report possible geminated consonants and manual /o/, /u/ review items."""
    raw = draft.read_bytes()
    findings = []
    for location, text in transcribable_parts(mwparserfromhell.parse(raw.decode("utf-8"))):
        masked = QUOTED.sub(lambda match: " " * len(match.group()), text)
        masked = BARE_URL.sub(lambda match: " " * len(match.group()), masked)
        for word_match in WORD.finditer(masked):
            word = word_match.group()
            doubled = GEMINATE.search(word)
            if not doubled:
                continue
            start = word_match.start()
            findings.append(
                {
                    "location": location,
                    "word": word,
                    "sequence": doubled.group(),
                    "capitalized": word[:1].isupper(),
                    "context": text[max(0, start - 60) : word_match.end() + 60],
                    "status": "review_required",
                }
            )
    return {
        "schema": 1,
        "draft_path": str(draft),
        "draft_sha256": digest(raw),
        "finding_count": len(findings),
        "findings": findings,
        "manual_checks": [
            "Confirm each new transcription maps the source /o/ sound to ô.",
            "Confirm each new transcription maps the source /u/ sound to o.",
            "Review geminated-consonant findings against the pinned source; "
            "protected quotations, titles, metadata, identifiers and URLs are skipped.",
        ],
        "limits": (
            "Candidate geminated consonants only. The script cannot infer source "
            "pronunciation, so /o/→ô and /u/→o require editorial review against the "
            "pinned source. Findings in established names still need a documented "
            "decision. No automatic replacements or publication approval."
        ),
    }
