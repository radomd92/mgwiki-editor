"""Pin mgwiki file availability/license metadata for source images."""
import json
from mgwiki_editor.core import Wiki, now

files = [
    "Sexual cycle.svg",
    "Hoverflies mating midair.jpg",
    "Mature flower diagram.svg",
    "Pinus nigra cone.jpg",
    "Pine cones, immature male.jpg",
    "Monoecy_dioecy_en.svg",
    "Evolsex-dia2a.svg",
    "Drosophila XY sex-determination.svg",
    "Chalkhill blue butterflies (Polyommatus coridon) mating 1.jpg",
    "Common clubtail (Gomphus vulgatissimus) male Estonia.jpg",
    "Ceratopteris pteridoides kz02.jpg",
    "Ocellaris clownfish.JPG",
    "Crocoparc Naissance des bébés.jpg",
    "Anisogamy.svg",
    "Isogamy.svg",
    "Male and female pheasant.jpg",
    "Beo-2.jpg",
    "Shiitake mushroom.jpg",
]
wiki = Wiki()
data = wiki.site("mg").simple_request(
    action="query",
    titles="|".join("File:" + f for f in files),
    prop="imageinfo",
    iiprop="url|timestamp|sha1|extmetadata",
    formatversion="2",
).submit()
out = {"pinned_at": now(), "requested": files, "response": data}
open("runs/biol-sex-20261114/evidence-file-metadata.json", "w", encoding="utf-8").write(
    json.dumps(out, ensure_ascii=False, indent=2)
)
for page in data.get("query", {}).get("pages", []):
    ii = (page.get("imageinfo") or [{}])[0]
    meta = ii.get("extmetadata", {})
    print(
        page.get("title"),
        "missing=" + str(page.get("missing", False)),
        "repo=" + str(ii.get("imagerepository") or ii.get("repository") or ""),
        "license=" + str(meta.get("LicenseShortName", {}).get("value", "")),
    )
