"""Cached metadata and opt-in link mapping; no Wikipedia calls."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mgwiki_editor import cli
from mgwiki_editor.core import GuardError, read_json, write_json
from mgwiki_editor.links import adapt_links, build_link_map, load_link_map
from mgwiki_editor.workflow import assemble_sections, plan_sections


@pytest.fixture
def job(tmp_path: Path) -> Path:
    (tmp_path / "evidence").mkdir()
    return tmp_path


def batch(job: Path, name: str = "links.json", **extra) -> str:
    """Use a source topic unrelated to historical recipes."""
    filename = f"evidence/{name}"
    write_json(
        job / filename,
        {
            "response": {
                "query": {
                    "pages": [
                        {
                            "ns": 0,
                            "title": "Source",
                            "langlinks": [{"lang": "mg", "title": "Kendrena"}],
                        }
                    ],
                    **extra,
                }
            }
        },
    )
    return filename


def test_build_alias_chain_and_merge_provenance(job: Path) -> None:
    first = batch(
        job,
        normalized=[{"from": "source", "to": "Source alias"}],
        redirects=[{"from": "Source alias", "to": "Source"}],
    )
    second = batch(job, "other.json")
    result = build_link_map(job, [second, first], "en")
    assert result == build_link_map(job, [first, second], "en")
    row = result["mappings"]["source"]
    assert row["mg"] == "Kendrena"
    assert row["canonical_source"] == "Source"
    assert row["evidence_files"] == sorted([first, second])
    assert result["status"] == "cached_candidates_only"
    assert len(result["artifacts"]) == 2


def test_underscore_normalization_is_not_a_redirect_cycle(job: Path) -> None:
    filename = batch(job, normalized=[{"from": "Some_title", "to": "Some title"}])
    assert "Some title" not in build_link_map(job, [filename], "en")["mappings"]


@pytest.mark.parametrize("special", [{"tofragment": "A section"}, {"tointerwiki": True}])
def test_narrower_or_interwiki_redirect_is_not_same_topic(job: Path, special) -> None:
    filename = batch(job, redirects=[{"from": "Alias", "to": "Source", **special}])
    row = build_link_map(job, [filename], "en")["mappings"]["Alias"]
    assert row["mg"] is None
    assert row["reason"] == "section_or_interwiki_redirect_requires_review"


def test_missing_redirect_terminal_stays_unresolved(job: Path) -> None:
    filename = batch(job, redirects=[{"from": "Alias", "to": "Not in batch"}])
    row = build_link_map(job, [filename], "en")["mappings"]["Alias"]
    assert row["mg"] is None
    assert row["reason"] == "redirect_target_evidence_missing"


@pytest.mark.parametrize(
    "response",
    [
        {"continue": {}, "query": {"pages": []}},
        {"error": "failed"},
        {"errors": []},
        {"warnings": {}},
        {"query": {"pages": {}}},
        {"query": {"pages": [{"title": "Source", "ns": 1}]}},
        {"query": {"pages": [{"title": "Source", "ns": 0, "langlinks": "bad"}]}},
        {
            "query": {
                "pages": [
                    {
                        "title": "Source",
                        "ns": 0,
                        "langlinks": [{"lang": "mg", "title": "Sokajy:Not a topic"}],
                    }
                ]
            }
        },
        {"query": {"pages": [{"title": "Source", "ns": 0, "langlinks": [{"lang": "mg"}]}]}},
    ],
)
def test_incomplete_or_malformed_metadata_rejected(job: Path, response) -> None:
    write_json(job / "evidence/bad.json", {"response": response})
    with pytest.raises(GuardError):
        build_link_map(job, ["evidence/bad.json"], "en")


def test_conflicting_topic_results_never_choose_newest_or_first(job: Path) -> None:
    filename = batch(job)
    other = batch(
        job,
        "other.json",
        pages=[
            {
                "title": "Source",
                "ns": 0,
                "langlinks": [{"lang": "mg", "title": "Hafa"}],
            }
        ],
    )
    with pytest.raises(GuardError, match="Conflicting cached topic"):
        build_link_map(job, [filename, other], "en")


def test_redirect_cycles_and_conflicting_edges(job: Path) -> None:
    filename = batch(job, redirects=[{"from": "A", "to": "B"}, {"from": "B", "to": "A"}])
    with pytest.raises(GuardError, match="cycle"):
        build_link_map(job, [filename], "en")
    filename = batch(job, redirects=[{"from": "A", "to": "B"}, {"from": "A", "to": "C"}])
    with pytest.raises(GuardError, match="Conflicting cached redirect"):
        build_link_map(job, [filename], "en")


def test_missing_page_vs_no_language_link(job: Path) -> None:
    filename = batch(
        job, pages=[{"title": "Absent", "ns": 0, "missing": True}, {"title": "No link", "ns": 0}]
    )
    mapping = build_link_map(job, [filename], "en")["mappings"]
    assert mapping["Absent"]["missing"] is True
    assert mapping["No link"]["missing"] is False
    assert mapping["Absent"]["mg"] is mapping["No link"]["mg"] is None


def test_language_must_match_job_and_map_inputs_stay_local(job: Path) -> None:
    filename = batch(job)
    write_json(job / "job.json", {"source": {"language": "fr"}})
    with pytest.raises(GuardError, match="language"):
        build_link_map(job, [filename], "en")
    with pytest.raises(GuardError):
        build_link_map(job, ["../outside.json"], "fr")


def test_loading_map_revalidates_assertions_and_evidence_hashes(job: Path) -> None:
    filename = batch(job)
    result = build_link_map(job, [filename], "en")
    write_json(job / "link-map.json", result)
    mapping, artifacts = load_link_map(job, "link-map.json")
    assert mapping["Source"]["mg"] == "Kendrena"
    assert set(artifacts) == {filename, "link-map.json"}
    result["mappings"]["Source"]["mg"] = "Invented"
    write_json(job / "link-map.json", result)
    with pytest.raises(GuardError, match="changed"):
        load_link_map(job, "link-map.json")
    write_json(job / "link-map.json", build_link_map(job, [filename], "en"))
    with (job / filename).open("a", encoding="utf-8") as stream:
        stream.write("\n")
    with pytest.raises(GuardError, match="changed"):
        load_link_map(job, "link-map.json")


def test_adapt_only_prose_and_captions_preserving_original_metadata() -> None:
    mapping = {"Source": {"mg": "Kendrena", "evidence_files": ["evidence/links.json"]}}
    protected = (
        "<ref>[[Source|ref metadata]]</ref>{{Box|x=[[Source]]}}"
        " ''[[Source|original title]]'' <nowiki>[[Source]]</nowiki>"
        " <math>[[Source]]</math> <code>[[Source]]</code>"
        " <blockquote>[[Source|quote]]</blockquote>"
        " [https://example.invalid/Source [[Source|external title]]]"
    )
    text = (
        "== [[Source|heading]] ==\n[[Source|translated label]]"
        + protected
        + "[[File:Source.jpg|thumb|upright=1.2|[[Source|caption]]]]\n"
        "<gallery>\nFile:Source.jpg|[[Source|gallery caption]]\n</gallery>\n"
        "{|\n| [[Source|table cell]]\n|}\n"
    )
    result, ledger = adapt_links(text, mapping)
    assert protected in result
    for label in ("heading", "translated label", "caption", "gallery caption", "table cell"):
        assert f"[[Kendrena|{label}]]" in result
    assert "File:Source.jpg|thumb|upright=1.2|" in result
    assert "File:Source.jpg|[[Kendrena|gallery caption]]" in result
    assert any(row["action"] == "protected_unchanged" for row in ledger)


def test_fallbacks_anchors_and_category_safety() -> None:
    mapping = {"Source": {"mg": "Kendrena", "evidence_files": ["links.json"]}}
    text = (
        "[[Source#Foreign anchor|label]] [[Missing|plain label]] "
        "[[#Nadika|local label]] [[Kendrena]] [[Kendrena#Local|local]] "
        "[[Sokajy:Keep|Sort]][[:Sokajy:Already|Key]][[Category:Foreign]]"
    )
    result, ledger = adapt_links(text, mapping)
    assert result == (
        "[[Kendrena|label]] plain label [[#Nadika|local label]] "
        "[[Kendrena]] [[Kendrena#Local|local]] "
        "[[Sokajy:Keep|Sort]][[Sokajy:Already|Key]][[:Category:Foreign]]"
    )
    assert {r["action"] for r in ledger} >= {
        "mapped_anchor_omitted",
        "plain_text_no_verified_target",
        "same_page_anchor_requires_review",
        "local_anchor_requires_review",
        "category_made_live",
        "category_unchanged",
        "category_foreign_made_inert",
    }


@pytest.mark.parametrize("destination", ["Lehilahy", None])
def test_explicit_source_mapping_wins_over_local_inference(destination: str | None) -> None:
    mapping = {
        "Man": {"mg": destination, "evidence_files": ["people.json"]},
        "Isle of Man": {"mg": "Man", "evidence_files": ["island.json"]},
    }
    result, decisions = adapt_links("[[Man|human label]]", mapping)
    assert result == ("[[Lehilahy|human label]]" if destination else "human label")
    assert decisions[0]["destination"] == destination
    assert decisions[0]["evidence_files"] == ["people.json"]


def test_colon_title_uses_pinned_mainspace_identity_not_a_prefix_guess(job: Path) -> None:
    filename = batch(
        job,
        pages=[
            {
                "title": "Source series",
                "ns": 0,
                "langlinks": [{"lang": "mg", "title": "Star Trek: Voyager"}],
            }
        ],
    )
    local = "evidence/mg-pages.json"
    write_json(
        job / local,
        {
            "response": {
                "query": {
                    "pages": [
                        {"title": "Star Trek: Voyager", "ns": 0, "pageid": 123},
                    ]
                }
            }
        },
    )
    with pytest.raises(GuardError, match="namespace-0"):
        build_link_map(job, [filename], "en")
    result = build_link_map(job, [filename], "en", local_files=[local])
    assert result["mappings"]["Source series"]["mg"] == "Star Trek: Voyager"
    assert set(result["mappings"]["Source series"]["evidence_files"]) == {filename, local}
    write_json(job / "map.json", result)
    mappings, artifacts = load_link_map(job, "map.json")
    assert set(artifacts) == {filename, local, "map.json"}
    assert adapt_links("[[Source series|label]]", mappings)[0] == "[[Star Trek: Voyager|label]]"
    with (job / local).open("a", encoding="utf-8") as stream:
        stream.write("\n")
    with pytest.raises(GuardError, match="changed"):
        load_link_map(job, "map.json")


@pytest.mark.parametrize(
    "page",
    [
        {"title": "Sokajy:Not a topic", "ns": 14},
        {"title": "Sokajy:Not a topic", "ns": 0, "missing": True},
        {"title": "Sokajy:Not a topic"},
    ],
)
def test_namespace_or_missing_target_evidence_cannot_authorize_a_colon_link(
    job: Path,
    page: dict,
) -> None:
    filename = batch(
        job,
        pages=[
            {
                "title": "Source",
                "ns": 0,
                "langlinks": [{"lang": "mg", "title": "Sokajy:Not a topic"}],
            }
        ],
    )
    write_json(job / "evidence/local.json", {"query": {"pages": [page]}})
    with pytest.raises(GuardError):
        build_link_map(job, [filename], "en", local_files=["evidence/local.json"])


def test_colon_namespace_evidence_cli_is_offline(job: Path, monkeypatch, capsys) -> None:
    filename = batch(
        job,
        pages=[
            {
                "title": "Source",
                "ns": 0,
                "langlinks": [{"lang": "mg", "title": "Title: Subtitle"}],
            }
        ],
    )
    write_json(
        job / "evidence/local.json",
        {
            "query": {
                "pages": [
                    {"title": "Title: Subtitle", "ns": 0},
                ]
            }
        },
    )

    def forbidden():
        raise AssertionError("Namespace verification must use pinned evidence, not live requests")

    monkeypatch.setattr(cli, "Wiki", forbidden)
    assert (
        cli.main(
            [
                "links-build",
                "--job",
                str(job),
                "--source-lang",
                "en",
                "--evidence",
                filename,
                "--local-evidence",
                "evidence/local.json",
            ]
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert result["mappings"]["Source"]["mg"] == "Title: Subtitle"
    assert "evidence/local.json" in result["local_artifacts"]


def test_namespace_evidence_cannot_choose_a_winner_or_reuse_source_snapshot(job: Path) -> None:
    filename = batch(job)
    with pytest.raises(GuardError, match="separate snapshots"):
        build_link_map(job, [filename], "en", local_files=[filename])
    write_json(
        job / "evidence/local.json",
        {
            "query": {
                "pages": [
                    {"title": "Conflicting: Topic", "ns": 0},
                    {"title": "Conflicting: Topic", "ns": 14},
                ]
            }
        },
    )
    with pytest.raises(GuardError, match="Conflicting Malagasy namespace"):
        build_link_map(job, [filename], "en", local_files=["evidence/local.json"])


def test_assembly_opt_in_map_pins_inputs_and_protects_citations(job: Path) -> None:
    filename = batch(job)
    write_json(job / "link-map.json", build_link_map(job, [filename], "en"))
    (job / "source.wiki").write_text("Source lead.\n", encoding="utf-8")
    (job / "draft.wiki").write_text("Existing draft", encoding="utf-8")
    plan_sections(job)
    directory = job / "sections/00-lead"
    (directory / "section.wiki").write_text(
        "[[Source|label]] {{cite book|title=[[Source|Original]]}}",
        encoding="utf-8",
    )
    (directory / "notes.wiki").write_text("# Handoff\nPending review.", encoding="utf-8")
    write_json(directory / "vocabulary.json", [])
    assemble_sections(job, native_citations=True, link_map="link-map.json")
    assert (job / "assembly/draft.wiki").read_text() == (
        "[[Kendrena|label]] title: [[Source|Original]].\n"
    )
    manifest = read_json(job / "assembly/assembly.json")
    assert {filename, "link-map.json"} <= set(manifest["inputs"])
    assert (job / "draft.wiki").read_text() == "Existing draft"
    assert read_json(job / "assembly/link-decisions.json")[0]["section_id"] == "00-lead"


def test_links_cli_offline_and_exclusive_output(job: Path, monkeypatch, capsys) -> None:
    filename = batch(job)

    def forbidden():
        raise AssertionError("No Wiki construction")

    monkeypatch.setattr(cli, "Wiki", forbidden)
    args = [
        "links-build",
        "--job",
        str(job),
        "--source-lang",
        "en",
        "--evidence",
        filename,
        "--output",
        str(job / "map.json"),
    ]
    assert cli.main(args) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "cached_candidates_only"
    original = (job / "map.json").read_bytes()
    assert cli.main(args) == 1
    assert "Output exists" in capsys.readouterr().err
    assert (job / "map.json").read_bytes() == original
