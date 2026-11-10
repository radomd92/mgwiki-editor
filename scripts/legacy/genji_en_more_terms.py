"""Read-only targeted literary terminology checks, serialized by shared gate."""
from pathlib import Path
from urllib.parse import quote

from mgwiki_editor.core import GuardError, lookup, now, write_json

JOB = Path("runs/genji-en-20261105-utf8")
TERMS = [
    ("monogatari", "tantara"), ("lady-in-waiting", "mpanotrona"),
    ("concertina", "foritra"), ("phonetic", "soratra"),
    ("aristocratic", "andriana"), ("honorific", "fanajana"),
    ("plot", "tantara"), ("prose", "lahateny"),
    ("tanka", "tononkalo"), ("kana", "soratra"),
    ("kanji", "soratra"), ("hiragana", "soratra"),
    ("inflected", "fiovaovana"), ("loanword", "teny"),
    ("statistically significant", "antontanisa"), ("psychological novel", "tantara"),
    ("novice", "mpianatra"), ("nun", "masera"),
    ("ukiyo-e", "sary"), ("sogana", "soratra"),
    ("photoreproduction", "sary"), ("manga", "tantara an-tsary"),
    ("anime", "sarimiaina"), ("opera", "opera"),
    ("braille", "braille"), ("movable type", "pirinty"),
    ("anthology", "angona"), ("regency", "mpisolo"),
]


if __name__ == "__main__":
    directory = JOB / "evidence"
    candidates = {}
    for file in directory.glob("lookup-mg-*.json"):
        import json
        record = json.loads(file.read_text(encoding="utf-8"))
        candidates[record.get("word")] = str(file.relative_to(JOB))
    index = {}
    for term, candidate in TERMS:
        paths = []
        for edition, word in (("en", term), ("mg", candidate)):
            if edition == "mg" and word in candidates:
                paths.append(candidates[word])
                continue
            filename = "lookup-" + edition + "-extra-" + term.replace(" ", "-") + ".json"
            output = directory / filename
            if not output.exists():
                try:
                    result = lookup(edition, word)
                except GuardError as exc:
                    result = {"status": "failed", "edition": edition, "word": word,
                              "retrieved_at": now(), "error": str(exc),
                              "url": "http://192.168.1.155:8000/wiktionary-pages/" + edition + "/" + quote(word)}
                write_json(output, result)
            relative = str(output.relative_to(JOB))
            paths.append(relative)
            if edition == "mg":
                candidates[word] = relative
        index[term] = {"candidate": candidate, "evidence_files": paths}
    write_json(JOB / "extra-terminology-index.json", index)
    print("Additional literary sense checks pinned:", len(index))
