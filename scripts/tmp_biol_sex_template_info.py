"""Existence-only check for local templates (parameter support still needs review)."""
import json
from mgwiki_editor.core import Wiki, now

names = [
    "Template:Cite book", "Template:Cite journal", "Template:Cite web", "Template:Cite news",
    "Template:Cite encyclopedia", "Template:Citation", "Template:Références", "Template:Reflist",
    "Template:Main", "Template:Further", "Template:See also", "Template:Multiple image",
    "Template:Div col", "Template:Div col end", "Template:Authority control",
    "Template:Sister project links", "Template:Portal bar", "Template:Spoken Wikipedia",
    "Template:Lahatsoratra antsipirihany",
]
wiki = Wiki()
data = wiki.site("mg").simple_request(
    action="query", titles="|".join(names), prop="info", formatversion="2"
).submit()
out = {"pinned_at": now(), "response": data}
open("runs/biol-sex-20261114/evidence-template-info.json", "w", encoding="utf-8").write(
    json.dumps(out, ensure_ascii=False, indent=2)
)
for page in data.get("query", {}).get("pages", []):
    print(page.get("title"), "missing=" + str(page.get("missing", False)))
