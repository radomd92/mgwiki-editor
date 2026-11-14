"""Bounded en->mg link mapping and mg title existence evidence for the Tsiro job."""
import json
import re

from mgwiki_editor.core import Wiki, now

JOB = "runs/tsiro-20261114"
text = open(f"{JOB}/source.wiki", encoding="utf-8").read()
prose = re.sub(r"<ref[^>]*?/>", "", text)
prose = re.sub(r"<ref[^>]*>.*?</ref>", "", prose, flags=re.S)
targets = []
seen = set()
for m in re.finditer(r"\[\[([^\]\|#]+)(?:#[^\]\|]*)?(?:\|[^\]]*)?\]\]", prose):
    raw = m.group(1).strip()
    if raw.lower().startswith(("file:", "image:", "category:")):
        continue
    key = raw.casefold()
    if raw and key not in seen:
        seen.add(key)
        targets.append(raw)
targets.sort()
wiki = Wiki()
mapping = {}
for start in range(0, len(targets), 50):
    batch = targets[start : start + 50]
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
        if "title" not in page:
            continue
        ll = page.get("langlinks", [])
        by_title[page["title"].casefold()] = {
            "en_title": page["title"],
            "mg_title": ll[0]["title"] if ll else None,
            "missing": bool(page.get("missing")),
        }
    for requested in batch:
        resolved = normalized.get(requested, requested)
        hit = by_title.get(resolved.casefold())
        mapping[requested] = {
            "resolved_en": resolved,
            "mg_title": hit["mg_title"] if hit else None,
            "source_missing": hit["missing"] if hit else None,
        }
out = {
    "language": "en",
    "prop": "langlinks-mg",
    "generated_at": now(),
    "source": f"{JOB}/source.wiki",
    "requested": targets,
    "mapping": mapping,
    "raw_response_pages": None,
}
json.dump(out, open(f"{JOB}/evidence/langlinks-en-mg.json", "w"), ensure_ascii=False, indent=2)

# Malagasy title existence for existing sandbox link targets.
sandbox = open(f"{JOB}/sandbox.wiki", encoding="utf-8").read()
mg_targets = []
seen = set()
for m in re.finditer(r"\[\[([^\]\|#]+)(?:#[^\]\|]*)?(?:\|[^\]]*)?\]\]", sandbox):
    raw = m.group(1).strip()
    if raw.lower().startswith(("file:", "sokajy:", "category:")):
        continue
    key = raw.casefold()
    if raw and key not in seen:
        seen.add(key)
        mg_targets.append(raw)
mg_targets.sort()
pages_all = []
for start in range(0, len(mg_targets), 50):
    batch = mg_targets[start : start + 50]
    data = wiki.site("mg").simple_request(
        action="query",
        titles="|".join(batch),
        prop="info",
        redirects="1",
        formatversion="2",
    ).submit()
    pages_all.extend(data.get("query", {}).get("pages", []))
json.dump(
    {
        "language": "mg",
        "prop": "info",
        "generated_at": now(),
        "requested": mg_targets,
        "pages": pages_all,
    },
    open(f"{JOB}/evidence/mg-title-info.json", "w"),
    ensure_ascii=False,
    indent=2,
)
print("targets", len(targets), "mg_targets", len(mg_targets))
print("mapped", sum(1 for v in mapping.values() if v["mg_title"]))
