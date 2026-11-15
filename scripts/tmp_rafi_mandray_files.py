"""Image availability evidence (mg repo = Commons) for the sensory-nervous-system fix."""
import json

from mgwiki_editor.core import Wiki, now

JOB = "runs/rafi-mandray-fix-20261115"
files = [
    "Sary:restingStateModels.jpg",
    "Sary:1212 Sensory Neuron Test Water.jpg",
    "Sary:Eye iris.jpg",
    "Sary:Earcov.JPG",
    "Sary:Hump nose2.jpg",
    "Sary:Tongue.agr.jpg",
    "Sary:Sense organ diseases world map - DALY - WHO2002.svg",
]
wiki = Wiki()
data = wiki.site("mg").simple_request(
    action="query",
    titles="|".join(files),
    prop="imageinfo",
    iiprop="url|size|mime|user|timestamp",
    formatversion="2",
).submit()
pages = data.get("query", {}).get("pages", [])
records = []
for page in pages:
    info = (page.get("imageinfo") or [{}])[0]
    records.append(
        {
            "title": page.get("title"),
            "missing": bool(page.get("missing")),
            "mime": info.get("mime"),
            "width": info.get("width"),
            "height": info.get("height"),
            "size": info.get("size"),
            "url": info.get("url"),
            "uploader": info.get("user"),
            "timestamp": info.get("timestamp"),
        }
    )
out = {
    "generated_at": now(),
    "checked_via": "mg.wikipedia.org action=query prop=imageinfo (shared repo)",
    "requested": len(files),
    "present": sum(1 for r in records if not r["missing"]),
    "files": records,
}
json.dump(out, open(f"{JOB}/evidence/media-existence-check-v2.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({"present": out["present"], "requested": out["requested"]}))
for r in records:
    if r["missing"]:
        print("MISSING", r["title"])
