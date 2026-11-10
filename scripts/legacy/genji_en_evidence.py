"""Pin sequential Genji link/file/terminology evidence through Wiki only."""
import json
import shutil
from pathlib import Path

import mwparserfromhell as mw

from mgwiki_editor.core import GuardError, Wiki, lookup, now, write_json

JOB = Path("runs/genji-en-20261105-utf8")


def run():
    source = (JOB / "source.wiki").read_text(encoding="utf-8")
    code = mw.parse(source)
    inventory = [{"target": str(x.title), "label": str(x.text or x.title)}
                 for x in code.filter_wikilinks()]
    write_json(JOB / "source-link-inventory.json", inventory)
    targets = sorted({x["target"].split("#")[0].replace("_", " ") for x in inventory
                      if ":" not in x["target"] and x["target"]})
    files = sorted({x["target"].split(":", 1)[1] for x in inventory
                    if x["target"].lower().startswith(("file:", "image:"))}
                   | {"Genji emaki 01003 002.jpg"})
    wiki = Wiki()
    directory = JOB / "evidence"
    directory.mkdir(exist_ok=True)
    mapping = {}
    for start in range(0, len(targets), 45):
        output = directory / f"links-{start:03d}.json"
        if not output.exists():
            data = wiki.site("en").simple_request(
                action="query", prop="langlinks", titles="|".join(targets[start:start+45]),
                lllang="mg", lllimit="max", formatversion=2,
            ).submit()
            write_json(output, {"retrieved_at": now(), "response": data})
            if "continue" in data:
                raise GuardError("Pagination requires targeted continuation; evidence retained")
        data = json.loads(output.read_text(encoding="utf-8"))["response"]
        for page in data["query"]["pages"]:
            mapping[page["title"]] = {
                "mg": page.get("langlinks", [{}])[0].get("title"),
                "missing": page.get("missing", False),
                "evidence_file": str(output.relative_to(JOB)),
            }
        for item in data.get("query", {}).get("normalized", []):
            if item["to"] in mapping:
                mapping[item["from"]] = mapping[item["to"]]
    write_json(JOB / "link-map.json", mapping)
    for filename, lang, params in [
        ("files.json", "en", dict(prop="imageinfo", titles="|".join("File:"+x for x in files),
                                  iiprop="timestamp|extmetadata")),
        ("categories.json", "mg", dict(prop="info", titles="Sokajy:Literatiora japoney|Sokajy:Boky|Sokajy:Tantara foronina|Sokajy:Literatiora")),
        ("reference-templates.json", "en", dict(prop="revisions", rvprop="content", rvslots="main",
             titles="Template:Zenkoku Accent Jiten|Template:Shinmeikai Nihongo Accent Jiten 2nd Edition|Template:NKBD")),
        ("prior-spaced-title.json", "mg", dict(prop="revisions", rvprop="ids|content", rvslots="main",
             titles="Tantaran' i Genji|Mpikambana:Bot-Jagwar/Tantaran' i Genji")),
    ]:
        output = directory / filename
        if not output.exists():
            data = wiki.site(lang).simple_request(action="query", formatversion=2, **params).submit()
            write_json(output, {"retrieved_at": now(), "response": data})
    shutil.copyfile("data/country-names.json", JOB / "country-names.json")
    # These are sense checks, not evidence for article facts.
    terms = [
        ("courtier", "tandapa"), ("concubine", "vadikely"),
        ("regent", "mpisolo"), ("vernacular", "fiteny"),
        ("manuscript", "sora-tanana"), ("homophone", "teny"),
        ("antihero", "mahery fo"), ("allusion", "fanoharana"),
        ("anachronism", "vanim-potoana"), ("calligraphy", "soratra"),
        ("feudal", "feodaly"), ("scroll", "horonana"),
    ]
    for english, malagasy in terms:
        for edition, word in (("en", english), ("mg", malagasy)):
            output = directory / f"lookup-{edition}-{english}.json"
            if output.exists():
                continue
            try:
                result = lookup(edition, word)
            except GuardError as exc:
                result = {"status": "failed", "edition": edition, "word": word,
                          "retrieved_at": now(), "error": str(exc)}
            write_json(output, result)
    print("Evidence pinned:", len(targets), "topics;", len(files), "files")


if __name__ == "__main__":
    run()
