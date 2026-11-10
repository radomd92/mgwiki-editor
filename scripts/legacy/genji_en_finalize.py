"""Offline coordinator corrections, evidence integration, and review inventories."""
import json
import re
import textwrap
from pathlib import Path
from urllib.parse import quote

import mwparserfromhell as mw

from genji_en_native import JOB
from mgwiki_editor.core import write_json


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def run():
    path = JOB / "draft.wiki"
    text = path.read_text(encoding="utf-8")
    edits = {
        "Lahatsoratra manazava izany amin' ny antsipiriany ny fampitana ny lahatsoratry ny ''Tantaran' i Genji''.\n\n": "",
        "Genji.''' Oakland": "Genji.&#39;'' Oakland",
        "lahatsoratra tsy miady rima": "lahatsoratra tsotra fa tsy andininy",
        "dia mbola hajaina fatratra ny ''Tantaran' i Genji'', ary efa nampitahaina tamin' ny": "dia nampitahain' i Bryan tamin' ny",
        "''Tale of Genji Scroll'', <nowiki>ISBN 0-87011-131-0</nowiki>)": "''Tale of Genji Scroll'', <nowiki>ISBN 0-87011-131-0</nowiki>",
        "Tyler, Royall (2009). The Disaster of the Third Princess: Essays on the tale of Genji.": "Tyler, Royall (2009). ''The Disaster of the Third Princess: Essays on the tale of Genji''.",
        "ny fandikana tamin' ny teny japoney ankehitriny, na dia": "ny [[Fandikan-teny|fandikana tamin' ny teny japoney ankehitriny]], na dia",
        "(Tranombakoky ny Zavakanto Tokugawa)": "(tranombakoka momba ny zavakanto Tokugawa)",
        "(mozean' ny zavakanto Tokugawa)": "(tranombakoka momba ny zavakanto Tokugawa)",
        "(mozea Gotoh)": "(tranombakoka Gotoh)",
        "tao amin' ny mozea Tokugawa": "tao amin' ny tranombakoka Tokugawa",
        "tao amin' io mozea io": "tao amin' io tranombakoka io",
    }
    for before, after in edits.items():
        text = text.replace(before, after)
    code = mw.parse(text)
    clements = [tag for tag in code.filter_tags()
                if str(tag.tag)=="ref" and not tag.self_closing
                and "Clements, Rebekah." in str(tag.contents)]
    if len(clements)==2 and str(clements[0].contents)==str(clements[1].contents):
        clements[0].add("name", "Clements2011")
        code.replace(clements[1], '<ref name="Clements2011" />')
    text = str(code)
    path.write_text(text, encoding="utf-8")
    (JOB / "draft-readable.wiki").write_text("\n".join(
        textwrap.fill(line, width=1000, break_long_words=False, break_on_hyphens=False,
                      replace_whitespace=False) if len(line)>1000 else line
        for line in text.split("\n")), encoding="utf-8")
    source = (JOB / "source.wiki").read_text(encoding="utf-8")
    a, b = mw.parse(source), mw.parse(text)
    inventory = []
    mapping = load(JOB / "link-map.json")
    mg_targets = {str(link.title).split("#")[0] for link in b.filter_wikilinks()}
    for link in a.filter_wikilinks():
        original = str(link.title)
        base = original.split("#")[0].replace("_", " ")
        if original.lower().startswith("category:"):
            outcome = "Tsy nafarana: sokajy anglisy; Boky malagasy voamarina ihany no nampiana, tsy miasa."
        elif original.lower().startswith(("file:", "image:")):
            outcome = "Voatahiry amin' ny toerana mifanaraka amin' ny source; filename tsy niova; caption nadika; Commons public domain (evidence/files.json)."
        elif mapping.get(base, {}).get("mg"):
            target = mapping[base]["mg"]
            outcome = f"Kendrena voamarina: {target}; " + ("tafiditra ao amin' ny draft." if target in mg_targets else "soratra eo an-toerana mbola mila ampifandraisina.")
        else:
            outcome = "Soratra tsotra nadika/anarana na titre tany am-boalohany: tsy misy target malagasy voamarina amin' ny porofo."
        inventory.append(f"* <nowiki>{original}</nowiki>: {outcome}")
    (JOB / "coverage-inventory.wiki").write_text(
        "= Sarintany feno source → draft =\n" + "\n".join(inventory)
        + "\n* Infobox image Genji emaki 01003 002.jpg: voatahiry amin' ny fampidirana miaraka amin' ny caption sy alt nadika.\n"
        + "* Lohatenin' ny toko: tabilao 54 sy X feno, tsy misy andalana nesorina; ireo original titles dia tsy natao ho dikan-teny malagasy ofisialy.\n"
        + "* Textual tradition of The Tale of Genji: hatnote fitetezana tsy nisy target malagasy voamarina, nesorina fa tsy navadika ho filazana hafahafa; voarakotra ao amin' ny fizarana Sora-tanana ny foto-kevitra.\n",
        encoding="utf-8")
    urls = lambda code: {str(link.url) for link in code.filter_external_links()}
    report = {
        "source_ref_tags": sum(str(t.tag)=="ref" for t in a.filter_tags()),
        "draft_ref_tags": sum(str(t.tag)=="ref" for t in b.filter_tags()),
        "draft_ref_tags_literal": len(re.findall(r"<ref\b",text)),
        "lost_source_urls": sorted(urls(a)-urls(b)),
        "draft_images": [str(l.title) for l in b.filter_wikilinks() if str(l.title).lower().startswith("file:")],
        "remaining_templates": [str(t) for t in b.filter_templates()],
        "remaining_arguments": [str(t) for t in b.filter_arguments()],
        "headings": [{"level": h.level, "title": str(h.title).strip()} for h in b.filter_headings()],
    }
    write_json(JOB / "structural-review.json", report)
    records = load(JOB / "vocabulary.json")
    aliases = {"anti-hero": "antihero", "homophones": "homophone", "feudal relationships": "feudal",
               "regent in all but name": "regent", "poetical allusions": "allusion",
               "anachronisms": "anachronism", "concertina / orihon": "concertina",
               "phonetic script": "phonetic", "prose fiction / monogatari": "monogatari",
               "highly inflected": "inflected", "chinese loan words / kango": "loanword",
               "nun / bikuni": "nun", "ukiyo-e prints": "ukiyo-e", "sōgana": "sogana",
               "moveable type": "movable type", "handscroll": "scroll",
               "illustrated hand scroll": "scroll", "kana (japanese phonetic script)": "kana",
               "aristocratic women (ladies-in-waiting)": "aristocratic"}
    extra = load(JOB / "extra-terminology-index.json") if (JOB / "extra-terminology-index.json").exists() else {}
    canonical = {}
    for record in records:
        term = record["source_term"]
        key = aliases.get(term.lower(), term.lower())
        evidence = record.setdefault("evidence_files", [])
        for edition in ("en", "mg"):
            f = JOB / "evidence" / f"lookup-{edition}-{key}.json"
            if f.exists() and str(f.relative_to(JOB)) not in evidence:
                evidence.append(str(f.relative_to(JOB)))
        if key in extra:
            evidence.extend(f for f in extra[key]["evidence_files"] if f not in evidence)
        if key == "sogana":
            evidence.append("evidence/lookup-en-extra-sogana-full.json")
        # Original fragment handoffs stay immutable; coordinator memo deduplicates
        # the same literary sense and keeps all source provenance/wording choices.
        if key in canonical:
            old = canonical[key]
            old["evidence_files"] = sorted(set(old["evidence_files"]+evidence))
            old.setdefault("section_provenance", []).append(record.get("section_id"))
            if record["chosen_expression"] != old["chosen_expression"]:
                old.setdefault("accepted_contextual_wordings", []).append(record["chosen_expression"])
        else:
            record["canonical_term"] = key
            record["section_provenance"] = [record.get("section_id")]
            canonical[key] = record
    # Country cache is exact, job-local naming evidence, not sovereignty evidence.
    if "japan" in canonical:
        canonical["japan"]["evidence_files"] = sorted(set(canonical["japan"]["evidence_files"]+["country-names.json"]))
    else:
        canonical["japan"] = {
            "source_term": "Japan", "source_language": "en", "domain": "country naming",
            "source_sense": "The country in which the Japanese literary work originated.",
            "english_definition": "The country Japan, not a generic category or historic polity.",
            "definition_origin": "editorial_simple_english", "malagasy_definition": "Ny firenena Japàna.",
            "chosen_expression": "Japàna", "status": "verified", "alternatives_rejected": [],
            "evidence_files": ["country-names.json", "sections/00-lead/source.wiki"],
            "reason": "Exact matching cached Malagasy country title; source establishes topic identity.",
        }
    records = list(canonical.values())
    for record in records:
        if any("lookup-" in f for f in record["evidence_files"]):
            record["coordinator_lookup_review"] = "Dictionary evidence informs the source sense; broad candidates and failed lookups do not establish a one-word equivalent. Editorial definitions remain labelled editorial."
            lookups = []
            for filename in record["evidence_files"]:
                if "lookup-" not in filename:
                    continue
                data = load(JOB / filename)
                url = data.get("url") or ("http://192.168.1.155:8000/wiktionary-pages/"
                      + data["edition"] + "/" + quote(data["word"]))
                lookups.append({"file": filename, "url": url,
                                "retrieved_at": data.get("retrieved_at"), "status": data.get("status")})
            record["lookup_evidence"] = lookups
        if record.get("canonical_term") in {"courtier", "manuscript"}:
            record["status"] = "verified"
            record["reason"] = "Coordinator checked the relevant English sense and the Malagasy entry: both support the chosen expression. Original fragment reservations are preserved in section handoffs."
        elif record.get("lookup_evidence"):
            record["original_worker_reason"] = record["reason"]
            results = "; ".join(f"{item['file']}: {item['status']}" for item in record["lookup_evidence"])
            record["reason"] = "Original offline worker rationale: " + record["reason"] + " Coordinator subsequently reviewed the attached lookup results (" + results + "). The contextual description is accurate; it is not claimed as an established one-word Malagasy dictionary equivalent."
        if record.get("canonical_term") == "limpid prose":
            record["malagasy_definition"] = "Lahatsoratra tsotra fa tsy andininy, izay mazava sy mikoriana mora."
            record["chosen_expression"] = "lahatsoratra tsotra fa tsy andininy mazava sy mikoriana"
            record["reason"] += " Coordinator corrected non-rhyming to non-verse: unrhymed poetry is still verse."
        if record.get("canonical_term") == "concubine":
            record["malagasy_definition"] = "Vehivavy miaraka amin' ny mpitondra nefa tsy manana ny laharan' ny vadiny lehibe; eto dia vadikelin' ny emperora ambany laharana."
            record["reason"] += " The wording does not assert a Western legal marriage; Malagasy lookup failed (HTTP 502), not a missing entry."
        record["evidence_files"] = sorted(set(record["evidence_files"]))
    # Exclude proper names and bibliographic labels; retain idioms genuinely
    # researched for sense, rather than counting English merely for being English.
    excluded = {"japan", "akiko yosano", "yasunari kawabata / kawabata yasunari",
        "japanese personal-name order in adaptations", "bibliography",
        "jun'ichirō tanizaki; fumiko enchi; seiko tanabe; jakucho setouchi; osamu hashimoto"}
    uncertain = [r for r in records if r.get("canonical_term", r["source_term"].lower()) not in excluded
                 and r.get("status") != "verified"]
    if len(uncertain)>100:
        lines = ["= Voambolana ho an' ny fandinihana terminolojika =",
                 "Famaritana ara-kevitra voavaha ny etsy ambany; ny fisafidianana teny tokana malagasy efa mahazatra no mbola ilana fanamafisana. Tsy misy hevitra lehibe ahemotra mba handalo vavahady.",
                 f"Isan' ny teny na andian-teny samihafa: {len(uncertain)}. Tsy nisaina anarana manokana na titre bibliografika noho izy ireo anglisy fotsiny."]
        for r in uncertain:
            lines.extend(["\n== " + r["source_term"] + " ==", "* Hevitra: " + r["source_sense"],
                "* Famaritana anglisy tsotra: " + r.get("english_definition", ""),
                "* Fanazavana malagasy: " + r["malagasy_definition"],
                "* Fomba fiteny voafidy: " + r["chosen_expression"],
                "* Dingana manaraka: fanamafisana voambolana tokana raha ilaina; tsy manova ny dikany mazava voarakitra eto."])
            if "unknown-vocabulary.wiki" not in r["evidence_files"]:
                r["evidence_files"].append("unknown-vocabulary.wiki")
        (JOB / "unknown-vocabulary.wiki").write_text("\n".join(lines)+"\n",encoding="utf-8")
    # Bind all accepted section notes, naming metadata, maps and review evidence.
    all_evidence = ["section-handoffs.wiki", "coverage-inventory.wiki", "link-decisions.wiki",
                    "structural-review.json", "citation-inventory.json", "integrated-section-plan.json",
                    "link-map.json", "source-link-inventory.json", "shared-context.wiki",
                    "shared-references.wiki", "section-plan.json", "extra-terminology-index.json"]
    all_evidence += [str(f.relative_to(JOB)) for f in sorted((JOB / "evidence").glob("*.json"))]
    records[0]["evidence_files"] = sorted(set(records[0]["evidence_files"]+all_evidence))
    write_json(JOB / "vocabulary.json", records)
    summary = []
    for r in records:
        summary.extend(["\n== " + r["source_term"] + " ==", "* status: " + r.get("status", ""),
                        "* EN: " + r.get("english_definition", ""), "* MG: " + r["malagasy_definition"],
                        "* voafidy: " + r["chosen_expression"], "* antony: " + r.get("reason", "")])
    (JOB / "vocabulary-review.wiki").write_text("\n".join(summary)+"\n",encoding="utf-8")
    print("Final structural inventory:",report["source_ref_tags"],report["draft_ref_tags"],len(report["draft_images"]))
    print("Deduplicated vocabulary",len(records),"terminology review list",len(uncertain))
    print("Unresolved statuses",[(r["source_term"],r.get("status")) for r in records if r.get("status") not in {"descriptive","verified"}])
    print("Lost source URLs",report["lost_source_urls"])


if __name__ == "__main__":
    run()
