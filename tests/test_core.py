"""Offline tests: no test logs in, renders remotely, or edits Wikimedia."""

from __future__ import annotations

import copy
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError, URLError

import pytest

from mgwiki_editor import core
from mgwiki_editor.core import (
    GATES,
    PYWIKIBOT_DIR,
    GuardError,
    Wiki,
    digest,
    initialize,
    job_path,
    lint_wikitext,
    lookup,
    prepare,
    publish,
    read_json,
    sandbox_title,
    write_json,
)
from mgwiki_editor.vocabulary import vocabulary

ARTICLE = "'''Rano''' dia ranoka.\n\n== Loharano ==\n<references />\n"


class FakeWiki:
    """Deterministic in-memory gateway with explicit save accounting."""

    def __init__(self) -> None:
        """Start with an English source and no Malagasy pages."""
        self.pages: dict[tuple[str, str], dict] = {}
        self.saves: list[tuple] = []
        self.html = "<p>Rano</p>"
        self.fail_save = False
        self.mismatch_readback = False
        self.put("en", "Water", "Source article", 11)

    def put(self, language: str, title: str, text: str, revision: int | None) -> None:
        """Set one fake snapshot."""
        self.pages[language, title] = {
            "language": language, "title": title, "requested_title": title,
            "revision_id": revision, "timestamp": "2026-11-03T10:00:00Z" if revision else None,
            "text": text, "sha256": digest(text.encode()),
            "url": f"https://{language}.wikipedia.org/w/index.php?oldid={revision}",
        }

    def snapshot(self, language: str, title: str, *, sandbox: bool = False) -> dict:
        """Return isolated fake evidence."""
        if (language, title) not in self.pages:
            self.put(language, title, "", None)
        return copy.deepcopy(self.pages[language, title])

    def existing_title(self, language: str, title: str, fallback: str) -> str:
        """Use the supplied Malagasy fallback."""
        return fallback

    def render(self, destination: str, text: str) -> str:
        """Return a stable offline rendering."""
        return self.html

    def save(self, destination: str, text: str, base: dict, summary: str) -> None:
        """Record a save or simulate an uncertain connection failure."""
        self.saves.append((destination, text, base, summary))
        if self.fail_save:
            raise OSError("connection lost after submission")
        self.put("mg", destination, "unexpected" if self.mismatch_readback else text, 99)


