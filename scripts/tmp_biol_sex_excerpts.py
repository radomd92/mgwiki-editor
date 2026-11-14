"""Pin enwiki excerpt expansions for transcluded source sections."""
import json
from mgwiki_editor.core import Wiki, now

wiki = Wiki()
out = {}
for key, title, text in [
    ("sex-ratio", "Biological sex", "{{Excerpt|Sex ratio|files=-Sex ratio total population 2020.svg}}"),
    ("sexual-characteristics", "Biological sex", "{{excerpt|Sexual characteristics|templates=-more citations needed}}"),
]:
    data = wiki.expand_template("en", title, text)
    out[key] = {"request": text, "response": data, "pinned_at": now()}
open("runs/biol-sex-20261114/evidence-excerpt-expansions.json", "w", encoding="utf-8").write(
    json.dumps(out, ensure_ascii=False, indent=2)
)
for key, value in out.items():
    wt = value["response"]["expandtemplates"]["wikitext"]
    print(key, len(wt), wt[:400].replace("\n", " "))
