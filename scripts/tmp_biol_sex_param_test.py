"""Check local citation-template parameter rendering for author fields."""
import json
from mgwiki_editor.core import Wiki, now

text = """{{cite book|vauthors=Mills A|title=Test|year=2018}}
{{cite book|author=Mills A|title=Test|year=2018}}
{{cite book|last=Mills|first=A|title=Test|year=2018}}
{{cite journal|vauthors=Smith J, Jones K|title=Test|journal=J|year=2020}}
{{cite journal|author=Smith J, Jones K|title=Test|journal=J|year=2020}}
{{cite journal|last=Smith|first=J|last2=Jones|first2=K|title=Test|journal=J|year=2020}}
"""
wiki = Wiki()
data = wiki.expand_template("mg", "Mpikambana:Bot-Jagwar/Lahy sy vavy ara-biôlôjika", text)
out = {"pinned_at": now(), "response": data}
open("runs/biol-sex-20261114/evidence-template-param-test.json", "w", encoding="utf-8").write(
    json.dumps(out, ensure_ascii=False, indent=2)
)
print(data["expandtemplates"]["wikitext"])
