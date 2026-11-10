"""Offline glossary regressions; source attestation is not linguistic verification."""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

import pytest

from mgwiki_editor import cli
from mgwiki_editor.core import GuardError, digest
from mgwiki_editor.vocabulary import (
    KAJY_ID,
    KAJY_URL,
    build_vocabulary_database,
    import_kajy_feed,
    load_vocabulary_cache,
    vocabulary,
)

CACHE = Path(__file__).resolve().parents[1] / "data/vocabulary/kajy-mathematics.sqlite"
SNAPSHOT = CACHE.with_suffix(".json")


def feed(rows: str, *, identity: str = KAJY_ID) -> bytes:
    """Build a tiny local Blogger response; no remote fixtures or resources."""
    return json.dumps({"entry": {
        "id": {"$t": identity}, "title": {"$t": "Synthetic glossary"},
        "author": [{"name": {"$t": "Test author"}}],
        "published": {"$t": "2011-04-19"}, "updated": {"$t": "2011-04-19"},
        "content": {"type": "html", "$t": f"<table>{rows}</table>"},
    }}).encode("utf-8")


def test_cached_glossary_preserves_all_numbered_terms_and_provenance() -> None:
    result = vocabulary(cache=CACHE)
    assert result["entry_count"] == result["match_count"] == 507
    assert result["source_row_count"] == 512
    assert [entry["source_number"] for entry in result["entries"]] == [
        number for number in range(1, 509) if number != 192
    ]
    assert result["source"]["url"] == KAJY_URL
    assert result["source"]["author"] == "teny malagasy"
    assert result["source"]["published_at"] == "2011-04-19T08:52:00.000-07:00"
    for key in ("feed_sha256", "content_sha256"):
        assert re.fullmatch(r"[0-9a-f]{64}", result["source"][key])
    assert result["cache_sha256"] == digest(CACHE.read_bytes())
    assert result["languages"] == ["mg", "fr"]
    for entry in result["entries"]:
        assert entry["status"] == "candidate"
        assert len(entry["source_cells"]) == 2
        assert entry["source_cells"][1] == entry["french"]
        assert entry["source_cells"][0].endswith(entry["malagasy"])
        assert "english_definition" not in entry


@pytest.mark.parametrize("word", ["équation", "EQUATION", "e\u0301quation"])
def test_search_folds_accents_and_case_without_rewriting_source(word: str) -> None:
    result = vocabulary(word, cache=CACHE)
    assert [entry["source_number"] for entry in result["entries"]] == [102, 268]
    assert result["entries"][0]["malagasy"] == "Fampimirana"
    assert result["entries"][1]["french"] == "Equation différentielle"


def test_malagasy_search_preserves_original_apostrophes() -> None:
    result = vocabulary("amin'ny", language="mg", cache=CACHE)
    assert result["entries"][0]["malagasy"] == "Amin’ny lafiny roa"
    assert result["query_language"] == "mg"


def test_alternatives_and_polysemy_are_not_collapsed() -> None:
    result = vocabulary("logarithme", cache=CACHE)
    assert [entry["malagasy"] for entry in result["entries"]] == ["Anaiso", "Logaritima"]
    result = vocabulary("mirazotra", language="mg", cache=CACHE)
    assert [entry["french"] for entry in result["entries"]] == ["Colinéaire", "Parallèle"]
    assert all("multiple_french_senses" in entry["review_flags"] for entry in result["entries"])


def test_broken_source_rows_are_retained_as_candidates() -> None:
    entries = {entry["source_number"]: entry for entry in vocabulary(cache=CACHE)["entries"]}
    for number in (80, 81):
        assert "split_entry_across_rows_80_81" in entries[number]["review_flags"]
        assert "unbalanced_parentheses" in entries[number]["review_flags"]
    assert entries[82]["french"] == "Congurence"
    assert entries[343]["french"] == "Srjectif"
    assert 192 not in entries
    assert entries[193]["malagasy"] == "Kisendrasendra"
    assert entries[193]["source_cells"][0] == "192. K 193. Kisendrasendra"


