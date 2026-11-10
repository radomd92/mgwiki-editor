"""Gather serialized, guarded Wikipedia metadata for this translation job."""
import json
from pathlib import Path

import mwparserfromhell

from mgwiki_editor.core import Wiki

JOB = Path("runs/alina-iraika-20261105")


def main():
    wiki = Wiki()
    code = mwparserfromhell.parse((JOB / "source.wiki").read_text(encoding="utf-8"))
    targets = set()
    images = {"William-Strang-Sindbad-AliBaba-titlepage.JPG"}
    for link in code.filter_wikilinks():
        target = str(link.title).strip()
        if target.lower().startswith(("file:", "image:")):
            images.add(target.split(":", 1)[1])
        elif ":" not in target and not target.startswith("#"):
            targets.add(target.split("#", 1)[0])
    import re
    images.update(re.findall(r"^File:([^|\n]+)", str(code), re.M))
    targets = sorted(targets)
    for start in range(0, len(targets), 50):
        out = JOB / f"links-{start:03}.json"
        if out.exists():
            continue
        result = wiki.site("en").simple_request(
            action="query", prop="langlinks", titles="|".join(targets[start:start+50]),
            lllang="mg", lllimit="max", redirects=1, formatversion=2,
        ).submit()
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    images = sorted(images)
    for start in range(0, len(images), 50):
        out = JOB / f"images-{start:03}.json"
        if out.exists():
            continue
        result = wiki.site("en").simple_request(
            action="query", prop="imageinfo", titles="|".join("File:"+x for x in images[start:start+50]),
            iiprop="canonicaltitle|extmetadata", formatversion=2,
        ).submit()
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    out = JOB / "local-categories.json"
    if not out.exists():
        result = wiki.site("mg").simple_request(
            action="query", prop="info", titles="Sokajy:Literatiora|Sokajy:Literatiora arabo|Sokajy:Angano",
            formatversion=2,
        ).submit()
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
