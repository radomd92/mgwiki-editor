"""Local raw-wikitext mechanics; no topic constants or remote resolution."""

import hashlib
import json
from pathlib import Path

import pytest

from mgwiki_editor.core import GuardError
from mgwiki_editor.wikitext import (
    convert_citations,
    convert_related_hatnotes,
    inventory,
    promote_article_categories,
    reference_inventory,
)


def test_reference_groups_and_exact_metadata() -> None:
    text = ('<ref name="same" group="a">One</ref><ref name="same" group="b">Two</ref>'
            '<ref name="same" group="a" /><ref>Anonymous</ref>')
    refs = reference_inventory(text)
    assert refs["anonymous_count"] == 1
    assert refs["undefined"] == refs["conflicts"] == []
    assert refs["named"] == [
        {"group": "a", "name": "same", "calls": 2, "body": "One"},
        {"group": "b", "name": "same", "calls": 1, "body": "Two"},
    ]


def test_reference_dangling_and_conflicting_definitions() -> None:
    refs = reference_inventory(
        '<ref name=bad>One</ref><ref name=bad>Two</ref><ref name=missing group=note />',
    )
    assert refs["conflicts"] == [{"group": "", "name": "bad"}]
    assert refs["undefined"] == [{"group": "note", "name": "missing"}]


def test_inventory_includes_nested_templates_and_galleries() -> None:
    result = inventory(
        '{{Box|body=[[Topic|Label]]|image=Nested.png}}'
        '[[File:Photo_a.jpg|thumb|[[Caption topic|Caption]]]][[:Sokajy:Keep|Sort]]\n'
        '<gallery>\nFile:Other.svg|Caption\nBare.webp|Alt\n</gallery>',
    )
    assert result["files"] == {"Bare.webp": 1, "Other.svg": 1, "Photo a.jpg": 1}
    assert {r["target"] for r in result["links"]} >= {"Topic", "Caption topic"}
    assert result["categories"] == ["[[:Sokajy:Keep|Sort]]"]
    assert result["template_file_candidates"] == [
        {"template": "Box", "parameter": "image", "value": "Nested.png"},
    ]


def test_gallery_captions_include_links_templates_and_references_once() -> None:
    text = ('<gallery>\nFile:Picture.jpg|[[Topic|caption]] {{lang|en|[[Nested]]}}'
            '<ref name="caption">Metadata</ref>\n</gallery>\n'
            '<ref name="caption" /><references />')
    result = inventory(text)
    assert result["links"] == [
        {"target": "Topic", "label": "caption"}, {"target": "Nested", "label": "Nested"},
    ]
    assert result["files"] == {"Picture.jpg": 1}
    assert result["templates"] == ["{{lang|en|[[Nested]]}}"]
    assert result["references"]["undefined"] == []
    assert result["references"]["named"][0]["calls"] == 2


@pytest.mark.parametrize("filename", [
    "File:Book.pdf", "Image:Volume.djvu", "Sary:Model.stl", "Media:Audio.mp3",
    "Book.pdf", "Volume.djvu", "Clip.webm",
])
def test_gallery_files_are_not_limited_to_image_extensions(filename: str) -> None:
    result = inventory(f"<gallery>\n{filename}|page=1|caption\n</gallery>")
    assert result["files"] == {filename.split(":", 1)[-1]: 1}


def test_citations_keep_all_authors_unknown_fields_and_name_order() -> None:
    source = ('{{cite journal|last=Surname|first=Given|author1=Name One|author101=Name 101'
              '|title=China: A title|url=https://example.invalid/article|custom=Unusual}}')
    text, ledger = convert_citations(source)
    for value in ("last: Surname", "first: Given", "author1: Name One", "author101: Name 101",
                  "title: China: A title", "url: https://example.invalid/article",
                  "custom: Unusual"):
        assert value in text
    assert ledger == [{"source": source, "replacement": text}]


