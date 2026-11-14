"""Bounded en->mg interlanguage mapping for pinned source link targets."""
import json, re
import mwparserfromhell
from mgwiki_editor.core import Wiki, now

text = open("runs/biol-sex-20261114/source.wiki", encoding="utf-8").read()
code = mwparserfromhell.parse(text)
targets = []
seen = set()
for link in code.filter_wikilinks():
    raw = str(link.title).strip()
    if raw.lower().startswith(("file:", "image:", "category:")):
        continue
    base = raw.split("#", 1)[0].strip()
    key = base.casefold()
    if base and key not in seen:
        seen.add(key)
        targets.append(base)
targets.sort()
wiki = Wiki()
mapping = {}
for start in range(0, len(targets), 50):
    batch = targets[start:start + 50]
    data = wiki.site("en").simple_request(
        action="query",
        titles="|".join(batch),
        prop="langlinks",
        lllang="mg",
        lllimit="max",
        redirects="1",
        formatversion="2",
    ).submit()
    pages = data.get("query", {}).get("pages", [])
    normalized = {n["from"]: n["to"] for n in data.get("query", {}).get("normalized", [])}
    redirs = {r["from"]: r["to"] for r in data.get("query", {}).get("redirects", [])}
    by_title = {}
    for page in pages:
        title = page.get("title")
        if not title:
            continue
        ll = page.get("langlinks", [])
        mg = ll[0]["title"] if ll else None
        by_title[title.casefold()] = {
            "en_title": title,
            "mg_title": mg,
            "missing": bool(page.get("missing")),
            "redirect": page.get("redirect"),
        }
    for requested in batch:
        resolved = normalized.get(requested, requested)
        # follow one or more redirects from the API response
        chain = [resolved]
        while resolved in redirs and len(chain) < 5:
            resolved = redirs[resolved]
            chain.append(resolved)
        hit = by_title.get(resolved.casefold())
        mapping[requested] = {
            "resolved_en": resolved,
            "redirect_chain": chain,
            "mg_title": hit["mg_title"] if hit else None,
            "en_exists": bool(hit and not hit["missing"]),
        }
out = {"pinned_at": now(), "source_revision": 1381968535, "mapping": mapping}
open("runs/biol-sex-20261114/evidence-link-targets.json", "w", encoding="utf-8").write(
    json.dumps(out, ensure_ascii=False, indent=2)
)
resolved = sum(1 for v in mapping.values() if v["mg_title"])
print("targets", len(mapping), "with_mg", resolved)
for k, v in mapping.items():
    if v["mg_title"]:
        print("+", k, "->", v["mg_title"])
