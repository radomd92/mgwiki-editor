"""Offline, article-independent inventories and conservative citation conversion."""

from __future__ import annotations

import html
import re
from collections import Counter
from collections.abc import Iterator
from typing import Any

import mwparserfromhell as mw

from .core import GuardError
from .references import reference_inventory as reference_inventory

FILE_PREFIXES = ("file:", "image:", "media:", "sary:")


def _markup_parts(text: str) -> Iterator[Any]:
    """Expose gallery captions, which the parser otherwise leaves as literal text."""
    pending = [mw.parse(text)]
    for code in pending:
        yield code
        for tag in code.filter_tags():
            if str(tag.tag).casefold() == "gallery":
                for line in str(tag.contents).splitlines():
                    _, separator, caption = line.partition("|")
                    if separator and caption:
                        pending.append(mw.parse(caption))


def reference_key(tag: Any) -> tuple[str, str]:
    """Reference names are scoped by group, not globally unique."""
    def value(key: str) -> str:
        return html.unescape(str(tag.get(key).value)).strip() if tag.has(key) else ""

    return value("group"), value("name")


def inventory(text: str) -> dict[str, Any]:
    """Inspect raw markup only; never resolve links, templates, URLs or files."""
    parts = list(_markup_parts(text))
    links = []
    files: Counter[str] = Counter()
    categories = []
    for link in (link for code in parts for link in code.filter_wikilinks()):
        target = str(link.title).strip()
        links.append({"target": target, "label": str(link.text or link.title)})
        bare = target.lstrip(":")
        if bare.casefold().startswith(FILE_PREFIXES):
            files[bare.split(":", 1)[1].strip().replace("_", " ")] += 1
        if bare.casefold().startswith(("sokajy:", "category:")):
            categories.append(str(link))
    # Gallery filenames are not Wikilink nodes. Captions' links were counted above.
    for tag in (tag for code in parts for tag in code.filter_tags()):
        if str(tag.tag).casefold() == "gallery":
            for line in str(tag.contents).splitlines():
                name = line.split("|", 1)[0].strip()
                prefixed = name.casefold().startswith(FILE_PREFIXES)
                if prefixed:
                    name = name.split(":", 1)[1].strip()
                if name and (prefixed or re.fullmatch(r"[^<>\[\]{}\n]+\.[^\s./]+", name)):
                    files[name.replace("_", " ")] += 1
    templates = [str(template) for code in parts for template in code.filter_templates()]
    # Bare infobox/template filenames need editorial checking, not guessed file metadata.
    candidates = []
    for template in (template for code in parts for template in code.filter_templates()):
        for param in template.params:
            value = str(param.value).strip()
            if re.fullmatch(r"[^\[\]{}\n]+\.(?:jpe?g|png|svg|gif|webp|tiff?)", value, re.I):
                candidates.append({"template": str(template.name).strip(),
                                   "parameter": str(param.name).strip(), "value": value})
    return {
        "links": links, "files": dict(sorted(files.items())),
        "template_file_candidates": candidates, "categories": categories,
        "templates": templates, "references": reference_inventory(text),
        "urls": sorted(set(re.findall(r"https?://[^\s<>\]|}]+", text))),
    }


def literal_citation(template: Any) -> str:
    """Render every populated parameter in source order, without guessing name parts.

    No fixed author limit, field whitelist, URL resolver, or silent metadata loss.
    Labels remain original metadata keys; coordinator adapts presentation separately.
    """
    fields = []
    for parameter in template.params:
        value = str(parameter.value).strip()
        if value:
            fields.append(f"{str(parameter.name).strip()}: {value}")
    if not fields:
        raise GuardError("Empty citation template requires editorial handling.")
    return "; ".join(fields) + "."


def convert_citations(text: str) -> tuple[str, list[dict[str, str]]]:
    """Convert citation templates only, preserving unknown/maintenance templates."""
    code = mw.parse(text)
    conversions = []
    # Children first: nested templates remain literal unless themselves citations.
    for template in reversed(code.filter_templates()):
        name = str(template.name).strip().replace("_", " ").casefold()
        if name == "citation" or name.startswith("cite "):
            original = str(template)
            replacement = literal_citation(template)
            code.replace(template, replacement)
            conversions.append({"source": original, "replacement": replacement})
    return str(code), conversions
