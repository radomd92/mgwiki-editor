"""Coordinator assembly of completed section fragments; no network or approval."""
import json
import re
from pathlib import Path

import mwparserfromhell as mw

from genji_en_native import JOB, citation, map_links, native_templates
from mgwiki_editor.core import write_json


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def accent_expansions():
    result = {}
    data = load(JOB / "evidence/reference-templates.json")
    for page in data["response"]["query"]["pages"]:
        key = page["title"].split(":", 1)[1].lower()
        if key == "nkbd":
            continue
        source = page["revisions"][0]["slots"]["main"]["content"].split("<noinclude>")[0]
        source = re.sub(r"\{\{\{([\w-]+)\|\}\}\}", lambda m: ("224" if key.startswith("zenkoku") else "275")
                        if m[1] == "p" else "", source)
        template = mw.parse(source).filter_templates()[0]
        result[key] = citation(template)
    return result


def run():
    plan = load(JOB / "section-plan.json")
    mapping = load(JOB / "link-map.json")
    expansions = accent_expansions()
    pieces, notes, vocabulary, decisions = [], [], [], []
    for item in plan:
        directory = Path(item["directory"])
        for filename in ("section.wiki", "notes.wiki", "vocabulary.json"):
            if not (directory / filename).is_file():
                raise RuntimeError("Missing assigned section artifact: " + str(directory / filename))
        text = (directory / "section.wiki").read_text(encoding="utf-8")
        text = native_templates(text, expansions)
        text, local_decisions = map_links(text, mapping)
        decisions += [item["id"] + ": " + d for d in local_decisions]
        pieces.append(text.strip())
        notes.append("\n== Fanolorana " + item["id"] + " ==\n" + (directory / "notes.wiki").read_text(encoding="utf-8"))
        records = load(directory / "vocabulary.json")
        if isinstance(records, dict):
            records = records.get("terms", [])
        for record in records:
            record["section_id"] = item["id"]
            files = record.setdefault("evidence_files", [])
            source_file = "sections/" + item["id"] + "/source.wiki"
            if source_file not in files:
                files.append(source_file)
            vocabulary.append(record)
        item["status"] = "integrated_pending_whole_article_review"
    text = "\n\n".join(pieces) + "\n"
    # Preserve literal source bibliographic identifiers without magic-link categories.
    # Existing nowiki spans are excluded by parsing, rather than regex on the whole draft.
    code = mw.parse(text)
    for node in list(code.filter_text(recursive=False)):
        changed = re.sub(r"\bISBN ([0-9Xx-]+)", r"<nowiki>ISBN \1</nowiki>", str(node))
        if changed != str(node):
            code.replace(node, changed)
    text = str(code)
    (JOB / "draft.wiki").write_text(text, encoding="utf-8")
    (JOB / "section-handoffs.wiki").write_text("\n".join(notes), encoding="utf-8")
    (JOB / "link-decisions.wiki").write_text("= Fanapahan-kevitra momba ny rohy =\n" + "\n".join("* " + d for d in decisions)+"\n", encoding="utf-8")
    write_json(JOB / "integrated-section-plan.json", plan)
    write_json(JOB / "vocabulary.json", vocabulary)
    print("Merged", len(plan), "sections;", len(text.encode("utf-8")), "bytes;", len(vocabulary), "vocabulary records")
    print("Remaining templates:", [str(t.name) for t in mw.parse(text).filter_templates()])


if __name__ == "__main__":
    run()
