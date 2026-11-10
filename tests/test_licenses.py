"""Structured license claims, not legal approval; no URLs fetched."""

import copy
import json

import pytest

from mgwiki_editor import cli
from mgwiki_editor.core import GuardError
from mgwiki_editor.licenses import license_evidence, license_report


def metadata(url="https://creativecommons.org/licenses/by-sa/4.0/"):
    return {"query": {"pages": [{"ns": 6, "title": "Sary:Exact.svg", "missing": True,
        "imagerepository": "shared", "imageinfo": [{
            "timestamp": "2026-11-10T00:00:00Z", "sha1": "a" * 40,
            "url": "https://example.invalid/never-fetch.svg", "extmetadata": {
                "LicenseUrl": {"value": url}, "LicenseShortName": {"value": "CC BY-SA 4.0"},
                "Artist": {"value": '<a href="https://example.invalid/author">Name</a>'},
                "AttributionRequired": {"value": "true"},
                "Restrictions": {"value": "insignia|noresize"},
            },
        }]}]}}


def fields(response):
    return response["query"]["pages"][0]["imageinfo"][0]["extmetadata"]


def test_capsule_retains_version_license_author_and_restrictions_never_approves():
    source = metadata()
    capsule = license_evidence("Exact.svg", source)
    version = capsule["versions"][0]
    assert capsule["availability_reported"] and capsule["local_description_missing"]
    assert capsule["origin"] == "unverified_cached_input"
    assert version["version_fields_present"] and version["restriction_review_required"]
    assert version["rights_fields"]["Restrictions"]["value"] == "insignia|noresize"
    assert version["license_identity"] == "cc_by_sa_4.0"
    assert "share_alike_for_adaptations" in version["reported_obligations"]
    assert version["attribution_text_present"]
    assert not capsule["license_approved"] and not version["license_approved"]
    assert capsule["response"] == source


@pytest.mark.parametrize("url", [
    "https://creativecommons.org.evil.invalid/licenses/by-sa/4.0/",
    "https://creativecommons.org/licenses/by-sa/4.0/fake",
    "https://user:secret@creativecommons.org/licenses/by-sa/4.0/",
    "https://creativecommons.org/licenses/by-sa/4.0/?redirect=other",
    "not a URL",
])
def test_lookalike_or_noncanonical_license_uri_never_recognized(url):
    result = license_evidence("Exact.svg", metadata(url))["versions"][0]
    assert result["license_identity"] == "unrecognized"
    assert result["metadata_assessment"] == "insufficient_rights_evidence"


@pytest.mark.parametrize("kind", ["by-nc", "by-nd", "by-nc-sa", "by-nc-nd"])
def test_restricted_creative_commons_terms_not_free_reuse_candidates(kind):
    result = license_evidence("Exact.svg", metadata(
        f"https://creativecommons.org/licenses/{kind}/4.0/"))["versions"][0]
    assert result["metadata_assessment"] == "not_a_free_reuse_candidate"


def test_nonfree_flag_overrides_free_uri_and_false_attribution_flags_conflict():
    data = metadata()
    fields(data)["NonFree"] = {"value": "true"}
    assert license_evidence("Exact.svg", data)["versions"][0]["metadata_assessment"] == (
        "not_a_free_reuse_candidate")
    fields(data).pop("NonFree")
    fields(data)["AttributionRequired"] = {"value": "false"}
    assert license_evidence("Exact.svg", data)["versions"][0]["metadata_assessment"] == (
        "conflicting_metadata_needs_review")


def test_public_domain_claim_without_url_not_fabricated_license_grant():
    data = metadata()
    fields(data).pop("LicenseUrl")
    fields(data)["Copyrighted"] = {"value": "False"}
    result = license_evidence("Exact.svg", data)["versions"][0]
    assert result["metadata_assessment"] == "public_domain_claim_needs_review"
    assert not result["license_approved"]


def test_missing_file_and_wrong_file_not_silently_accepted():
    data = metadata()
    data["query"]["pages"][0]["imageinfo"] = []
    assert not license_evidence("Exact.svg", data)["availability_reported"]
    with pytest.raises(GuardError, match="Exact requested"):
        license_evidence("Other.svg", data)
    for filename in ("File:Exact.svg", "https://example.invalid/x", False):
        with pytest.raises(GuardError):
            license_evidence(filename, data)