def test_citation_conversion_does_not_silently_drop_maintenance_or_other_templates() -> None:
    text = '{{citation needed}}{{Box|title=Unknown}}{{cite book|title={{lang|en|Original}}}}'
    result, ledger = convert_citations(text)
    assert "{{citation needed}}" in result
    assert "{{Box|title=Unknown}}" in result
    assert "{{lang|en|Original}}" in result
    assert len(ledger) == 1


def test_empty_citation_requires_explicit_handling() -> None:
    with pytest.raises(GuardError, match="Empty citation"):
        convert_citations("{{cite book}}")


@pytest.mark.parametrize("source", [
    "{{Main|Fitsaboana}}", "{{Main article|Fitsaboana}}",
    "{{Further|Fitsaboana}}", "{{Details|Fitsaboana}}",
    "{{main|Fitsaboana}}", "{{Template:Main|Fitsaboana}}",
])
def test_related_hatnotes_use_verified_malagasy_template(source: str) -> None:
    text, ledger = convert_related_hatnotes(source)
    assert text == "{{lahatsoratra antsipirihany|Fitsaboana}}"
    assert ledger == [{"source": source, "replacement": text}]


def test_related_hatnotes_preserve_multiple_targets_and_are_idempotent() -> None:
    text, ledger = convert_related_hatnotes("{{Main|Iray|Roa}}")
    assert text == ("{{lahatsoratra antsipirihany|Iray}}\n"
                    "{{lahatsoratra antsipirihany|Roa}}")
    assert len(ledger) == 1
    unchanged, ledger = convert_related_hatnotes("{{lahatsoratra antsipirihany|Iray}}")
    assert unchanged == "{{lahatsoratra antsipirihany|Iray}}"
    assert ledger == []


def test_related_hatnotes_use_translated_malagasy_targets() -> None:
    mapping = {
        "Dentistry": {"mg": "Fitsaboana nify"},
        "History of dentistry": {"mg": "Tantaran' ny fitsaboana nify"},
        "Unmapped topic": {"mg": None},
    }
    text, ledger = convert_related_hatnotes(
        "{{Main|Dentistry}}{{Further|History of dentistry#Modern era}}{{Details|Unmapped topic}}",
        mapping,
    )
    assert "{{lahatsoratra antsipirihany|Fitsaboana nify}}" in text
    assert "{{lahatsoratra antsipirihany|Tantaran' ny fitsaboana nify#Modern era}}" in text
    assert "{{lahatsoratra antsipirihany|Unmapped topic}}" in text
    assert "Dentistry|" not in text
    assert len(ledger) == 3


def test_related_hatnote_target_already_local_is_not_remapped() -> None:
    mapping = {"Dentistry": {"mg": "Fitsaboana nify"}}
    text, _ = convert_related_hatnotes("{{Main|Fitsaboana nify}}", mapping)
    assert text == "{{lahatsoratra antsipirihany|Fitsaboana nify}}"


def test_unrelated_templates_are_not_rewritten() -> None:
    text = "{{Jereo koa|Topic}}{{Infobox|name=X}}"
    result, ledger = convert_related_hatnotes(text)
    assert result == text
    assert ledger == []


def test_inert_malagasy_categories_become_live_membership() -> None:
    text = "[[Sokajy:Keep|Sort]][[:Sokajy:Add|Key]][[:Category:Foreign]]"
    result, ledger = promote_article_categories(text)
    assert result == "[[Sokajy:Keep|Sort]][[Sokajy:Add|Key]][[:Category:Foreign]]"
    assert ledger == [{"source": "[[:Sokajy:Add|Key]]",
                       "replacement": "[[Sokajy:Add|Key]]"}]


def test_live_categories_are_left_unchanged() -> None:
    text = "[[Sokajy:Keep|Sort]] [[:Category:Foreign]]"
    result, ledger = promote_article_categories(text)
    assert result == text
    assert ledger == []


def test_archive_manifest_preserves_original_scripts() -> None:
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "scripts/legacy/manifest.json").read_text())
    assert manifest["schema"] == 1
    assert len(manifest["scripts"]) == 117
    assert not list(root.glob("*.py"))
    for record in manifest["scripts"]:
        path = root / record["path"]
        assert path.parent == root / "scripts/legacy"
        assert path.name == record["original_path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"]