@pytest.fixture
def job(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[FakeWiki, Path]:
    """Create an initialized offline job with completed editorial attestations."""
    monkeypatch.chdir(tmp_path)
    wiki = FakeWiki()
    path = tmp_path / "runs" / "water"
    initialize(wiki, path, "en", "Water", "Rano")
    (path / "draft.wiki").write_text(ARTICLE, encoding="utf-8")
    (path / "notes.wiki").write_text(
        "# Review\nAll intended sections compared.\n", encoding="utf-8",
    )
    write_json(path / "review.json", dict.fromkeys(GATES, True))
    return wiki, path


@pytest.mark.parametrize("value", [
    "", "X#fragment", "X\nY", "[X]", "User:Other/X", "Mpikambana:Other/X",
])
def test_invalid_sandbox_titles(value: str) -> None:
    """Never accept a caller-selected user namespace or fragment."""
    with pytest.raises(GuardError):
        sandbox_title(value)


def test_valid_sandbox_title() -> None:
    """Construct the fixed destination without losing valid article punctuation."""
    assert sandbox_title(" Rano_madio ") == "Mpikambana:Bot-Jagwar/Rano madio"
    assert sandbox_title("Star Trek: Voyager") == "Mpikambana:Bot-Jagwar/Star Trek: Voyager"


def test_job_path_confined(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Reject sibling trees and symlink escapes."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "runs").mkdir()
    (tmp_path / "runs" / "escape").symlink_to(tmp_path)
    for path in (tmp_path / "outside", tmp_path / "runs", tmp_path / "runs" / "escape" / "x"):
        with pytest.raises(GuardError):
            job_path(path)


def test_dictionary_filters_language_and_keeps_evidence() -> None:
    """A Malagasy Wiktionary page must not yield unrelated language senses."""
    raw = [
        {"entry": "rano", "language": "mg", "definitions": ["ranoka"]},
        {"entry": "rano", "language": "eo", "definitions": ["sahona"]},
    ]
    calls = []

    def opener(request, timeout):
        calls.append((request, timeout))
        return io.BytesIO(json.dumps(raw).encode())

    result = lookup("mg", "rano manga", opener=opener)
    assert result["entries"] == raw[:1]
    assert result["raw_entries"] == raw
    assert calls[0][0].get_method() == "GET"
    assert calls[0][0].full_url.endswith("/wiktionary-pages/mg/rano%20manga")
    assert calls[0][1] == 20


@pytest.mark.parametrize("edition", ["en", "mg"])
def test_dictionary_edition_filter(edition: str) -> None:
    """Filter the entry language for either edition."""
    raw = [{"language": edition, "definitions": ["sense"]},
           {"language": "fr", "definitions": ["other"]}]
    result = lookup(edition, "term", opener=lambda *a, **k: io.BytesIO(json.dumps(raw).encode()))
    assert len(result["entries"]) == 1
    assert result["entries"][0]["language"] == edition


@pytest.mark.parametrize("status", [404, 500])
def test_dictionary_http_errors_distinguish_misses(status: int) -> None:
    """An outage must not be interpreted as a missing word."""
    def opener(*args, **kwargs):
        raise HTTPError("http://example.org", status, "error", {}, None)

    if status == 404:
        assert lookup("mg", "x", opener=opener)["status"] == "missing"
    else:
        with pytest.raises(GuardError, match="not a dictionary miss"):
            lookup("mg", "x", opener=opener)


@pytest.mark.parametrize("data", [
    b"not JSON", b"{}", b'[{}]', b'[{"language":"mg","definitions":1}]',
])
def test_dictionary_rejects_bad_schema(data: bytes) -> None:
    """Do not convert malformed definitions into translation evidence."""
    with pytest.raises(GuardError):
        lookup("mg", "x", opener=lambda *a, **k: io.BytesIO(data))


def test_dictionary_network_failure() -> None:
    """Fail closed on an unreachable service."""
    def opener(*args, **kwargs):
        raise URLError("offline")

    with pytest.raises(GuardError, match="unavailable"):
        lookup("en", "x", opener=opener)


@pytest.mark.parametrize("base", ["file:///etc", "http://user:pass@host", "http://host/translations"])
def test_dictionary_rejects_non_origin_base(base: str) -> None:
    """Do not route dictionary requests through arbitrary endpoint paths."""
    with pytest.raises(GuardError):
        lookup("mg", "x", base_url=base)


@pytest.mark.parametrize("text", [
    "```wiki\nX\n```", "`X`", "**X**", "*italic*", "[X](https://example.org)",
    "![X](url)", "- [x] Done", "- Item", "1. Item", "---", "| --- | --- |",
    "[[:Sokajy:Rano]]", "[[Category:Water]]", "[[en:Water]]", "#REDIRECT [[X]]",
    "TODO translate", '<ref name="missing" /><references />', '<ref>Source</ref>',
])
def test_lint_rejects_markdown_and_structural_problems(text: str) -> None:
    """Catch common Markdown and unsafe sandbox/citation output."""
    assert lint_wikitext(text)


def test_lint_accepts_mediawiki_lists_tables_and_references() -> None:
    """Shared list characters must not produce false Markdown errors."""
    text = """'''Rano''' dia ''ranoka''.
== Lohateny ==
* Singa iray
** Zana-tsinga
# Voalohany
## Zana-tsinga
[[Sokajy:Rano]] [[:Category:Water]] [[Rano|rohy]] [https://example.org loharano]
{| class="wikitable"
|-
! Lohateny !! Lohateny
|-
| Iray || Roa
|}
<ref name="a">Loharano</ref><ref name="a" />
<ref group="note" name="n">Fanamarihana</ref><ref group="note" name="n" />
<references /><references group="note" />
"""
    assert lint_wikitext(text) == []


def test_math_operators_are_not_markdown() -> None:
    """Keep native mathematical multiplication valid."""
    assert lint_wikitext("<math>a*b*c</math>") == []


@pytest.mark.parametrize("tag", ["code", "pre", "nowiki", "syntaxhighlight", "source"])
@pytest.mark.parametrize("literal", [
    "const s = `template string`;", "x = a*b*c", "**literal asterisks**",
    "- [x] literal checklist", "1. literal numbered text", "| --- | --- |",
])
def test_markdown_characters_inside_literal_code_are_not_article_markdown(
    tag: str, literal: str,
) -> None:
    assert lint_wikitext(f"<{tag}>{literal}</{tag}>") == []


@pytest.mark.parametrize("tag", ["code", "pre", "nowiki", "syntaxhighlight", "source"])
def test_protected_code_does_not_exempt_surrounding_markdown_or_other_guards(tag: str) -> None:
    assert "Markdown emphasis." in lint_wikitext(f"<{tag}>literal</{tag}>\n**Markdown**")
    assert "Unsafe HTML element." in lint_wikitext(f"<{tag}><script>bad</script></{tag}>")
    assert "Unresolved editorial placeholder." in lint_wikitext(f"<{tag}>TODO</{tag}>")


def test_init_preserves_existing_and_sandbox(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Existing sandbox is the initial draft, not disposable workspace."""
    monkeypatch.chdir(tmp_path)
    wiki = FakeWiki()
    wiki.put("mg", "Rano", "Mainspace additions", 22)
    wiki.put("mg", "Mpikambana:Bot-Jagwar/Rano", "Sandbox work", 33)
    path = tmp_path / "runs" / "existing"
    state = initialize(wiki, path, "en", "Water", "Rano")
    assert state["destination"] == "Mpikambana:Bot-Jagwar/Rano"
    assert state["sandbox"]["requested_title"] == "Mpikambana:Bot-Jagwar/Rano"
    assert state["existing"]["revision_id"] == 22
    assert (path / "draft.wiki").read_text() == "Sandbox work"
    assert (path / "existing.wiki").read_text() == "Mainspace additions"
    assert wiki.saves == []
    with pytest.raises(GuardError, match="already exists"):
        initialize(wiki, path, "en", "Water", "Rano")


def test_prepare_and_publish_exact_draft(job: tuple[FakeWiki, Path]) -> None:
    """Preparation never saves; approved publication reads back exact bytes."""
    wiki, path = job
    proposal = prepare(wiki, path)
    assert not wiki.saves
    assert "oldid=11" in proposal["summary"]
    assert proposal["summary"].startswith("Dika amin' ny teny malagasy: ")
    receipt = publish(wiki, path, proposal["digest"])
    assert receipt["status"] == "confirmed"
    assert receipt["revision_id"] == 99
    assert len(wiki.saves) == 1
    assert wiki.saves[0][1] == ARTICLE


def test_autonomous_publish_keeps_exact_proposal_guards(job: tuple[FakeWiki, Path]) -> None:
    """Autonomous mode still binds content and records the exact prepared digest."""
    wiki, path = job
    proposal = prepare(wiki, path)
    receipt = publish(wiki, path)
    assert receipt["status"] == "confirmed"
    assert receipt["mode"] == "autonomous"
    assert receipt["proposal_digest"] == proposal["digest"]
    assert len(wiki.saves) == 1


def test_autonomous_publish_rejects_tampered_proposal(job: tuple[FakeWiki, Path]) -> None:
    """No approval prompt does not mean no proposal-integrity check."""
    wiki, path = job
    proposal = prepare(wiki, path)
    proposal["summary"] = "Tampered attribution"
    write_json(path / "proposal.json", proposal)
    with pytest.raises(GuardError, match="digest"):
        publish(wiki, path)
    assert not wiki.saves


def test_autonomous_publish_rejects_changed_draft(job: tuple[FakeWiki, Path]) -> None:
    """Fresh preparation is mandatory after autonomous draft changes too."""
    wiki, path = job
    prepare(wiki, path)
    (path / "draft.wiki").write_text(ARTICLE + "Changed", encoding="utf-8")
    with pytest.raises(GuardError, match="changed"):
        publish(wiki, path)
    assert not wiki.saves


@pytest.mark.parametrize("phase", ["prepare", "publish"])
@pytest.mark.parametrize("filename", [
    "draft.wiki", "job.json", "review.json", "vocabulary.json", "notes.wiki",
])
def test_consumed_artifacts_are_bound_even_when_a_concurrent_edit_is_reverted(
    job: tuple[FakeWiki, Path], monkeypatch: pytest.MonkeyPatch, phase: str, filename: str,
) -> None:
    """A→B→A on disk cannot approve/render/save the transient B captured in memory."""
    wiki, path = job
    if phase == "publish":
        prepare(wiki, path)
    target = path / filename
    original = target.read_bytes()
    changed = original + (b"<!-- unreviewed edit -->" if filename.endswith(".wiki") else b" ")
    original_hashes, original_read = core.artifact_hashes, Path.read_bytes
    armed, injected = False, False

    def hashes_then_edit(directory):
        nonlocal armed, injected
        result = original_hashes(directory)
        if not injected:
            target.write_bytes(changed)
            armed = injected = True
        return result

    def read_then_restore(filename_path):
        nonlocal armed
        raw = original_read(filename_path)
        if armed and filename_path == target:
            target.write_bytes(original)
            armed = False
        return raw

    monkeypatch.setattr(core, "artifact_hashes", hashes_then_edit)
    monkeypatch.setattr(Path, "read_bytes", read_then_restore)
    with pytest.raises(GuardError, match=f"Captured {filename} changed"):
        (prepare if phase == "prepare" else publish)(wiki, path)
    assert original_read(target) == original
    assert not wiki.saves
    assert not (path / "receipt.json").exists()


@pytest.mark.parametrize("filename", [
    "draft.wiki", "notes.wiki", "source-issues.md", "review.json", "vocabulary.json",
    "preview.html", "changes.diff",
])
def test_changed_artifact_invalidates_approval(job: tuple[FakeWiki, Path], filename: str) -> None:
    """Any post-proposal draft, evidence, or preview mutation invalidates approval."""
    wiki, path = job
    proposal = prepare(wiki, path)
    with (path / filename).open("ab") as stream:
        stream.write(b" ")
    with pytest.raises(GuardError, match="changed"):
        publish(wiki, path, proposal["digest"])
    assert not wiki.saves


def test_initialize_uses_non_wiki_memory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """New operational notes are Markdown, not article wikitext."""
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "runs" / "memory"
    wiki = FakeWiki()
    initialize(wiki, path, "en", "Water", "Rano")
    assert (path / "notes.wiki").read_text(encoding="utf-8") == "# Edition notes\n"
    assert (path / "source-issues.md").read_text(encoding="utf-8") == (
        "# Source issues\n\nNone recorded. Review pending.\n"
    )
    assert not wiki.saves


def test_open_source_issues_do_not_block_publication(job: tuple[FakeWiki, Path]) -> None:
    """Source disagreement is durable evidence, not an unresolved vocabulary gate."""
    wiki, path = job
    memory = (
        "# Source issues\n\n## SRC-001\n"
        "Status: open; nonblocking. Article: Rano; job: runs/water.\n"
        "Evidence: source.wiki; en:Water revision 11; lead vs history.\n"
        "Claims: A says 1900 (ref A); B says 1901 (ref B).\n"
        "Draft: attribution retained. Next: user review.\n"
    )
    (path / "source-issues.md").write_text(memory, encoding="utf-8")
    proposal = prepare(wiki, path)
    assert proposal["artifacts"]["source-issues.md"] == digest(memory.encode("utf-8"))
    receipt = publish(wiki, path)
    assert receipt["status"] == "confirmed"
    assert (path / "source-issues.md").read_text(encoding="utf-8") == memory
    assert wiki.saves[0][1] == ARTICLE
    assert "SRC-001" not in wiki.saves[0][1]


@pytest.mark.parametrize("present_before", [False, True])
def test_source_issue_memory_addition_or_removal_requires_prepare(
    job: tuple[FakeWiki, Path], present_before: bool,
) -> None:
    """Optional-memory set changes still invalidate the exact prepared proposal."""
    wiki, path = job
    memory = path / "source-issues.md"
    if not present_before:
        memory.unlink()
    prepare(wiki, path)
    if present_before:
        memory.unlink()
    else:
        memory.write_text("# Source issues\nNone recorded.\n", encoding="utf-8")
    with pytest.raises(GuardError, match="changed"):
        publish(wiki, path)
    assert not wiki.saves


def test_legacy_job_without_source_issue_memory_can_publish(job: tuple[FakeWiki, Path]) -> None:
    """Existing jobs need no evidence rewrite solely to adopt the new memory file."""
    wiki, path = job
    (path / "source-issues.md").unlink()
    proposal = prepare(wiki, path)
    assert "source-issues.md" not in proposal["artifacts"]
    assert publish(wiki, path)["status"] == "confirmed"


def test_wrong_digest_cannot_publish(job: tuple[FakeWiki, Path]) -> None:
    """A generic yes or truncated digest is not an approval token."""
    wiki, path = job
    prepare(wiki, path)
    with pytest.raises(GuardError, match="Approval"):
        publish(wiki, path, "yes")
    assert not wiki.saves


def test_legacy_job_requires_fresh_initialization(job: tuple[FakeWiki, Path]) -> None:
    """Reject old-owner jobs rather than silently retargeting their evidence."""
    wiki, path = job
    state = read_json(path / "job.json")
    state["destination"] = "Mpikambana:Jagwar/Rano"
    write_json(path / "job.json", state)
    with pytest.raises(GuardError, match="outside Bot-Jagwar's sandbox"):
        prepare(wiki, path)
    assert not (path / "proposal.json").exists()
    assert not wiki.saves


def test_unreviewed_gate_blocks_prepare(job: tuple[FakeWiki, Path]) -> None:
    """Editorial attestations are mandatory, including existing-work review."""
    wiki, path = job
    review = read_json(path / "review.json")
    review["existing_preserved"] = False
    write_json(path / "review.json", review)
    with pytest.raises(GuardError, match="existing_preserved"):
        prepare(wiki, path)


@pytest.mark.parametrize("which", ["source", "existing", "sandbox"])
def test_stale_snapshot_blocks_publish(job: tuple[FakeWiki, Path], which: str) -> None:
    """A source change, mainspace edit, or newly created sandbox needs a fresh merge."""
    wiki, path = job
    proposal = prepare(wiki, path)
    old = read_json(path / "job.json")[which]
    wiki.put(old["language"], old["requested_title"], "Other editor's work", 55)
    with pytest.raises(GuardError, match="Snapshot changed"):
        publish(wiki, path, proposal["digest"])
    assert not wiki.saves


def test_changed_rendering_blocks_publish(job: tuple[FakeWiki, Path]) -> None:
    """Template changes cannot silently change an approved rendered article."""
    wiki, path = job
    proposal = prepare(wiki, path)
    wiki.html = "<p>Changed template output</p>"
    with pytest.raises(GuardError, match="rendering changed"):
        publish(wiki, path, proposal["digest"])


@pytest.mark.parametrize("failure", ["fail_save", "mismatch_readback"])
def test_uncertain_save_has_receipt_and_cannot_retry(
    job: tuple[FakeWiki, Path], failure: str,
) -> None:
    """Timeouts and read-back mismatches never become false success or blind retries."""
    wiki, path = job
    proposal = prepare(wiki, path)
    setattr(wiki, failure, True)
    with pytest.raises((OSError, GuardError)):
        publish(wiki, path, proposal["digest"])
    assert read_json(path / "receipt.json")["status"] == "unconfirmed"
    with pytest.raises(GuardError):
        publish(wiki, path, proposal["digest"])
    assert len(wiki.saves) == 1
    with pytest.raises(GuardError, match="save attempt"):
        prepare(wiki, path)


def test_vocabulary_evidence_is_bound(job: tuple[FakeWiki, Path]) -> None:
    """Sense evidence is part of the exact proposal, not just the memo text."""
    wiki, path = job
    write_json(path / "lookup-en.json", {"entries": ["definition"]})
    write_json(path / "vocabulary.json", [{
        "status": "descriptive", "source_sense": "domain sense",
        "chosen_expression": "phrase", "malagasy_definition": "explanation",
        "evidence_files": ["lookup-en.json"],
    }])
    proposal = prepare(wiki, path)
    write_json(path / "lookup-en.json", {"entries": ["changed definition"]})
    with pytest.raises(GuardError, match="changed"):
        publish(wiki, path, proposal["digest"])


@pytest.mark.parametrize("filename", [
    "unknown-vocabulary.wiki", "user-vocabulary.wiki", "country-names.json", "kajy-equation.json",
])
def test_supplemental_terminology_evidence_is_bound(
    job: tuple[FakeWiki, Path], filename: str,
) -> None:
    """Deferred terms, user corrections and pinned country spellings bind approval."""
    wiki, path = job
    (path / filename).write_text("{}\n" if filename.endswith(".json") else "= Evidence =\n")
    write_json(path / "vocabulary.json", [{
        "status": "descriptive", "source_sense": "unambiguous source sense",
        "chosen_expression": "clear descriptive wording", "malagasy_definition": "fanazavana",
        "evidence_files": [filename],
    }])
    proposal = prepare(wiki, path)
    assert filename in proposal["artifacts"]
    with (path / filename).open("a") as stream:
        stream.write(" ")
    with pytest.raises(GuardError, match="evidence changed"):
        publish(wiki, path, proposal["digest"])
    assert not wiki.saves


def test_unresolved_vocabulary_blocks_prepare(job: tuple[FakeWiki, Path]) -> None:
    """Do not publish unresolved sense choices."""
    wiki, path = job
    write_json(path / "vocabulary.json", [{"status": "unresolved", "evidence_files": []}])
    with pytest.raises(GuardError, match="Vocabulary"):
        prepare(wiki, path)


def test_dictionary_502_alone_does_not_block_reviewed_descriptive_publication(
    job: tuple[FakeWiki, Path],
) -> None:
    """Dictionary outage evidence does not waive or fail independent editorial gates."""
    from mgwiki_editor.dictionary_retries import DictionaryRetries

    wiki, path = job

    def opener(*args, **kwargs):
        raise HTTPError("http://dictionary", 502, "Bad Gateway", {}, io.BytesIO(b"timeout"))

    evidence = lookup("en", "term", opener=opener,
                      retries=DictionaryRetries(path / "retry-state.json"))
    assert evidence["status"] == "failed"
    write_json(path / "dictionary-failure.json", evidence)
    write_json(path / "vocabulary.json", [{
        "status": "descriptive", "source_sense": "clear source-context meaning",
        "chosen_expression": "fanazavana", "malagasy_definition": "fanazavana mazava",
        "evidence_files": ["dictionary-failure.json"],
    }])
    prepare(wiki, path)
    assert publish(wiki, path)["status"] == "confirmed"
    assert len(wiki.saves) == 1


def test_pinned_sqlite_lookup_survives_shared_database_change(job: tuple[FakeWiki, Path]) -> None:
    """Prepared jobs depend on exact query evidence, never on a mutable shared database."""
    wiki, path = job
    source = Path(__file__).resolve().parents[1] / "data/vocabulary/kajy-mathematics.sqlite"
    temporary_db = path.parent / "reference.sqlite"
    temporary_db.write_bytes(source.read_bytes())
    evidence = vocabulary("equation", exact=True, cache=temporary_db)
    assert evidence["entries"][0]["source_number"] == 102
    write_json(path / "kajy-equation.json", evidence)
    write_json(path / "vocabulary.json", [{
        "status": "descriptive", "source_sense": "mathematical equation",
        "chosen_expression": "fampimirana", "malagasy_definition": "fanazavana",
        "evidence_files": ["kajy-equation.json"], "source_numbers": [102],
    }])
    proposal = prepare(wiki, path)
    assert proposal["artifacts"]["kajy-equation.json"] == digest(
        (path / "kajy-equation.json").read_bytes(),
    )
    temporary_db.write_bytes(b"shared database changed after evidence was pinned")
    assert publish(wiki, path)["status"] == "confirmed"


class FakePage:
    """Minimal page boundary for testing actual gateway save flags."""

    def __init__(self) -> None:
        """Keep all Pywikibot writes observable."""
        self.calls: list[dict] = []
        self.text = ""

    def namespace(self) -> int:
        """Return the user namespace."""
        return 2

    def title(self, **kwargs) -> str:
        """Return the title without namespace for owner checks."""
        return "Bot-Jagwar/Rano"

    def save(self, **kwargs) -> None:
        """Capture save parameters without contacting Wikimedia."""
        self.calls.append(kwargs)


@pytest.mark.parametrize("revision", [None, 33])
def test_pywikibot_write_guards(revision: int | None, monkeypatch: pytest.MonkeyPatch) -> None:
    """Exercise real gateway logic with fake Pywikibot account/page boundaries."""
    wiki = Wiki()
    page = FakePage()
    site = SimpleNamespace(code="mg", family=SimpleNamespace(name="wikipedia"),
                           hostname=lambda: "mg.wikipedia.org", login=lambda: None,
                           user=lambda: "Bot-Jagwar")
    base = FakeWiki().snapshot("mg", "Mpikambana:Bot-Jagwar/Rano", sandbox=True)
    base["revision_id"] = revision
    base["timestamp"] = "2026-11-03T10:00:00Z" if revision else None
    monkeypatch.setattr(wiki, "site", lambda language: site)
    monkeypatch.setattr(wiki, "page", lambda *args: page)
    monkeypatch.setattr(wiki, "snapshot", lambda *args, **kwargs: base)
    wiki.save("Mpikambana:Bot-Jagwar/Rano", ARTICLE, base, "Attribution")
    flags = page.calls[0]
    assert flags["bot"] is False and flags["minor"] is False
    assert flags["notminor"] is True
    assert flags["asynchronous"] is False and flags["force"] is False
    assert flags["apply_cosmetic_changes"] is False
    if revision:
        assert flags["baserevid"] == revision
        assert flags["basetimestamp"] == base["timestamp"]
        assert flags["nocreate"] is True and flags["recreate"] is False
    else:
        assert flags["createonly"] is True


@pytest.mark.parametrize("problem", [
    "account", "legacy_account", "host", "target", "legacy_target",
])
def test_pywikibot_rejects_wrong_identity(problem: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Do not trust configuration to enforce account/site/destination constraints."""
    wiki = Wiki()
    account = {"account": "Other", "legacy_account": "Jagwar"}.get(problem, "Bot-Jagwar")
    site = SimpleNamespace(
        code="mg", family=SimpleNamespace(name="wikipedia"),
        hostname=lambda: "other.example" if problem == "host" else "mg.wikipedia.org",
        login=lambda: None, user=lambda: account,
    )
    monkeypatch.setattr(wiki, "site", lambda language: site)
    destination = {
        "target": "Rano", "legacy_target": "Mpikambana:Jagwar/Rano",
    }.get(problem, "Mpikambana:Bot-Jagwar/Rano")
    with pytest.raises(GuardError):
        wiki.save(destination, ARTICLE, {}, "Summary")


def test_pywikibot_rejects_legacy_resolved_owner(monkeypatch: pytest.MonkeyPatch) -> None:
    """A correct prefix must not permit a page resolving to the former owner."""
    wiki = Wiki()
    page = FakePage()
    monkeypatch.setattr(page, "title", lambda **kwargs: "Jagwar/Rano")
    site = SimpleNamespace(
        code="mg", family=SimpleNamespace(name="wikipedia"),
        hostname=lambda: "mg.wikipedia.org", login=lambda: None, user=lambda: "Bot-Jagwar",
    )
    monkeypatch.setattr(wiki, "site", lambda language: site)
    monkeypatch.setattr(wiki, "page", lambda *args: page)
    with pytest.raises(GuardError, match="exact permitted sandbox"):
        wiki.save("Mpikambana:Bot-Jagwar/Rano", ARTICLE, {}, "Summary")
    assert not page.calls


@pytest.mark.parametrize("payload", [
    {"text": '<span class="error">bad</span>'},
    {"text": "<p>Text</p>", "langlinks": [{"lang": "en"}]},
])
def test_render_rejects_parser_errors_and_side_effects(
    payload: dict, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject parser errors and language-link side effects; categories are expected."""
    wiki = Wiki()
    site = SimpleNamespace(
        simple_request=lambda **kwargs: SimpleNamespace(submit=lambda: {"parse": payload}),
    )
    monkeypatch.setattr(wiki, "site", lambda language: site)
    with pytest.raises(GuardError):
        wiki.render("Mpikambana:Bot-Jagwar/Rano", ARTICLE)


def test_render_allows_live_article_categories(monkeypatch: pytest.MonkeyPatch) -> None:
    """Live Sokajy membership is intended article output, not a render side effect."""
    wiki = Wiki()
    site = SimpleNamespace(
        simple_request=lambda **kwargs: SimpleNamespace(
            submit=lambda: {"parse": {"text": "<p>Text</p>",
                                      "categories": [{"category": "Fahasalamana"}]}},
        ),
    )
    monkeypatch.setattr(wiki, "site", lambda language: site)
    assert wiki.render("Mpikambana:Bot-Jagwar/Rano", ARTICLE) == "<p>Text</p>"


@pytest.mark.parametrize("state", ["existing", "missing", "redirect", "namespace"])
def test_gateway_snapshot_contract(state: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Use actual gateway read logic without contacting a live site."""
    from pywikibot.exceptions import IsRedirectPageError, NoPageError

    wiki = Wiki()

    class Page:
        """Offline Pywikibot page with configurable existence/namespace."""

        latest_revision = SimpleNamespace(revid=123, timestamp="2026-11-03T10:00:00Z")

        def namespace(self):
            return 2 if state == "namespace" else 0

        def title(self):
            return "Water"

        def full_url(self):
            return "https://en.wikipedia.org/wiki/Water"

        def get(self, *, force):
            assert force is True
            if state == "missing":
                raise NoPageError(self)
            if state == "redirect":
                raise IsRedirectPageError(self)
            return "Water article"

        def __str__(self):
            return "Water"

    monkeypatch.setattr(wiki, "page", lambda *args: Page())
    if state in {"redirect", "namespace"}:
        with pytest.raises(GuardError):
            wiki.snapshot("en", "Water")
    else:
        result = wiki.snapshot("en", "Water")
        assert result["revision_id"] == (None if state == "missing" else 123)
        assert result["sha256"] == digest(result["text"].encode())


def test_gateway_sandbox_read_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    """Even reads labeled as sandbox must resolve to the expected owner/namespace."""
    wiki = Wiki()
    monkeypatch.setattr(wiki, "page", lambda *args: SimpleNamespace(
        namespace=lambda: 2, title=lambda **kwargs: "Other/Rano",
    ))
    with pytest.raises(GuardError, match="owner"):
        wiki.snapshot("mg", "Mpikambana:Bot-Jagwar/Rano", sandbox=True)
    with pytest.raises(GuardError, match="prefix"):
        wiki.snapshot("en", "Mpikambana:Bot-Jagwar/Rano", sandbox=True)
    with pytest.raises(GuardError, match="prefix"):
        wiki.snapshot("mg", "Mpikambana:Jagwar/Rano", sandbox=True)


def test_gateway_prefers_malagasy_interlanguage_link(monkeypatch: pytest.MonkeyPatch) -> None:
    """Do not assume that the source title is the existing Malagasy title."""
    wiki = Wiki()
    link = SimpleNamespace(title="Rano madio", site=SimpleNamespace(
        code="mg", family=SimpleNamespace(name="wikipedia"),
    ))
    monkeypatch.setattr(wiki, "page", lambda *args: SimpleNamespace(langlinks=lambda: [link]))
    assert wiki.existing_title("en", "Water", "Rano") == "Rano madio"


def test_gateway_site_creation_is_lazy(monkeypatch: pytest.MonkeyPatch) -> None:
    """No import/constructor network calls or arbitrary site-family selection."""
    import pywikibot

    calls = []
    marker = object()

    def site(*args, **kwargs):
        calls.append((args, kwargs))
        return marker

    monkeypatch.setattr(pywikibot, "Site", site)
    wiki = Wiki()
    assert not calls
    assert wiki.site("mg") is marker
    assert wiki.site("mg") is marker
    assert calls == [(("mg", "wikipedia"), {"user": "Bot-Jagwar"})]
    with pytest.raises(GuardError):
        wiki.site("http://evil.example")


def test_gateway_defaults_to_external_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Select the confirmed external directory without importing or reading credentials."""
    monkeypatch.delenv("PYWIKIBOT_DIR")
    wiki = Wiki()
    assert os.environ["PYWIKIBOT_DIR"] == PYWIKIBOT_DIR == "/home/jagwar/.pywikibot"
    assert not wiki.sites


def test_gateway_preserves_credentials_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Respect an operator's explicit configuration instead of replacing it."""
    monkeypatch.setenv("PYWIKIBOT_DIR", str(tmp_path))
    Wiki()
    assert os.environ["PYWIKIBOT_DIR"] == str(tmp_path)