def test_no_match_is_local_only_and_retains_provenance() -> None:
    result = vocabulary("nonexistent-glossary-term", cache=CACHE)
    assert result["entries"] == []
    assert result["match_count"] == 0
    assert result["entry_count"] == 507
    assert result["source"]["url"] == KAJY_URL


@pytest.mark.parametrize("word", ["", "  ", "\u0301", "x" * 251])
def test_invalid_queries_are_rejected(word: str) -> None:
    with pytest.raises(GuardError, match="nonempty"):
        vocabulary(word, cache=CACHE)


def test_english_mappings_are_not_invented() -> None:
    with pytest.raises(GuardError, match="no English mapping"):
        vocabulary("equation", language="en", cache=CACHE)


def test_missing_cache_never_triggers_fetch(tmp_path: Path) -> None:
    with pytest.raises(GuardError, match="no automatic external fetch"):
        vocabulary("equation", cache=tmp_path / "absent.json")


@pytest.mark.parametrize("mutation", ["schema", "empty", "count", "verified", "language", "id"])
def test_invalid_cache_is_not_treated_as_evidence(tmp_path: Path, mutation: str) -> None:
    result = json.loads(SNAPSHOT.read_bytes())
    if mutation == "schema":
        result["schema"] = 99
    elif mutation == "empty":
        result["entries"] = []
    elif mutation == "count":
        result["entry_count"] += 1
    elif mutation == "verified":
        result["entries"][0]["status"] = "verified"
    elif mutation == "language":
        result["languages"] = ["en", "mg"]
    else:
        result["source"]["post_id"] = "unrelated-post"
    cache = tmp_path / "invalid.json"
    cache.write_text(json.dumps(result), encoding="utf-8")
    with pytest.raises(GuardError, match="Invalid local vocabulary"):
        load_vocabulary_cache(cache)


def test_importer_extracts_cells_entities_and_numbered_headings_without_network() -> None:
    payload = feed(
        "<tr><td>G 159. <span>Goba</span></td><td>Cube</td></tr>"
        "<tr><td>I177. Ivodanja</td><td>Affine</td></tr>"
        "<tr><td>192. <div>K</div>193. Kisendrasendra</td><td>Al&eacute;atoire</td></tr>"
        "<tr><td></td><td></td></tr>"
    )
    result = import_kajy_feed(payload, retrieved_at="2026-11-09T00:00:00Z")
    assert result["entry_count"] == 3
    assert result["source_row_count"] == 4
    assert [entry["malagasy"] for entry in result["entries"]] == [
        "Goba", "Ivodanja", "Kisendrasendra",
    ]
    assert result["entries"][2]["french"] == "Aléatoire"
    assert result["numbered_placeholders"][0]["source_number"] == 192
    assert result["source"]["feed_sha256"] == digest(payload)


@pytest.mark.parametrize("rows", [
    "", "<tr><td>1. Isa</td></tr>",
    "<tr><td>1. Isa</td><td>Nombre</td><td>Extra</td></tr>",
    "<tr><td>1. Isa</td><td>Nombre</td></tr><tr><td>1. Isa</td><td>Nombre</td></tr>",
])
def test_importer_rejects_unrecognized_or_duplicate_rows(rows: str) -> None:
    with pytest.raises(GuardError):
        import_kajy_feed(feed(rows), retrieved_at="2026-11-09")


def test_importer_rejects_unrelated_post() -> None:
    with pytest.raises(GuardError, match="Not the requested"):
        import_kajy_feed(feed("", identity="another-post"), retrieved_at="2026-11-09")


