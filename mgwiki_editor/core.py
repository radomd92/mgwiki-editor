"""Read-only research and autonomous, content-bound Pywikibot sandbox saves."""

from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request

import mwparserfromhell

from .network import dictionary_open, install_wikimedia_transport

ACCOUNT = "Bot-Jagwar"
PREFIX = f"Mpikambana:{ACCOUNT}/"
DICTIONARY_URL = "http://192.168.1.155:8000"
PYWIKIBOT_DIR = "/home/jagwar/.pywikibot"
COUNTRY_CATEGORY = "Sokajy:Firenena"
COUNTRY_CACHE = Path("data/country-names.json")
GATES = (
    "meaning", "fluency", "coverage", "terminology", "citations", "links_templates",
    "neutrality", "existing_preserved", "wikitext_only",
)


class GuardError(RuntimeError):
    """An operation failed a safety or editorial gate."""


def now() -> str:
    """Return a UTC audit timestamp."""
    return datetime.now(UTC).isoformat()


def digest(data: bytes) -> str:
    """Hash exact bytes for content-bound approval."""
    return hashlib.sha256(data).hexdigest()


def json_bytes(value: Any) -> bytes:
    """Serialize canonical UTF-8 JSON for stable proposal hashing."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")


def write_json(path: Path, value: Any) -> None:
    """Atomically replace one local JSON artifact."""
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(json_bytes(value) + b"\n")
    temporary.replace(path)


def read_json(path: Path) -> Any:
    """Read one complete UTF-8 JSON artifact."""
    return json.loads(path.read_text(encoding="utf-8"))


def title(value: str) -> str:
    """Normalize a title while rejecting fragments, control characters, and markup."""
    value = unicodedata.normalize("NFC", value.replace("_", " ").strip())
    if (
        not value or len(value.encode("utf-8")) > 220
        or any(unicodedata.category(c).startswith("C") for c in value)
        or any(c in value for c in "#|[]{}<>")
        or value.startswith(":")
    ):
        raise GuardError("Invalid or oversized page title.")
    return value


def sandbox_title(article_title: str) -> str:
    """Construct the sole permitted destination, never accepting a full namespace title."""
    article_title = title(article_title)
    if article_title.casefold().startswith(("mpikambana:", "user:")):
        raise GuardError("Supply an article title, not a user-page title.")
    result = PREFIX + article_title
    if len(result.encode("utf-8")) > 255:
        raise GuardError("Sandbox title exceeds MediaWiki's title limit.")
    return result


def job_path(value: str | Path) -> Path:
    """Limit job artifacts to this working directory's runs tree."""
    root = (Path.cwd() / "runs").resolve()
    path = Path(value).resolve()
    if not path.is_relative_to(root) or path == root:
        raise GuardError("Job must be a subdirectory of ./runs/.")
    return path


def country_names(wiki: Wiki, *, refresh: bool = False) -> dict[str, Any]:
    """Read the local country-title cache; only explicit refresh contacts mgwiki."""
    if not refresh:
        if not COUNTRY_CACHE.is_file():
            raise GuardError("Country-name cache missing; run countries --refresh once.")
        result = read_json(COUNTRY_CACHE)
    else:
        result = {
            "schema": 1, "language": "mg", "category": COUNTRY_CATEGORY,
            "category_url": "https://mg.wikipedia.org/wiki/Sokajy:Firenena",
            "scope": "direct_mainspace_members", "retrieved_at": now(),
            "titles": sorted(set(wiki.country_titles())),
        }
    if (
        not isinstance(result, dict) or result.get("schema") != 1
        or result.get("language") != "mg" or result.get("category") != COUNTRY_CATEGORY
        or result.get("category_url") != "https://mg.wikipedia.org/wiki/Sokajy:Firenena"
        or result.get("scope") != "direct_mainspace_members"
        or not isinstance(result.get("retrieved_at"), str) or not result["retrieved_at"]
        or not isinstance(result.get("titles"), list) or not result["titles"]
        or any(not isinstance(item, str) for item in result["titles"])
    ):
        raise GuardError("Invalid or empty country-name cache; not a usable country list.")
    if any(title(item) != item or ":" in item for item in result["titles"]):
        raise GuardError("Country-name cache contains a non-mainspace or noncanonical title.")
    if result["titles"] != sorted(set(result["titles"])):
        raise GuardError("Country-name cache must contain sorted, distinct titles.")
    if refresh:
        COUNTRY_CACHE.parent.mkdir(parents=True, exist_ok=True)
        write_json(COUNTRY_CACHE, result)
    return result


