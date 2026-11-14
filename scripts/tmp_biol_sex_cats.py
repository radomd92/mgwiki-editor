"""Bounded category search for Malagasy category naming evidence."""
import json
from mgwiki_editor.core import Wiki, now

terms = ["biôlôjia", "fananahana", "firaisana ara-nofo", "lahy sy vavy", "zavamananaina"]
wiki = Wiki()
out = {"pinned_at": now(), "queries": []}
for term in terms:
    data = wiki.site("mg").simple_request(
        action="query", list="search", srsearch=term, srnamespace=14,
        srlimit=15, formatversion=2,
    ).submit()
    hits = [h["title"] for h in data.get("query", {}).get("search", [])]
    out["queries"].append({"term": term, "hits": hits})
    print("##", term)
    for hit in hits:
        print("  ", hit)
open("runs/biol-sex-20261114/evidence-category-search.json", "w", encoding="utf-8").write(
    json.dumps(out, ensure_ascii=False, indent=2)
)
