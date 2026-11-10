"""Inspect the source bibliography's own revision history, through Wiki."""
from pathlib import Path

from mgwiki_editor.core import Wiki, now, write_json

JOB = Path("runs/genji-en-20261105-utf8")


if __name__ == "__main__":
    wiki = Wiki()
    data = wiki.site("en").simple_request(
        action="query", titles="The Tale of Genji", prop="revisions",
        rvstartid=1381255844, rvdir="older", rvlimit=15,
        rvprop="ids|timestamp|comment|content", rvslots="main", rvsection="21",
        formatversion=2,
    ).submit()
    # Only bibliography content was requested, not a new source/base snapshot.
    write_json(JOB / "evidence" / "bibliography-history.json", {"retrieved_at": now(), "response": data})
    for page in data["query"]["pages"]:
        for revision in page.get("revisions", []):
            text = revision["slots"]["main"].get("content", "")
            pos = text.find("Nihon Koten Bungaku Taikei 14")
            print(revision["revid"], revision["timestamp"], revision.get("comment", ""))
            print(text[max(0, pos-150):pos+300] if pos >= 0 else "No matching entry; "+text[:100])
