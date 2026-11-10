"""Offline, loss-accounted citation/template and link adaptation for Genji."""
import json
import re
from pathlib import Path

import mwparserfromhell as mw

JOB = Path("runs/genji-en-20261105-utf8")


def param(template, key, default=""):
    return str(template.get(key).value).strip() if template.has(key) else default


def italics(text):
    if not text:
        return ""
    inner = text.replace("''", "")
    if inner.startswith("'"):
        inner = "&#39;" + inner[1:]
    if inner.endswith("'"):
        inner = inner[:-1] + "&#39;"
    return "''" + inner + "''"


def citation(template):
    """Render literal source bibliographic metadata; never resolve a source URL."""
    fields = {str(p.name).strip().lower(): str(p.value).strip() for p in template.params
              if str(p.value).strip()}
    used = set()

    def take(key):
        used.add(key)
        return fields.get(key, "")

    authors = []
    if fields.get("author"):
        authors.append(take("author"))
    if fields.get("last") or fields.get("first"):
        authors.append(", ".join(x for x in (take("last"), take("first")) if x))
    for number in range(1, 10):
        suffix = str(number)
        if fields.get("last"+suffix) or fields.get("first"+suffix):
            authors.append(", ".join(x for x in (take("last"+suffix), take("first"+suffix)) if x))
        elif fields.get("author"+suffix):
            authors.append(take("author"+suffix))
    title = take("title") or take("script-title")
    title = re.sub(r"^[a-z]{2,3}:", "", title) if "title" not in fields else title
    url = take("url")
    work = italics(title)
    if url:
        work = f"[{url} {work or url}]"
    parts = ["; ".join(authors), work]
    for key in ("chapter", "journal", "work", "newspaper"):
        value = take(key)
        if value:
            parts.append(italics(value))
    for key in ("publisher", "location", "place", "date", "year"):
        if value := take(key):
            parts.append(value)
    labels = {
        "volume": "boky", "issue": "laharana", "page": "p.", "pages": "pp.",
        "editor": "mpamoaka", "editor-last": "mpamoaka (anarana)",
        "editor-first": "mpamoaka (fanampin' anarana)",
        "editor-last2": "mpamoaka faharoa (anarana)",
        "editor-first2": "mpamoaka faharoa (fanampin' anarana)",
        "translator-last": "mpandika (anarana)", "translator-first": "mpandika (fanampin' anarana)",
        "trans-title": "dikan' ny lohateny voarakitra", "language": "fiteny",
        "via": "nampitaina tamin' ny", "others": "fanampim-baovao",
        "isbn": "ISBN", "issn": "ISSN", "doi": "DOI", "jstor": "JSTOR", "hdl": "HDL",
        "s2cid": "S2CID", "access-date": "daty nijerena voarakitra",
        "accessdate": "daty nijerena voarakitra", "archive-date": "datin' ny tahiry",
        "url-status": "toetry ny rohy voarakitra", "url-access": "fidirana voarakitra",
        "doi-access": "fidirana DOI voarakitra", "hdl-access": "fidirana HDL voarakitra",
        "p": "p.", "pp": "pp.", "edition": "fanontana", "lang": "fiteny",
        "orig-date": "daty niandohana voarakitra", "website": "tranonkala",
        "oclc": "OCLC",
    }
    for key, label in labels.items():
        if value := take(key):
            if key in {"isbn", "issn", "doi", "jstor", "hdl", "s2cid"}:
                parts.append(f"<nowiki>{label} {value}</nowiki>")
            else:
                parts.append(f"{label}: {value}")
    if value := take("archive-url"):
        parts.append(f"[{value} rohy tahiry voarakitra]")
    # author-link fields are presentation directives, not author-name evidence.
    # Their exact original bytes remain in source.wiki and citation-inventory.json.
    for key, value in fields.items():
        if key not in used and not re.fullmatch(r"(?:author(?:-?link\d*|\d+-link)|editor-link\d*)", key):
            parts.append(f"{key}: {value}")
    return ". ".join(x for x in parts if x) + "."


def native_templates(text, expansions=None):
    expansions = expansions or {}
    code = mw.parse(text)
    for t in list(code.filter_templates(recursive=True)):
        name = str(t.name).strip().lower()
        replacement = None
        if name.startswith("cite "):
            replacement = citation(t)
        elif name in {"sfnb", "sfn"}:
            author, year = param(t, "1"), param(t, "2")
            pages = param(t, "p") or param(t, "pp")
            replacement = f"<ref>{author} ({year})" + (f", p. {pages}" if pages else "") + ".</ref>"
        elif name in {"transliteration", "transl"}:
            replacement = italics(param(t, "2"))
        elif name in {"nihongo", "nihongo3"}:
            en, ja, roman = (param(t, str(i)) for i in (1, 2, 3))
            replacement = (en or roman or ja) + (f" ({ja})" if ja and (en or roman) else "")
        elif name == "isbn":
            replacement = "<nowiki>ISBN " + param(t, "1") + "</nowiki>"
        elif name in {"dead link", "cbignore", "why", "who"}:
            replacement = ""
        elif name in {"webarchive", "webarchive ", "webarchive".lower()}:
            url, date = param(t, "url"), param(t, "date")
            replacement = f"[{url} tahiry" + (f" tamin' ny {date}" if date else "") + "]" if url else ""
        elif name == "google books":
            volume = param(t, "1")
            replacement = "[https://books.google.com/books?id=" + volume + " ''" + param(t, "2") + "''], p. " + param(t, "page")
        elif name in expansions:
            replacement = expansions[name]
        if replacement is not None:
            try:
                code.replace(t, replacement)
            except ValueError:
                pass  # Parent replacement has already incorporated its value.
    return str(code)


def map_links(text, mapping):
    code = mw.parse(text)
    decisions = []
    verified = {value["mg"] for value in mapping.values() if value.get("mg")}
    for link in list(code.filter_wikilinks()):
        target = str(link.title).strip()
        label = str(link.text) if link.text is not None else target
        base, _, anchor = target.partition("#")
        if target.lower().startswith(("file:", "image:", ":sokajy:")) or target.startswith("#"):
            continue
        if base in verified or target.startswith(":s:ja:"):
            continue
        item = mapping.get(base.replace("_", " "), {})
        mg = item.get("mg")
        if mg:
            # Only source-supported cross-page anchors may survive. Most source
            # anchors are English; link to the verified same-topic page instead.
            replacement = f"[[{mg}|{label}]]" if label != mg else f"[[{mg}]]"
            decision = f"{target} → {mg}" + (" (vatofantsika anglisy nesorina)" if anchor else "")
        else:
            replacement = label
            decision = f"{target} → soratra tsotra: tsy misy target malagasy voamarina"
        try:
            code.replace(link, replacement)
            decisions.append(decision)
        except ValueError:
            pass
    return str(code), decisions


if __name__ == "__main__":
    source = (JOB / "source.wiki").read_text(encoding="utf-8")
    templates = [str(t) for t in mw.parse(source).filter_templates()
                 if str(t.name).strip().lower().startswith("cite ")]
    (JOB / "citation-inventory.json").write_text(
        json.dumps(templates, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print("Citation metadata inventory:", len(templates))
