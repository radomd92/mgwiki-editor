"""Offline HTML checks. Never loads linked images, CSS, scripts or references."""

from __future__ import annotations

from collections import Counter
from html.parser import HTMLParser
from urllib.parse import unquote


def rendering_report(document: str) -> dict:
    """Catch Cite errors, missing template links and dangling native Cite anchors."""
    ids, targets, errors = Counter(), set(), set()

    class Inspect(HTMLParser):
        def handle_starttag(self, tag, attributes):
            attrs = dict(attributes)
            classes = set((attrs.get("class") or "").casefold().split())
            if classes & {"error", "mw-ext-cite-error", "errorbox"}:
                errors.add("Parser/citation error element.")
            if tag in {"script", "iframe"}:
                errors.add("Active preview HTML element.")
            if "new" in classes and (attrs.get("title") or "").casefold().startswith(
                ("template:", "endrika:"),
            ):
                errors.add("Unresolved template in rendered output.")
            if attrs.get("id"):
                ids[attrs["id"]] += 1
            href = attrs.get("href") or ""
            if href.startswith(("#cite_note", "#cite_ref")):
                targets.add(unquote(href[1:]))

        handle_startendtag = handle_starttag

    parser = Inspect(convert_charrefs=True)
    parser.feed(document)
    parser.close()
    dangling = sorted(targets - ids.keys())
    duplicates = sorted(key for key, count in ids.items()
                        if count > 1 and key.startswith(("cite_note", "cite_ref")))
    if dangling:
        errors.add("Rendered citation anchor has no destination.")
    if duplicates:
        errors.add("Duplicate rendered citation identifier.")
    return {"valid": not errors, "errors": sorted(errors), "dangling_citations": dangling,
            "duplicate_citation_ids": duplicates,
            "limits": "Offline HTML structure only; no resource access, licensing, semantic "
                      "citation provenance, translation review or publication approval."}
