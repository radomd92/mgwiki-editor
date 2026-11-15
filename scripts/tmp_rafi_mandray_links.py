"""Bounded en->mg link mapping + mg title existence evidence for the sensory-nervous-system fix."""
import json
import re

from mgwiki_editor.core import Wiki, now

JOB = "runs/rafi-mandray-fix-20261115"
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
        resolved = redirs.get(resolved, resolved)
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
    "source_revision": json.load(open(f"{JOB}/job.json", encoding="utf-8"))["source"]["revision_id"],
    "requested_count": len(targets),
    "mapping": mapping,
    "note": "Langlink evidence only; topic identity and label wording still need review.",
}
json.dump(out, open(f"{JOB}/evidence/source-to-mg-links.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

candidates = [
    # hatnote targets
    "Mpandray fanaitairana ara-pahatsapana",
    "Mpandray fanaitairana simika",
    "Sela mpandray hazavana",
    "Mpandray tsindry na fiovan' ny bika",
    "Mpandray fiovan' ny hafanana",
    "Mpandray fanaitairana mety hanimba tambatsela",
    # see also targets
    "Fampitambarana vaovao avy amin' ny fahatsapana samihafa",
    "Fiovan' ny famalian' ny nerônina rehefa maharitra na miverimberina ny fanaitairana",
    "Fanehoana vaovao amin' ny alalan' ny fiasan' ny nerônina",
    "Fitaovana mamantatra fiovana ara-batana na simika",
    "Fanitarana na fanatsarana ny fahafahana mandray fahatsapana",
    "Fandalinana ny fiasan' ny rafi-pitatitra amin' ny fandraisana sy fanodinana fahatsapana",
    "Rafitra mandray sy mandamina fahatsapana ao amin' ny trondro",
    # disease labels
    "Ambliôpia",
    "Anakozia",
    "Fahajambana amin' ny loko",
    "Marenina",
    # concept labels used in prose
    "Atidoha",
    "Aristôty",
    "Sofina",
    "Orona",
    "Lela",
    "Masomboly",
    "Maso",
    "Fanaintainana",
    "Taratra elektrômanetika",
    "Angôvo",
    "Ôksizenina",
    "Tsindry (fizika)",
    "Mari-pana",
    "Biby mampinono",
    "Relativité general",
    "Flip-flop",
    # categories
    "Sokajy:Fahasalamana",
    "Sokajy:Rafi-pitatitra",
    "Sokajy:Fahatsapana",
    "Sokajy:Biolojia",
    "Sokajy:Siansa",
    "Sokajy:Anatômia",
    "Sokajy:Neorôsiansa",
]
titles = [t for t in candidates if not t.startswith("Sokajy:")]
cats = [t for t in candidates if t.startswith("Sokajy:")]

def batch_check(site, names):
    result = {}
    for start in range(0, len(names), 50):
        batch = names[start : start + 50]
        data = site.simple_request(
            action="query", titles="|".join(batch), formatversion="2", redirects="1"
        ).submit()
        q = data.get("query", {})
        normalized = {n["from"]: n["to"] for n in q.get("normalized", [])}
        redirs = {r["from"]: r["to"] for r in q.get("redirects", [])}
        pages = q.get("pages", [])
        by_title = {p.get("title", "").casefold(): p for p in pages if "title" in p}
        for requested in batch:
            resolved = normalized.get(requested, requested)
            resolved = redirs.get(resolved, resolved)
            hit = by_title.get(resolved.casefold())
            result[requested] = {
                "resolved": resolved if hit else None,
                "missing": None if hit is None else bool(hit.get("missing")),
            }
    return result

site = wiki.site("mg")
check = {
    "generated_at": now(),
    "checked_on": "mg.wikipedia.org",
    "mainspace": batch_check(site, titles),
    "categories": batch_check(site, cats),
    "note": "Existence/redirect evidence only; topic identity and label quality still need review.",
}
json.dump(check, open(f"{JOB}/evidence/link-targets-mg.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({"links": out["requested_count"], "with_mg": sum(1 for v in mapping.values() if v["mg_title"]),
                  "checked_titles": len(titles), "checked_categories": len(cats)}, ensure_ascii=False))
