"""Country spelling cache tests with no live Wikipedia access."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from mgwiki_editor.core import (
    COUNTRY_CACHE,
    COUNTRY_CATEGORY,
    GuardError,
    Wiki,
    country_names,
    write_json,
)


def test_refresh_then_reuse_offline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Fetch once, preserve exact spellings, and never fetch during cached reads."""
    monkeypatch.chdir(tmp_path)
    calls = []

    def fetch():
        calls.append("fetch")
        return ["Nôrvezy", "Etazonia", "Frantsa", "Nôrvezy"]

    result = country_names(SimpleNamespace(country_titles=fetch), refresh=True)
    assert calls == ["fetch"]
    assert result["category"] == "Sokajy:Firenena"
    assert result["scope"] == "direct_mainspace_members"
    assert result["titles"] == ["Etazonia", "Frantsa", "Nôrvezy"]
    assert COUNTRY_CACHE.is_file()
    # An object without network methods proves cached reads do not use the gateway.
    assert country_names(object()) == result
    assert calls == ["fetch"]


def test_missing_cache_requires_explicit_refresh(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A normal command must not silently start a remote category fetch."""
    monkeypatch.chdir(tmp_path)
    with pytest.raises(GuardError, match="countries --refresh"):
        country_names(object())
    assert not COUNTRY_CACHE.exists()


@pytest.mark.parametrize("failure", ["network", "empty", "namespace", "markup"])
def test_failed_refresh_preserves_previous_cache(
    failure: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An outage or invalid response cannot replace usable spellings."""
    monkeypatch.chdir(tmp_path)
    country_names(SimpleNamespace(country_titles=lambda: ["Etazonia"]), refresh=True)
    before = COUNTRY_CACHE.read_bytes()

    def fetch():
        if failure == "network":
            raise OSError("offline")
        return {"empty": [], "namespace": ["Sokajy:Firenena"], "markup": ["[[Etazonia]]"]}[
            failure
        ]

    with pytest.raises((GuardError, OSError)):
        country_names(SimpleNamespace(country_titles=fetch), refresh=True)
    assert COUNTRY_CACHE.read_bytes() == before


@pytest.mark.parametrize("field,value", [
    ("language", "en"), ("category", "Sokajy:Hafa"), ("scope", "recursive"),
    ("titles", []), ("titles", [None]), ("titles", ["User:Other"]),
    ("titles", ["Etazonia", "Etazonia"]), ("titles", ["Frantsa", "Etazonia"]),
    ("retrieved_at", None),
])
def test_rejects_invalid_cached_data(
    field: str, value: object, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Do not use altered identity, invalid titles or an empty cached list."""
    monkeypatch.chdir(tmp_path)
    result = country_names(SimpleNamespace(country_titles=lambda: ["Etazonia"]), refresh=True)
    result[field] = value
    write_json(COUNTRY_CACHE, result)
    with pytest.raises(GuardError):
        country_names(object())


def test_gateway_lists_only_direct_mainspace_members(monkeypatch: pytest.MonkeyPatch) -> None:
    """Use the fixed mg category without reading articles or traversing subcategories."""
    import pywikibot

    wiki = Wiki()
    marker = object()
    calls = []

    def site(language):
        assert language == "mg"
        return marker

    def category(site, name):
        assert site is marker
        assert name == COUNTRY_CATEGORY == "Sokajy:Firenena"

        def articles(**kwargs):
            calls.append(kwargs)
            return [
                SimpleNamespace(title=lambda: "Etazonia", namespace=lambda: 0),
                SimpleNamespace(title=lambda: "Sokajy:Hafa", namespace=lambda: 14),
            ]

        return SimpleNamespace(articles=articles)

    monkeypatch.setattr(wiki, "site", site)
    monkeypatch.setattr(pywikibot, "Category", category)
    assert wiki.country_titles() == ["Etazonia"]
    assert calls == [{"namespaces": 0, "recurse": False}]