def lookup(
    edition: str, word: str, *, base_url: str | None = None, opener: Any = dictionary_open,
) -> dict[str, Any]:
    """GET dictionary entries without invoking translation/publication endpoints."""
    if edition not in {"en", "mg"}:
        raise GuardError("Dictionary edition must be en or mg.")
    if not word.strip() or len(word) > 250 or any(ord(c) < 32 for c in word):
        raise GuardError("Invalid dictionary word.")
    base = (base_url or os.getenv("MGWIKI_DICTIONARY_URL", DICTIONARY_URL)).rstrip("/")
    parsed = urlsplit(base)
    if (
        parsed.scheme not in {"http", "https"} or not parsed.hostname
        or parsed.username or parsed.password or parsed.query or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise GuardError("Dictionary base must be an HTTP(S) origin without credentials.")
    url = f"{base}/wiktionary-pages/{edition}/{quote(word.strip(), safe='')}"
    request = Request(
        url, headers={"Accept": "application/json", "User-Agent": "mgwiki-editor/0.1"},
    )
    try:
        with opener(request, timeout=20) as response:
            payload = response.read(5_000_001)
            if len(payload) > 5_000_000:
                raise GuardError("Dictionary response exceeds 5 MB.")
            raw = json.loads(payload)
    except HTTPError as exc:
        if exc.code == 404:
            return {"url": url, "retrieved_at": now(), "status": "missing", "entries": []}
        raise GuardError(f"Dictionary HTTP error {exc.code}; not a dictionary miss.") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise GuardError("Dictionary unavailable; do not infer a missing word.") from exc
    except (ValueError, UnicodeError) as exc:
        raise GuardError("Malformed dictionary JSON.") from exc
    if not isinstance(raw, list) or any(
        not isinstance(entry, dict) or not isinstance(entry.get("language"), str)
        or not isinstance(entry.get("definitions"), list)
        or any(not isinstance(d, str) for d in entry["definitions"])
        for entry in raw
    ):
        raise GuardError("Unexpected dictionary entry schema.")
    entries = [entry for entry in raw if entry["language"] == edition]
    return {
        "url": url, "retrieved_at": now(), "edition": edition, "word": word,
        "status": "found" if entries else "no_matching_language",
        "entries": entries, "raw_entries": raw, "content_trust": "untrusted_dictionary_data",
    }


def lint_wikitext(text: str) -> list[str]:
    """Conservatively lint wikitext; do not pretend to prove language or full syntax validity."""
    errors = []
    if not text.strip():
        errors.append("Empty article.")
    if len(text.encode("utf-8")) > 1_000_000:
        errors.append("Article exceeds the 1 MB harness limit.")
    code = mwparserfromhell.parse(text)
    prose = text
    # Operators inside native math/chem tags are not Markdown emphasis.
    for tag in code.filter_tags():
        if str(tag.tag).strip().lower() in {"math", "chem"}:
            prose = prose.replace(str(tag), "")
    patterns = {
        "Markdown fence or backtick": r"`|(?m:^\s*~~~)",
        "Markdown link/image": r"!?\[[^\]\n]*\]\([^\n]*\)",
        "Markdown emphasis": r"\*\*[^*\n]+\*\*|(?<!\w)__[^_\n]+__|(?<!\*)\*[^*\n]+\*(?!\*)",
        "Markdown task list": r"(?m:^\s*[-*+]\s+\[[ xX]\])",
        "Markdown bullet (use MediaWiki *)": r"(?m:^\s*[-+]\s+\S)",
        "Markdown numbered list (use MediaWiki #)": r"(?m:^\s*\d+[.)]\s+\S)",
        "Markdown horizontal rule": r"(?m:^\s*(?:---|\*\s*\*\s*\*|_\s*_\s*_)\s*$)",
        "Markdown table separator": r"(?m:^\s*\|?\s*:?-{3,}:?\s*\|\s*:?-{3,})",
        "Unresolved editorial placeholder": r"(?i:\bTODO\b|\bFIXME\b|\[TRANSLAT[^\]]*\])",
        "Redirect or metadata directive": r"(?im:^\s*#redirect\b)|(?i:\{\{\s*DEFAULTSORT\s*:)",
        "Unsafe HTML element": r"(?i:<\s*(?:script|iframe)\b)",
    }
    for label, pattern in patterns.items():
        if re.search(pattern, prose):
            errors.append(label + ".")
    for link in code.filter_wikilinks():
        target = str(link.title).strip()
        if re.match(r"(?i)^(?:category|sokajy)\s*:", target):
            errors.append("Sandbox category must be inert (prefix link with :).")
        if re.match(r"^[a-z]{2,3}(?:-[a-z0-9]+)*:", target):
            errors.append("Live interwiki link is not permitted in the sandbox.")
    definitions: set[tuple[str, str]] = set()
    reuses: set[tuple[str, str]] = set()
    reference_groups: set[str] = set()
    rendered_groups: set[str] = set()
    for tag in code.filter_tags():
        name = str(tag.tag).strip().lower()
        if name not in {"ref", "references"}:
            continue
        group = str(tag.get("group").value).strip("\"' ") if tag.has("group") else ""
        if name == "references":
            rendered_groups.add(group)
            continue
        reference_groups.add(group)
        if tag.has("name"):
            key = (group, str(tag.get("name").value).strip("\"' "))
            if tag.self_closing:
                reuses.add(key)
            elif str(tag.contents).strip():
                definitions.add(key)
    if reuses - definitions:
        errors.append("Named reference reused without a definition in the same group.")
    # Require native reference rendering instead of guessing local template behavior.
    if reference_groups - rendered_groups:
        errors.append("Each reference group needs a matching <references /> renderer.")
    return sorted(set(errors))


class Wiki:
    """Lazy Pywikibot gateway; account and writable site are not configurable."""

    def __init__(self) -> None:
        """Initialize without contacting Wikimedia."""
        # Pywikibot reads this at its first import, including exception imports.
        # Reuse the external configuration; never copy or modify credentials.
        os.environ.setdefault("PYWIKIBOT_DIR", PYWIKIBOT_DIR)
        self.sites: dict[str, Any] = {}

    def site(self, language: str) -> Any:
        """Return a Wikipedia site, never a Wiktionary or arbitrary host."""
        if not re.fullmatch(r"[a-z]{2,12}(?:-[a-z0-9]{1,12})*", language):
            raise GuardError("Invalid Wikipedia language code.")
        if language not in self.sites:
            import pywikibot

            install_wikimedia_transport()
            kwargs = {"user": ACCOUNT} if language == "mg" else {}
            self.sites[language] = pywikibot.Site(language, "wikipedia", **kwargs)
        return self.sites[language]

    def page(self, language: str, page_title: str) -> Any:
        """Construct a validated Pywikibot page."""
        import pywikibot

        return pywikibot.Page(self.site(language), page_title)

    def snapshot(self, language: str, page_title: str, *, sandbox: bool = False) -> dict[str, Any]:
        """Read exact current text/revision without silently following redirects."""
        from pywikibot.exceptions import IsRedirectPageError, NoPageError

        if sandbox and (language != "mg" or not page_title.startswith(PREFIX)):
            raise GuardError("Invalid sandbox site or prefix.")
        if sandbox:
            if page_title != sandbox_title(page_title[len(PREFIX):]):
                raise GuardError("Use the exact normalized sandbox title.")
        else:
            page_title = title(page_title)
        page = self.page(language, page_title)
        if sandbox:
            if (
                int(page.namespace()) != 2
                or page.title(with_ns=False) != page_title.split(":", 1)[1]
            ):
                raise GuardError("Sandbox namespace/owner changed after title normalization.")
        elif int(page.namespace()) != 0:
            raise GuardError("Source/existing article must be mainspace.")
        try:
            text = page.get(force=True)
            revision = page.latest_revision
            revision_id = revision.revid
            timestamp = str(revision.timestamp)
        except NoPageError:
            text, revision_id, timestamp = "", None, None
        except IsRedirectPageError as exc:
            raise GuardError(f"Redirect requires explicit resolution: {page_title}") from exc
        return {
            "language": language, "title": page.title(), "requested_title": page_title,
            "revision_id": revision_id, "timestamp": timestamp,
            "text": text, "sha256": digest(text.encode("utf-8")),
            "url": f"https://{language}.wikipedia.org/w/index.php?oldid={revision_id}"
            if revision_id else page.full_url(),
        }

    def existing_title(self, language: str, source_title: str, fallback: str) -> str:
        """Prefer a source's Malagasy interlanguage target when available."""
        for link in self.page(language, source_title).langlinks():
            if link.site.code == "mg" and link.site.family.name == "wikipedia":
                return link.title
        return fallback

    def country_titles(self) -> list[str]:
        """List direct mainspace members of mgwiki's fixed country category."""
        import pywikibot

        category = pywikibot.Category(self.site("mg"), COUNTRY_CATEGORY)
        pages = category.articles(namespaces=0, recurse=False)
        return [page.title() for page in pages if int(page.namespace()) == 0]

    def render(self, destination: str, text: str) -> str:
        """Parse a sandbox draft on mgwiki without saving it."""
        data = self.site("mg").simple_request(
            action="parse", title=destination, text=text, contentmodel="wikitext",
            prop="text|categories|langlinks", formatversion=2, disablelimitreport=True,
        ).submit()["parse"]
        html = data["text"]
        if isinstance(html, dict):
            html = html["*"]
        if data.get("categories") or data.get("langlinks"):
            raise GuardError("Rendered sandbox has category or language-link side effects.")
        if re.search(r'class=[\"\'][^\"\']*\b(?:error|mw-ext-cite-error)\b', html):
            raise GuardError("MediaWiki preview contains a parser/citation error.")
        return html

    def save(self, destination: str, text: str, base: dict[str, Any], summary: str) -> None:
        """Save only Bot-Jagwar's sandbox with server-side creation/revision guards."""
        site = self.site("mg")
        if (
            site.code != "mg" or site.family.name != "wikipedia"
            or site.hostname() != "mg.wikipedia.org"
        ):
            raise GuardError("Writable site is not mg.wikipedia.org.")
        site.login()
        if site.user() != ACCOUNT:
            raise GuardError(f"Authenticated account must be {ACCOUNT}.")
        if (
            not destination.startswith(PREFIX)
            or destination != sandbox_title(destination[len(PREFIX):])
        ):
            raise GuardError("Write is outside the fixed sandbox prefix.")
        page = self.page("mg", destination)
        if int(page.namespace()) != 2 or page.title(with_ns=False) != destination.split(":", 1)[1]:
            raise GuardError("Resolved write target is not the exact permitted sandbox.")
        # Recheck immediately before save. The server-side guards close the remaining race.
        assert_snapshot(base, self.snapshot("mg", destination, sandbox=True))
        guards: dict[str, Any] = {"createonly": True}
        if base["revision_id"] is not None:
            guards = {
                "baserevid": base["revision_id"], "basetimestamp": base["timestamp"],
                "nocreate": True, "recreate": False,
            }
        page.text = text
        page.save(
            summary=summary, minor=False, notminor=True, bot=False, force=False, asynchronous=False,
            apply_cosmetic_changes=False, quiet=True, watch="nochange", **guards,
        )


def assert_snapshot(expected: dict[str, Any], actual: dict[str, Any]) -> None:
    """Reject stale revisions, changed content, canonical titles, or identities."""
    for key in ("language", "title", "revision_id", "sha256"):
        if expected[key] != actual[key]:
            raise GuardError(
                f"Snapshot changed ({key}): {expected['title']}; reinitialize and merge.",
            )


def initialize(
    wiki: Wiki, job: Path, source_language: str, source_title: str,
    article_title: str, existing_title: str | None = None,
) -> dict[str, Any]:
    """Pin source, mainspace, and sandbox evidence without writing any remote page."""
    job = job_path(job)
    if job.exists():
        raise GuardError("Job already exists; choose a new directory to preserve evidence.")
    if source_language == "mg":
        raise GuardError("Translation source must be a non-Malagasy Wikipedia.")
    source_title, article_title = title(source_title), title(article_title)
    destination = sandbox_title(article_title)
    source = wiki.snapshot(source_language, source_title)
    if source["revision_id"] is None:
        raise GuardError("Source article does not exist.")
    existing_title = title(existing_title) if existing_title else wiki.existing_title(
        source_language, source_title, article_title,
    )
    existing = wiki.snapshot("mg", existing_title)
    sandbox = wiki.snapshot("mg", destination, sandbox=True)
    state = {
        "schema": 1, "created_at": now(), "destination": destination,
        "source": source, "existing": existing, "sandbox": sandbox,
    }
    job.mkdir(parents=True, exist_ok=False)
    write_json(job / "job.json", state)
    for name in ("source", "existing", "sandbox"):
        (job / f"{name}.wiki").write_bytes(state[name]["text"].encode("utf-8"))
    initial = sandbox["text"] if sandbox["revision_id"] is not None else existing["text"]
    (job / "draft.wiki").write_bytes(initial.encode("utf-8"))
    (job / "notes.wiki").write_text("= Fanamarihana momba ny fanitsiana =\n", encoding="utf-8")
    write_json(job / "review.json", dict.fromkeys(GATES, False))
    write_json(job / "vocabulary.json", [])
    return state


ARTIFACTS = ("job.json", "draft.wiki", "review.json", "notes.wiki", "vocabulary.json")


def artifact_hashes(job: Path) -> dict[str, str]:
    """Bind every editable proposal input to exact bytes."""
    names = set(ARTIFACTS)
    vocabulary = read_json(job / "vocabulary.json")
    if not isinstance(vocabulary, list):
        raise GuardError("Vocabulary memo must be a list.")
    for entry in vocabulary:
        if not isinstance(entry, dict) or not isinstance(entry.get("evidence_files"), list):
            raise GuardError("Vocabulary entries need evidence_files.")
        for name in entry["evidence_files"]:
            if not isinstance(name, str):
                raise GuardError("Invalid vocabulary evidence path.")
            evidence = (job / name).resolve()
            if not evidence.is_relative_to(job) or not evidence.is_file():
                raise GuardError("Vocabulary evidence must be an existing file inside the job.")
            names.add(name)
    return {name: digest((job / name).read_bytes()) for name in sorted(names)}


def check_state(state: dict[str, Any]) -> None:
    """Reject changed job identities before any network or publication operation."""
    destination = state["destination"]
    if (
        not destination.startswith(PREFIX)
        or destination != sandbox_title(destination[len(PREFIX):])
    ):
        raise GuardError(f"Job destination is outside {ACCOUNT}'s sandbox.")
    if (
        state.get("schema") != 1 or state["source"]["language"] == "mg"
        or state["source"]["revision_id"] is None
        or state["existing"]["language"] != "mg" or state["sandbox"]["language"] != "mg"
        or state["sandbox"]["requested_title"] != destination
    ):
        raise GuardError("Invalid job snapshot identities.")
    for name in ("source", "existing", "sandbox"):
        snapshot = state[name]
        if snapshot["sha256"] != digest(snapshot["text"].encode("utf-8")):
            raise GuardError(f"Corrupt {name} snapshot hash.")


def check_live(wiki: Wiki, state: dict[str, Any]) -> None:
    """Ensure all pinned article evidence is still current."""
    for name in ("source", "existing", "sandbox"):
        old = state[name]
        new = wiki.snapshot(old["language"], old["requested_title"], sandbox=name == "sandbox")
        assert_snapshot(old, new)


def checked_draft(job: Path) -> str:
    """Read exact UTF-8 bytes, require all editorial attestations, and lint syntax."""
    text = (job / "draft.wiki").read_bytes().decode("utf-8")
    review = read_json(job / "review.json")
    missing = [gate for gate in GATES if review.get(gate) is not True]
    if missing:
        raise GuardError("Unreviewed gates: " + ", ".join(missing))
    errors = lint_wikitext(text)
    if errors:
        raise GuardError(" ".join(errors))
    vocab = read_json(job / "vocabulary.json")
    if not isinstance(vocab, list) or any(
        not isinstance(item, dict) or item.get("status") not in {"verified", "descriptive"}
        or not item.get("evidence_files") or not item.get("source_sense")
        or not item.get("chosen_expression") or not item.get("malagasy_definition")
        for item in vocab
    ):
        raise GuardError("Vocabulary memo contains unresolved or invalid entries.")
    if len((job / "notes.wiki").read_text(encoding="utf-8").strip().splitlines()) < 2:
        raise GuardError("Record section coverage and review evidence in notes.wiki.")
    return text


def prepare(wiki: Wiki, job: Path) -> dict[str, Any]:
    """Create a rendered, diffable proposal; never save a remote page."""
    job = job_path(job)
    if (job / "receipt.json").exists():
        raise GuardError("Job has a save attempt; reconcile it and use a fresh job.")
    before = artifact_hashes(job)
    state = read_json(job / "job.json")
    check_state(state)
    text = checked_draft(job)
    check_live(wiki, state)
    html = wiki.render(state["destination"], text)
    (job / "preview.html").write_bytes(html.encode("utf-8"))
    changes = "".join(difflib.unified_diff(
        state["sandbox"]["text"].splitlines(keepends=True), text.splitlines(keepends=True),
        fromfile=state["destination"] + " (pinned)", tofile=state["destination"] + " (proposed)",
    ))
    (job / "changes.diff").write_bytes(changes.encode("utf-8"))
    summary = "Dika amin' ny teny malagasy: " + state["source"]["url"]
    if state["existing"]["revision_id"]:
        summary += "; nampidirina ny " + state["existing"]["url"]
    if len(summary.encode("utf-8")) > 500:
        raise GuardError("Attribution summary exceeds 500 bytes.")
    after = artifact_hashes(job)
    if before != after:
        raise GuardError("Job inputs changed during preparation.")
    proposal = {
        "schema": 1, "prepared_at": now(), "destination": state["destination"],
        "artifacts": after, "preview_sha256": digest(html.encode("utf-8")),
        "diff_sha256": digest(changes.encode("utf-8")), "summary": summary,
        "source_url": state["source"]["url"],
    }
    proposal["digest"] = digest(json_bytes(proposal))
    write_json(job / "proposal.json", proposal)
    return proposal


def publish(wiki: Wiki, job: Path, approval: str | None = None) -> dict[str, Any]:
    """Autonomously save an exact prepared proposal once, retaining every integrity gate."""
    job = job_path(job)
    proposal = read_json(job / "proposal.json")
    body = {key: value for key, value in proposal.items() if key != "digest"}
    if (
        approval is not None and approval != proposal["digest"]
        or digest(json_bytes(body)) != proposal["digest"]
    ):
        raise GuardError("Approval/digest must match the complete, unmodified proposal.")
    if artifact_hashes(job) != proposal["artifacts"]:
        raise GuardError("Draft or evidence changed after preparation; prepare again.")
    for name, key in (("preview.html", "preview_sha256"), ("changes.diff", "diff_sha256")):
        if digest((job / name).read_bytes()) != proposal[key]:
            raise GuardError("Review artifact changed after preparation.")
    state = read_json(job / "job.json")
    check_state(state)
    if state["destination"] != proposal["destination"]:
        raise GuardError("Proposal destination does not match job.")
    text = checked_draft(job)
    check_live(wiki, state)
    html = wiki.render(state["destination"], text)
    if digest(html.encode("utf-8")) != proposal["preview_sha256"]:
        raise GuardError("Live rendering changed after preparation; prepare and review again.")
    if artifact_hashes(job) != proposal["artifacts"]:
        raise GuardError("Job inputs changed during publication checks.")
    receipt = {
        "status": "unconfirmed", "attempted_at": now(), "proposal_digest": proposal["digest"],
        "mode": "autonomous" if approval is None else "explicit_digest",
        "destination": state["destination"], "source_url": proposal["source_url"],
        "draft_sha256": digest(text.encode("utf-8")),
    }
    # Exclusive receipt creation prevents double submission and blind retry after a timeout.
    try:
        with (job / "receipt.json").open("xb") as stream:
            stream.write(json_bytes(receipt) + b"\n")
    except FileExistsError as exc:
        raise GuardError(
            "A save was already attempted; inspect/reconcile it, never blindly retry.",
        ) from exc
    wiki.save(state["destination"], text, state["sandbox"], proposal["summary"])
    actual = wiki.snapshot("mg", state["destination"], sandbox=True)
    if actual["sha256"] != receipt["draft_sha256"] or actual["revision_id"] is None:
        raise GuardError("Save unconfirmed: read-back differs. Inspect receipt and live sandbox.")
    receipt.update(
        status="confirmed", verified_at=now(), revision_id=actual["revision_id"], url=actual["url"],
    )
    write_json(job / "receipt.json", receipt)
    return receipt
