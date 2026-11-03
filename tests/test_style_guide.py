"""Offline reference/markup regressions, not proof of Malagasy linguistic quality."""

from pathlib import Path

import pytest

from mgwiki_editor.core import lint_wikitext

STYLE = Path(__file__).resolve().parents[1] / ".opencode/skills/mgwiki-style"


@pytest.mark.parametrize("name, revision", [
    ("manual-of-style.wiki", "1381654087"),
    ("words-to-watch.wiki", "1382059772"),
])
def test_style_references_are_local_required_and_attributed(name: str, revision: str) -> None:
    """Style loading must lead to offline guidance with exact upstream provenance."""
    skill = (STYLE / "SKILL.md").read_text(encoding="utf-8")
    assert f"references/{name}" in skill
    reference = (STYLE / "references" / name).read_text(encoding="utf-8")
    assert "oldid=" + revision in reference
    assert "Wikipedia contributors" in reference
    assert "Creative Commons Attribution-ShareAlike 4.0" in reference


def test_malagasy_style_examples_are_valid_wikitext() -> None:
    """Elision spacing and italic originals must not break wiki emphasis/citations."""
    article = """'''Ohatra''' amin' ny fanoratana amin' izao fotoana izao.
WHO (Fikambanana Iraisam-pirenena momba ny Fahasalamana).
''National Aeronautics and Space Administration'' (sampan-draharaha momba ny
habakabaka sy ny fiaramanidina).
Teny vahiny: ''soprano''; boky: ''L'Étranger''; sarimihetsika: ''Metropolis'';
lahatsoratra: ''On the Electrodynamics of Moving Bodies''.
An' Andriamanitra; O'Connor; Kim Dae-jung; Nguyễn Phú Trọng.
<ref name="source">Original Author. ''The Greatest Show''.
"This is a legendary, revolutionary discovery", hoy ny loharano.
[https://example.org/amin'ny Original title].</ref>
== Loharano ==
<references />
"""
    assert lint_wikitext(article) == []


@pytest.mark.parametrize("protected", [
    '"legendary, alleged, controversial"',
    "''The Greatest Show''",
    '<ref>Original title: "A revolutionary claim".</ref><references />',
])
def test_words_to_watch_are_not_a_forbidden_token_filter(protected: str) -> None:
    """Context-sensitive editorial caution must not ban faithful source wording."""
    assert lint_wikitext(protected) == []


def test_words_to_watch_preserves_all_source_warning_groups() -> None:
    """The saved adaptation includes the complete section-level review checklist."""
    text = (STYLE / "references/words-to-watch.wiki").read_text(encoding="utf-8")
    for heading in (
        "Puffery and peacock language", "Contentious labels",
        "Unsupported attributions and weasel language", "Expressions of doubt and scare quotes",
        "Editorializing and implied relationships", "Loaded substitutes for said", "Euphemisms",
        "Cliches and idioms", "Relative time", "Unspecified places or events",
        "Obituary-style survived by", "Person versus office", "Neologisms and new compounds",
        "Easily confused terms", "Vulgarities, obscenities, and profanities",
    ):
        assert f"== {heading} ==" in text
