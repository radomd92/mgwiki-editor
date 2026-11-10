"""Literal Cite graph, including delayed core #tag calls; never expands templates."""

from __future__ import annotations

import html
from collections import Counter
from typing import Any

import mwparserfromhell as mw


def reference_nodes(text: str) -> tuple[list[dict[str, Any]], list[str]]:
    """Expose native/delayed references once; dynamic attributes need real parsing."""
    nodes, errors = [], []
    literal = {"nowiki", "pre", "code", "syntaxhighlight", "source", "math", "chem"}

    def walk(code, *, in_ref=False, inherited_group="", depth=0):
        if depth > 80:
            errors.append("Reference nesting exceeds the inspection limit.")
            return
        for node in code.nodes:
            kind, body, attrs, reuse, delayed = None, None, {}, False, False
            if isinstance(node, mw.nodes.Tag):
                tag = str(node.tag).strip().casefold()
                if tag in literal:
                    continue
                if tag in {"ref", "references"}:
                    kind, body = tag, node.contents
                    if in_ref and tag == "ref":
                        errors.append("Raw nested references need delayed core #tag markup.")
                    for attribute in node.attributes:
                        key = str(attribute.name).strip().casefold()
                        if key in {"name", "group"}:
                            if key in attrs:
                                errors.append("Duplicate reference name/group attribute.")
                            attrs[key] = html.unescape(str(attribute.value or "")).strip()
                    reuse = node.self_closing or not str(body or "").strip()
            elif isinstance(node, mw.nodes.Template):
                name = str(node.name).strip().casefold().replace(" ", "")
                if name in {"#tag:ref", "#tag:references"}:
                    kind, delayed = name.split(":", 1)[1], True
                    seen = set()
                    for parameter in node.params:
                        key = str(parameter.name).strip()
                        if key in {"1", "name", "group"}:
                            if key in seen:
                                errors.append("Duplicate delayed reference parameter.")
                            seen.add(key)
                            if key == "1":
                                body = parameter.value
                            else:
                                attrs[key] = html.unescape(str(parameter.value)).strip()
                    reuse = not str(body or "").strip()
            if kind is not None:
                if any("{{" in value or "[[" in value for value in attrs.values()):
                    errors.append("Dynamic reference attributes require explicit literal values.")
                group = attrs.get("group", inherited_group if kind == "ref" else "")
                nodes.append({"kind": kind, "group": group,
                              "name": attrs.get("name", ""), "body": str(body or ""),
                              "reuse": reuse, "delayed": delayed, "raw": str(node)})
                if body is not None:
                    walk(body, in_ref=kind == "ref" and not delayed,
                         inherited_group=group if kind == "references" else "", depth=depth + 1)
            elif isinstance(node, mw.nodes.Tag) and str(node.tag).casefold() == "gallery":
                for line in str(node.contents).splitlines():
                    _, separator, caption = line.partition("|")
                    if separator:
                        walk(mw.parse(caption), in_ref=in_ref, depth=depth + 1)
            else:
                for child in node.__children__():
                    walk(child, in_ref=in_ref, inherited_group=inherited_group, depth=depth + 1)

    walk(mw.parse(text))
    return nodes, sorted(set(errors))


def reference_inventory(text: str) -> dict[str, Any]:
    """Names scoped by decoded group; parser/render review still required."""
    nodes, errors = reference_nodes(text)
    definitions, calls, conflicts = {}, Counter(), []
    anonymous, groups, renderers = 0, set(), set()
    for node in nodes:
        group, name = node["group"], node["name"]
        if node["kind"] == "references":
            renderers.add(group)
            continue
        groups.add(group)
        if not name:
            anonymous += 1
            continue
        key = (group, name)
        calls[key] += 1
        if not node["reuse"]:
            if key in definitions and definitions[key] != node["body"]:
                conflicts.append({"group": group, "name": name})
            definitions[key] = node["body"]
    return {
        "anonymous_count": anonymous,
        "named": [{"group": group, "name": name, "calls": count,
                   "body": definitions.get((group, name))}
                  for (group, name), count in sorted(calls.items())],
        "undefined": [{"group": group, "name": name}
                      for group, name in sorted(calls.keys() - definitions.keys())],
        "conflicts": conflicts, "groups": sorted(groups), "rendered_groups": sorted(renderers),
        "missing_renderers": sorted(groups - renderers), "errors": errors,
    }
