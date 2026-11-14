"""Existence-only check for assembly-critical templates."""
import json
from mgwiki_editor.core import Wiki, now

names = [
    "Template:Rp", "Template:GBurl", "Template:Sfnref", "Template:Snd",
    "Template:!", "Template:Reflist", "Template:Refbegin", "Template:Refend",
    "Template:Biological sex", "Template:Div col end", "Template:Cite encyclopedia",
    "Template:Multiple image", "Template:Main", "Template:Further",
    "Template:See also", "Template:Lahatsoratra antsipirihany",
    "Template:Sfn whitelist", "Template:Citation",
]
wiki = Wiki()
data = wiki.site("mg").simple_request(
    action="query", titles="|".join(names), prop="info", formatversion="2"
).submit()
out = {"pinned_at": now(), "requested": names, "response": data}
open("runs/biol-sex-20261114/evidence-template-info-v2.json", "w", encoding="utf-8").write(
    json.dumps(out, ensure_ascii=False, indent=2)
)
for page in data.get("query", {}).get("pages", []):
    print(page.get("title"), "missing=" + str(page.get("missing", False)))