def test_cli_vocab_is_offline_and_pins_without_overwriting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
) -> None:
    class OfflineWiki:
        def __getattr__(self, name):
            raise AssertionError(f"Offline vocab must not use Wikipedia: {name}")

    monkeypatch.setattr(cli, "Wiki", OfflineWiki)
    output = tmp_path / "kajy-equation.json"
    args = ["vocab", "--language", "fr", "--word", "equation", "--output", str(output)]
    assert cli.main(args) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["match_count"] == 2
    assert json.loads(output.read_bytes()) == result
    pinned = output.read_bytes()
    assert cli.main(args) == 1
    assert "Output exists" in capsys.readouterr().err
    assert output.read_bytes() == pinned


def test_sqlite_rows_preserve_complete_json_snapshot_and_source_hash() -> None:
    result = vocabulary(cache=CACHE)
    imported = load_vocabulary_cache(SNAPSHOT)
    assert result["entries"] == imported["entries"]
    assert result["source"] == imported["source"]
    assert result["numbered_placeholders"] == imported["numbered_placeholders"]
    assert result["source_cache_sha256"] == digest(SNAPSHOT.read_bytes())
    assert result["database_sha256"] == digest(CACHE.read_bytes())


def test_sqlite_query_is_read_only_and_has_indexes(tmp_path: Path) -> None:
    database = tmp_path / "terms.sqlite"
    summary = build_vocabulary_database(SNAPSHOT, database)
    before = database.read_bytes()
    result = vocabulary("equation", exact=True, cache=database)
    assert summary["entry_count"] == 507
    assert result["database_sha256"] == summary["database_sha256"]
    assert [entry["source_number"] for entry in result["entries"]] == [102]
    assert result["match_mode"] == "exact"
    assert database.read_bytes() == before
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as connection:
        indexes = {row[1] for row in connection.execute("PRAGMA index_list(entries)")}
        assert indexes == {"entries_malagasy_key", "entries_french_key"}
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            connection.execute("DELETE FROM entries")


@pytest.mark.parametrize("query", ["%", "_", "x' OR 1=1; DROP TABLE entries; --"])
def test_sqlite_query_uses_bound_literal_parameters(query: str) -> None:
    result = vocabulary(query, cache=CACHE)
    assert result["match_count"] == 0
    assert vocabulary(cache=CACHE)["entry_count"] == 507


def test_builder_never_overwrites_existing_database(tmp_path: Path) -> None:
    database = tmp_path / "existing.sqlite"
    database.write_bytes(b"existing user data")
    with pytest.raises(GuardError, match="already exists"):
        build_vocabulary_database(SNAPSHOT, database)
    assert database.read_bytes() == b"existing user data"


def test_invalid_sqlite_is_not_silently_rebuilt(tmp_path: Path) -> None:
    database = tmp_path / "invalid.sqlite"
    database.write_bytes(b"invalid data")
    with pytest.raises(GuardError, match="Invalid local vocabulary database"):
        vocabulary("equation", cache=database)
    assert database.read_bytes() == b"invalid data"


def test_cli_exact_query(capsys: pytest.CaptureFixture) -> None:
    assert cli.main(["vocab", "--word", "equation", "--exact"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["match_count"] == 1
    assert result["entries"][0]["malagasy"] == "Fampimirana"


@pytest.mark.parametrize("path", [
    "AGENTS.md", ".opencode/agents/mgwiki-editor.md", ".opencode/agents/mgwiki-section.md",
    ".opencode/skills/mg-vocab/SKILL.md", ".opencode/skills/mgwiki-edition/SKILL.md",
    "docs/edition-protocol.wiki", "README.wiki",
])
def test_grounded_substitution_workflow_is_discoverable(path: str) -> None:
    text = " ".join((CACHE.parents[2] / path).read_text(encoding="utf-8").split())
    assert "SQLite" in text or ".sqlite" in text
    assert "inventory" in text
    assert "substitut" in text
    assert "evidence" in text
    assert "quotations" in text
    assert "link targets" in text
