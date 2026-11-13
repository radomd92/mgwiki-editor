"""Typed metadata requests with fake Wikipedia API responses only."""

import json
from types import SimpleNamespace

import pytest

from mgwiki_editor.core import GuardError, Wiki
from mgwiki_editor.metadata import metadata_audit


def fake_wiki(monkeypatch, response):
    wiki, calls = Wiki(), []

    def request(**parameters):
        calls.append(parameters)
        return SimpleNamespace(submit=lambda: response)

    monkeypatch.setattr(wiki, "site", lambda language: SimpleNamespace(simple_request=request))
    monkeypatch.setattr(
        wiki,
        "page",
        lambda language, title: SimpleNamespace(
            namespace=lambda: 10, title=lambda: title.replace("Template:", "Endrika:")
        ),
    )
    return wiki, calls


def test_template_metadata_pins_exact_revision_and_missing_records(monkeypatch):
    response = {
        "query": {
            "pages": [
                {
                    "ns": 10,
                    "title": "Endrika:Flag",
                    "revisions": [
                        {
                            "revid": 123,
                            "slots": {"main": {"content": "Exact {{{parameter}}} bytes"}},
                        }
                    ],
                },
                {"ns": 10, "title": "Endrika:Absent", "missing": True},
            ]
        }
    }
    wiki, calls = fake_wiki(monkeypatch, response)
    result = wiki.template_metadata(["Template:Flag", "Template:Absent"])
    assert result["response"] is response
    assert calls[0]["rvprop"] == "ids|timestamp|sha1|content"
    assert calls[0]["rvslots"] == "main" and "redirects" not in calls[0]
    assert result["requested_to_canonical"]["Template:Flag"] == "Endrika:Flag"


@pytest.mark.parametrize(
    "response",
    [
        {"query": {"pages": [{"ns": 0}]}},
        {"query": {"pages": [{"ns": 10, "revisions": []}]}},
        {"continue": {}, "query": {"pages": []}},
        {"error": {"code": "no"}},
    ],
)
def test_incomplete_or_wrong_namespace_template_metadata_rejected(monkeypatch, response):
    wiki, _ = fake_wiki(monkeypatch, response)
    with pytest.raises(GuardError):
        wiki.template_metadata(["Template:Flag"])


def test_template_metadata_rejects_unscoped_title_before_request(monkeypatch):
    wiki, calls = fake_wiki(monkeypatch, {})
    for titles in ([], ["Water"], [False], ["Template:Flag"] * 51):
        with pytest.raises(GuardError):
            wiki.template_metadata(titles)
    assert not calls


def test_expand_is_read_only_metadata_not_image_download(monkeypatch):
    response = {"expandtemplates": {"wikitext": "[[File:Exact.svg|label]]"}}
    wiki, calls = fake_wiki(monkeypatch, response)
    assert wiki.expand_template("en", "Source", "{{flag|Example}}") is response
    assert calls == [
        {
            "action": "expandtemplates",
            "title": "Source",
            "text": "{{flag|Example}}",
            "prop": "wikitext",
            "formatversion": 2,
        }
    ]


def test_render_rejects_non_sandbox_before_any_request(monkeypatch):
    wiki, calls = fake_wiki(monkeypatch, {})
    with pytest.raises(GuardError, match="sandbox"):
        wiki.render("Rano", "Text")
    assert not calls


def test_metadata_audit_preserves_restrictions_without_approving_rights_or_contracts(tmp_path):
    (tmp_path / "draft.wiki").write_text("[[File:Exact.svg]] {{Flag|Example}}")
    response = {
        "query": {
            "pages": [
                {
                    "ns": 6,
                    "title": "File:Exact.svg",
                    "missing": True,
                    "imagerepository": "shared",
                    "imageinfo": [
                        {
                            "url": "https://example.invalid/never-fetch.svg",
                            "sha1": "version",
                            "extmetadata": {
                                "LicenseShortName": {"value": "Public domain"},
                                "Restrictions": {"value": "insignia|noresize"},
                            },
                        }
                    ],
                },
                {"ns": 10, "title": "Endrika:Flag", "lastrevid": 12},
            ]
        }
    }
    path = tmp_path / "metadata.json"
    path.write_text(json.dumps(response))
    report = metadata_audit(tmp_path, [path.name])
    image = report["files"][0]
    assert image["metadata"][0]["availability_reported"]
    assert image["metadata"][0]["rights_fields_present"]
    assert not image["license_approved"]
    assert "insignia|noresize" in json.dumps(image)
    assert not report["templates"][0]["metadata"][0]["revision_content_present"]
    assert not report["templates"][0]["parameter_contract_approved"]


def test_metadata_audit_missing_evidence_never_treats_page_image_as_license(tmp_path):
    (tmp_path / "draft.wiki").write_text("[[File:Exact.svg]] {{Flag|Example}}")
    (tmp_path / "country.json").write_text(
        json.dumps(
            {
                "query": {
                    "pages": [
                        {
                            "ns": 0,
                            "title": "Example",
                            "pageprops": {"page_image_free": "Exact.svg"},
                        },
                    ]
                }
            }
        )
    )
    report = metadata_audit(tmp_path, ["country.json"])
    assert report["files"][0]["metadata"] == []
    assert report["templates"][0]["metadata"] == []


def test_source_expansion_file_candidates_require_exact_call_not_guessed_flag(tmp_path):
    (tmp_path / "draft.wiki").write_text("{{flag|Example}}")
    data = {
        "template": "{{flag|Example}}",
        "language": "en",
        "source_sha256": "pin",
        "response": {"expandtemplates": {"wikitext": "[[File:Actual.svg]]"}},
    }
    (tmp_path / "expansion.json").write_text(json.dumps(data))
    report = metadata_audit(tmp_path, ["expansion.json"])
    assert report["files"] == [
        {"filename": "Actual.svg", "metadata": [], "license_approved": False}
    ]
    data["template"] = "{{flag|Another}}"
    (tmp_path / "expansion.json").write_text(json.dumps(data))
    assert metadata_audit(tmp_path, ["expansion.json"])["files"] == []


@pytest.mark.parametrize(
    "data", [[], {"continue": {}}, {"error": {}}, {"query": {"pages": "not a list"}}]
)
def test_metadata_audit_rejects_failed_incomplete_or_malformed_responses(tmp_path, data):
    (tmp_path / "draft.wiki").write_text("Text")
    (tmp_path / "metadata.json").write_text(json.dumps(data))
    with pytest.raises(GuardError):
        metadata_audit(tmp_path, ["metadata.json"])
