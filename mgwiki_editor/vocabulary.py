"""Offline, source-attested terminology candidates; never dictionary verification."""

from __future__ import annotations

import json
import os
import re
import sqlite3
import tempfile
import unicodedata
from collections import defaultdict
from contextlib import closing
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from .core import GuardError, digest

VOCABULARY_CACHE = Path("data/vocabulary/kajy-mathematics.json")
VOCABULARY_DATABASE = Path("data/vocabulary/kajy-mathematics.sqlite")
KAJY_URL = (
    "https://kajy.blogspot.com/2011/04/ireo-voambolana-matematika-malagasy.html?m=1"
)
KAJY_FEED_URL = "https://kajy.blogspot.com/feeds/posts/default/2307042205075419731?alt=json"
KAJY_ID = "tag:blogger.com,1999:blog-7429401142448269532.post-2307042205075419731"


class GlossaryRows(HTMLParser):
    """Extract visible table cells without executing HTML or loading any resource."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self.row: list[str] | None = None
        self.cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self.row = []
        elif tag == "td":
            self.cell = []
        elif tag in {"br", "div", "p"} and self.cell is not None:
            self.cell.append(" ")

    def handle_data(self, data: str) -> None:
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "td" and self.row is not None and self.cell is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None
        elif tag in {"div", "p"} and self.cell is not None:
            self.cell.append(" ")


def import_kajy_feed(payload: bytes, *, retrieved_at: str) -> dict[str, Any]:
    """Import a user-requested, already downloaded post; no network or file writes."""
    post = json.loads(payload)["entry"]
    if post["id"]["$t"] != KAJY_ID or post["content"]["type"] != "html":
        raise GuardError("Not the requested Kajy glossary post.")
    html = post["content"]["$t"]
    parser = GlossaryRows()
    parser.feed(html)
    entries = []
    placeholders = []
    for table_row, cells in enumerate(parser.rows, 1):
        if not any(cells):
            continue
        if len(cells) != 2:
            raise GuardError(f"Expected two glossary columns at table row {table_row}.")
        left, french = cells
        # Section letters can share a cell with its first term. Row 193 also
        # contains an empty numbered section heading, 192; retain that evidence.
        matches = list(re.finditer(r"(?<!\d)(\d+)\.\s*", left))
        if not matches or not french:
            raise GuardError(f"Unrecognized glossary row {table_row}.")
        number = matches[-1]
        malagasy = left[number.end():].strip()
        if not malagasy:
            raise GuardError(f"Missing Malagasy term at table row {table_row}.")
        for placeholder in matches[:-1]:
            placeholders.append({
                "source_number": int(placeholder[1]), "table_row": table_row,
                "reason": "Numbered section heading; no bilingual term. Not invented.",
            })
        flags = []
        if len(matches) > 1:
            flags.append("numbered_heading_prefix")
        if any(value.count("(") != value.count(")") for value in (malagasy, french)):
            flags.append("unbalanced_parentheses")
        if int(number[1]) in {80, 81}:
            flags.append("split_entry_across_rows_80_81")
        entries.append({
            "source_number": int(number[1]), "table_row": table_row,
            "malagasy": malagasy, "french": french, "source_cells": cells,
            "status": "candidate", "review_flags": flags,
        })
    numbers = [entry["source_number"] for entry in entries]
    if not entries or numbers != sorted(set(numbers)):
        raise GuardError("Empty, duplicate, or unordered Kajy source numbers.")
    senses: dict[str, set[str]] = defaultdict(set)
    for entry in entries:
        senses[entry["malagasy"].casefold()].add(entry["french"].casefold())
    for entry in entries:
        if len(senses[entry["malagasy"].casefold()]) > 1:
            entry["review_flags"].append("multiple_french_senses")
    return {
        "schema": 1, "domain": "mathematics", "languages": ["mg", "fr"],
        "source": {
            "url": KAJY_URL, "retrieval_url": KAJY_FEED_URL, "post_id": KAJY_ID,
            "title": post["title"]["$t"], "author": post["author"][0]["name"]["$t"],
            "published_at": post["published"]["$t"], "updated_at": post["updated"]["$t"],
            "retrieved_at": retrieved_at, "feed_sha256": digest(payload),
            "content_sha256": digest(html.encode("utf-8")),
            "authority": (
                "User-requested blog glossary; candidates, not verified dictionary entries."
            ),
            "rights": "No reuse license verified. Terminology evidence, not article prose.",
        },
        "normalization": (
            "HTML text/entity extraction; whitespace collapsed. Source spellings retained. "
            "Number/heading prefixes removed only from malagasy, retained in source_cells. "
            "No English equivalents, definitions, typo corrections, or row merges invented."
        ),
        "source_row_count": len(parser.rows), "entry_count": len(entries),
        "numbered_placeholders": placeholders, "entries": entries,
    }


def search_key(text: str) -> str:
    """Fold case, accents, apostrophe variants and whitespace for search only."""
    text = unicodedata.normalize("NFKD", text.casefold().replace("’", "'"))
    return " ".join("".join(c for c in text if not unicodedata.combining(c)).split())


def validate_glossary(result: Any, *, allow_empty: bool = False) -> None:
    """Validate the JSON import format and decoded SQLite query rows."""
    if (
        not isinstance(result, dict) or result.get("schema") != 1
        or result.get("domain") != "mathematics" or result.get("languages") != ["mg", "fr"]
        or not isinstance(result.get("source"), dict) or result["source"].get("post_id") != KAJY_ID
        or not isinstance(result.get("entries"), list)
        or (not result["entries"] and not allow_empty)
        or result.get("entry_count") != len(result["entries"])
        or any(
            not isinstance(entry, dict) or entry.get("status") != "candidate"
            or not isinstance(entry.get("source_number"), int)
            or not isinstance(entry.get("review_flags"), list)
            or not isinstance(entry.get("source_cells"), list) or len(entry["source_cells"]) != 2
            or any(not isinstance(flag, str) for flag in entry["review_flags"])
            or any(not isinstance(entry.get(key), str) or not entry[key]
                   for key in ("malagasy", "french"))
            for entry in result["entries"]
        )
    ):
        raise GuardError("Invalid local vocabulary cache.")


def load_vocabulary_cache(cache: Path = VOCABULARY_CACHE) -> dict[str, Any]:
    """Read the preserved JSON import snapshot, not the live query database."""
    result = json.loads(cache.read_bytes())
    validate_glossary(result)
    return result


def build_vocabulary_database(
    source: Path = VOCABULARY_CACHE, output: Path = VOCABULARY_DATABASE,
) -> dict[str, Any]:
    """Build a standalone indexed SQLite snapshot offline; never overwrite any file."""
    if output.exists():
        raise GuardError("Vocabulary database already exists; choose a new output path.")
    payload = source.read_bytes()
    glossary = json.loads(payload)
    validate_glossary(glossary)
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=".vocabulary-", suffix=".sqlite", dir=output.parent,
    )
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        with closing(sqlite3.connect(temporary)) as database:
            database.executescript("""
                PRAGMA journal_mode = DELETE;
                PRAGMA user_version = 1;
                CREATE TABLE metadata (key TEXT PRIMARY KEY, value_json TEXT NOT NULL);
                CREATE TABLE entries (
                    source_number INTEGER PRIMARY KEY,
                    table_row INTEGER NOT NULL,
                    malagasy TEXT NOT NULL,
                    french TEXT NOT NULL,
                    malagasy_key TEXT NOT NULL,
                    french_key TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status = 'candidate'),
                    source_cells_json TEXT NOT NULL,
                    review_flags_json TEXT NOT NULL
                );
                CREATE INDEX entries_malagasy_key ON entries (malagasy_key);
                CREATE INDEX entries_french_key ON entries (french_key);
            """)
            metadata = {key: value for key, value in glossary.items() if key != "entries"}
            metadata["source_cache_sha256"] = digest(payload)
            database.executemany(
                "INSERT INTO metadata (key, value_json) VALUES (?, ?)",
                [(key, json.dumps(value, ensure_ascii=False)) for key, value in metadata.items()],
            )
            database.executemany(
                "INSERT INTO entries VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [(
                    entry["source_number"], entry["table_row"], entry["malagasy"], entry["french"],
                    search_key(entry["malagasy"]), search_key(entry["french"]), entry["status"],
                    json.dumps(entry["source_cells"], ensure_ascii=False),
                    json.dumps(entry["review_flags"], ensure_ascii=False),
                ) for entry in glossary["entries"]],
            )
            database.commit()
            if database.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                raise GuardError("Vocabulary database failed integrity checking.")
        # Atomic publication without replacement, even if another builder races.
        os.link(temporary, output)
    finally:
        temporary.unlink()
    return {"database": str(output), "entry_count": glossary["entry_count"],
            "database_sha256": digest(output.read_bytes()), "source_cache_sha256": digest(payload)}


def vocabulary(
    word: str | None = None, *, language: str = "fr", cache: Path = VOCABULARY_DATABASE,
    exact: bool = False,
) -> dict[str, Any]:
    """Query SQLite in read-only mode with bound parameters; no network or substitutions."""
    if language not in {"fr", "mg"}:
        raise GuardError("Glossary language must be fr or mg; no English mapping is supplied.")
    if word is not None and (not search_key(word) or len(word) > 250):
        raise GuardError("Supply a nonempty glossary term of at most 250 characters.")
    if not cache.is_file():
        raise GuardError("Local vocabulary database missing; no automatic external fetch.")
    before = digest(cache.read_bytes())
    key = "malagasy_key" if language == "mg" else "french_key"
    sql = "SELECT * FROM entries"
    parameters: tuple[str, ...] = ()
    if word is not None:
        sql += f" WHERE {key} = ?" if exact else f" WHERE instr({key}, ?) > 0"
        parameters = (search_key(word),)
    sql += " ORDER BY source_number"
    try:
        with closing(sqlite3.connect(cache.resolve().as_uri() + "?mode=ro", uri=True)) as database:
            database.execute("PRAGMA query_only = ON")
            database.execute("PRAGMA trusted_schema = OFF")
            if database.execute("PRAGMA user_version").fetchone()[0] != 1:
                raise GuardError("Unsupported vocabulary database schema.")
            if database.execute("PRAGMA journal_mode").fetchone()[0] != "delete":
                raise GuardError("Vocabulary database must be a standalone, non-WAL snapshot.")
            database.row_factory = sqlite3.Row
            database.execute("BEGIN")
            result = {row["key"]: json.loads(row["value_json"])
                      for row in database.execute("SELECT key, value_json FROM metadata")}
            count = database.execute("SELECT count(*) FROM entries").fetchone()[0]
            if not count or result.get("entry_count") != count:
                raise GuardError("Vocabulary database entry count mismatch.")
            entries = []
            for row in database.execute(sql, parameters):
                entries.append({
                    "source_number": row["source_number"], "table_row": row["table_row"],
                    "malagasy": row["malagasy"], "french": row["french"], "status": row["status"],
                    "source_cells": json.loads(row["source_cells_json"]),
                    "review_flags": json.loads(row["review_flags_json"]),
                })
            validate_glossary({**result, "entries": entries, "entry_count": len(entries)},
                              allow_empty=True)
    except (sqlite3.DatabaseError, ValueError, TypeError) as exc:
        raise GuardError("Invalid local vocabulary database.") from exc
    if digest(cache.read_bytes()) != before:
        raise GuardError(
            "Vocabulary database changed during lookup; retain evidence and retry locally.",
        )
    return {
        **result, "database_path": str(cache), "database_sha256": before,
        "cache_path": str(cache), "cache_sha256": before,
        "query": word, "query_language": language, "match_count": len(entries), "entries": entries,
        "match_mode": "exact" if exact else "substring",
    }