@pytest.mark.parametrize("data", [[], {"error": {}}, {"continue": {}}, {"query": "invalid"}])
def test_malformed_or_failed_response_cannot_be_license_evidence(data):
    with pytest.raises(GuardError):
        license_evidence("Exact.svg", data)


def test_offline_report_ignores_forged_origin_and_cannot_change_original(tmp_path):
    source = {"origin": "broker_image_info_read", "license_approved": True, "response": metadata()}
    path = tmp_path / "metadata.json"
    path.write_text(json.dumps(source))
    before = path.read_bytes()
    result = license_report(tmp_path, path.name, "Exact.svg")
    assert result["origin"] == "unverified_cached_input" and not result["license_approved"]
    assert path.read_bytes() == before


def test_license_report_cli_is_offline_and_exclusive(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("MGWIKI_BROKER_SOCKET", raising=False)
    monkeypatch.delenv("MGWIKI_CAPABILITY_FILE", raising=False)
    monkeypatch.setattr(cli, "Wiki", lambda: pytest.fail("Offline report contacted Wiki"))
    (tmp_path / "metadata.json").write_text(json.dumps(metadata()))
    before = copy.deepcopy(metadata())
    output = tmp_path / "license.json"
    args = ["license-report", "--job", str(tmp_path), "--evidence", "metadata.json",
            "--filename", "Exact.svg", "--output", str(output)]
    assert cli.main(args) == 0
    assert json.loads(capsys.readouterr().out)["response"] == before
    assert cli.main(args) == 1


def test_license_capture_uses_existing_wiki_without_broker_or_credential_setup(
    tmp_path, monkeypatch, capsys,
):
    monkeypatch.delenv("MGWIKI_BROKER_SOCKET", raising=False)
    monkeypatch.delenv("MGWIKI_CAPABILITY_FILE", raising=False)
    from mgwiki_editor import control

    monkeypatch.setattr(control, "client", lambda *a: pytest.fail("Optional broker contacted"))
    calls = []
    class ExistingWiki:
        def file_metadata(self, filename):
            calls.append(filename)
            return metadata()

    monkeypatch.setattr(cli, "Wiki", ExistingWiki)
    monkeypatch.setattr(cli.time, "time", lambda: 1234)
    output = tmp_path / "license.json"
    assert cli.main(["license-evidence", "--filename", "Exact.svg", "--output", str(output)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert calls == ["Exact.svg"]
    assert result["origin"] == "wiki_image_info_read" and result["captured_at"] == 1234
    assert result["source_api"] == "https://mg.wikipedia.org/w/api.php"
    assert not result["license_approved"]
    assert json.loads(output.read_bytes()) == result
    # Cached claims never acquire authenticated broker origin from their own label.
    cached = license_report(tmp_path, output.name, "Exact.svg")
    assert cached["origin"] == "unverified_cached_input"


@pytest.mark.parametrize("filename", ["File:Exact.svg", "https://example.invalid/x"])
def test_direct_license_capture_rejects_unsafe_names_before_request(monkeypatch, capsys, filename):
    monkeypatch.delenv("MGWIKI_BROKER_SOCKET", raising=False)
    monkeypatch.delenv("MGWIKI_CAPABILITY_FILE", raising=False)
    class ExistingWiki:
        def file_metadata(self, filename):
            pytest.fail("Invalid filename reached Wikipedia")

    monkeypatch.setattr(cli, "Wiki", ExistingWiki)
    assert cli.main(["license-evidence", "--filename", filename]) == 1
    assert json.loads(capsys.readouterr().err)["error"] == "GuardError"


def test_direct_license_capture_preserves_guard_failure(monkeypatch, capsys):
    monkeypatch.delenv("MGWIKI_BROKER_SOCKET", raising=False)
    monkeypatch.delenv("MGWIKI_CAPABILITY_FILE", raising=False)
    class ExistingWiki:
        def file_metadata(self, filename):
            raise GuardError("Shared transport cooldown; deferred")

    monkeypatch.setattr(cli, "Wiki", ExistingWiki)
    assert cli.main(["license-evidence", "--filename", "Exact.svg"]) == 1
    assert json.loads(capsys.readouterr().err)["message"] == "Shared transport cooldown; deferred"
