"""Citation and preview diagnostics with local strings only."""

import json

import pytest

from mgwiki_editor import cli
from mgwiki_editor.citations import citation_audit
from mgwiki_editor.core import GuardError, lint_wikitext
from mgwiki_editor.references import reference_inventory
from mgwiki_editor.rendering import rendering_report


def test_delayed_note_retains_inner_default_reference_and_requires_both_renderers():
    text = '{{#tag:ref|Note <ref name="book">Book</ref>|group=note}}'
    report = reference_inventory(text)
    assert report["groups"] == ["", "note"]
    assert report["missing_renderers"] == ["", "note"]
    assert report["anonymous_count"] == 1
    assert report["named"][0]["body"] == "Book"
    assert lint_wikitext(text)
    assert lint_wikitext(text + '<references /><references group="note"/>') == []


def test_delayed_named_reuse_matches_native_xml_decoded_name_and_list_definition():
    text = (
        "{{#tag:ref||name=US&Carib.|group=note}}"
        '<references group="note"><ref name="US&amp;Carib." group="note">Body</ref>'
        "</references>"
    )
    assert reference_inventory(text)["undefined"] == []
    assert reference_inventory(text)["named"][0]["calls"] == 2
    assert lint_wikitext(text) == []


def test_delayed_reference_renderer_and_literal_content():
    text = (
        '<nowiki><ref name="fake" /></nowiki>'
        "<pre>{{#tag:ref|not a reference|group=fake}}</pre>"
        "<ref>Real</ref>{{#tag:references|}}"
    )
    assert reference_inventory(text)["anonymous_count"] == 1
    assert lint_wikitext(text) == []


def test_list_defined_reference_inherits_renderer_group_but_inner_note_citation_does_not():
    text = "<ref name=x group=note/><references group=note><ref name=x>Body</ref></references>"
    assert lint_wikitext(text) == []
    assert reference_inventory(text)["named"][0]["group"] == "note"


@pytest.mark.parametrize(
    "text, error",
    [
        ("<ref name=x>One</ref><ref name=x>Two</ref><references/>", "Conflicting named"),
        ("{{#tag:ref|A|group=note|group=other}}", "Duplicate delayed"),
        ("<ref group=x group=y>A</ref>", "Duplicate reference"),
        ("{{#tag:ref|A|group={{unknown}}}}", "Dynamic reference"),
        ("<ref>Outer<ref>Inner</ref></ref>", "Raw nested"),
    ],
)
def test_reference_ambiguities_fail_lint(text, error):
    assert any(error in message for message in lint_wikitext(text))


def test_short_citations_remain_unresolved_even_with_same_surname_candidate(tmp_path):
    source = (
        "<ref>Translated from Waldmann, ''op.cit.'', p. 147.</ref>\n"
        "* {{cite book|last=Waldmann|title=An unconnected work|year=2000}}\n"
        "<ref>Lindow, ''op. cit.'', p. 2.</ref><ref>Ibid., p. 3.</ref>"
    )
    (tmp_path / "source.wiki").write_text(source)
    (tmp_path / "draft.wiki").write_text(source)
    report = citation_audit(tmp_path)
    short = report["source"]["short_citations"]
    assert len(short) == 3
    assert short[0]["author_label"] == "Waldmann"
    assert short[0]["status"] == "candidates_require_review"
    assert short[0]["candidates"][0]["basis"] == "same_surname_only"
    assert short[1]["status"] == short[2]["status"] == "needs_evidence"
    assert report["status"] == "review_required"
    assert (tmp_path / "draft.wiki").read_text() == source


def test_audit_is_scoped_and_reports_empty_draft(tmp_path):
    (tmp_path / "source.wiki").write_text("Source")
    (tmp_path / "draft.wiki").write_text("")
    assert citation_audit(tmp_path)["draft"]["empty"]
    with pytest.raises(GuardError):
        citation_audit(tmp_path, "../outside")


def test_plain_author_page_shortrefs_find_bibliography_candidates_not_proven_antecedents(tmp_path):
    text = (
        "<ref>Borg and Radelet, pp. 144–47</ref><ref>Van Norman p. 287</ref>\n"
        "* Marian J. Borg and Michael L. Radelet (2004), Original title.\n"
        "* Gail A. Van Norman (2010), Another original title.\n"
    )
    (tmp_path / "source.wiki").write_text(text, encoding="utf-8")
    (tmp_path / "draft.wiki").write_text(text, encoding="utf-8")
    short = citation_audit(tmp_path)["source"]["short_citations"]
    assert [row["author_label"] for row in short] == ["Borg and Radelet", "Van Norman"]
    assert all(row["status"] == "candidates_require_review" for row in short)
    assert all(len(row["candidates"]) == 1 for row in short)


def test_citation_audit_cli_offline_and_exclusive_output(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("MGWIKI_BROKER_SOCKET", raising=False)
    monkeypatch.delenv("MGWIKI_CAPABILITY_FILE", raising=False)
    monkeypatch.setattr(cli, "Wiki", lambda: pytest.fail("Offline audit made Wiki"))
    (tmp_path / "source.wiki").write_text("<ref>Ibid.</ref>")
    (tmp_path / "draft.wiki").write_text("Draft")
    output = tmp_path / "audit.json"
    args = ["citation-audit", "--job", str(tmp_path), "--output", str(output)]
    assert cli.main(args) == 0
    assert json.loads(capsys.readouterr().out)["source"]["short_citations"]
    assert cli.main(args) == 1


@pytest.mark.parametrize(
    "html, problem",
    [
        ('<strong CLASS="mw-ext-cite-error">Bad</strong>', "Parser/citation"),
        ('<a class=new title="Endrika:Missing">Missing</a>', "Unresolved template"),
        ('<a href="#cite_note-missing">1</a>', "no destination"),
        ('<li id="cite_note-x"></li><li id="cite_note-x"></li>', "Duplicate rendered"),
        ('<script src="https://example.invalid/x"></script>', "Active preview"),
    ],
)
def test_render_report_flags_errors_without_loading_resources(html, problem):
    result = rendering_report(html)
    assert not result["valid"]
    assert any(problem in error for error in result["errors"])


def test_rendered_note_and_backlink_graph_handles_entities_and_percent_encoding():
    html = (
        '<sup id="cite_ref-a"><a href="#cite_note-a%26b">1</a></sup>'
        '<li id="cite_note-a&amp;b"><a href="#cite_ref-a">up</a></li>'
        '<img src="https://example.invalid/never-fetch.png">'
    )
    assert rendering_report(html)["valid"]
