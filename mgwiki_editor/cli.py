"""CLI tools for the mgwiki-editor agent; machine results go to JSON, not article text."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from .artifacts import write_new
from .citations import citation_audit
from .core import (
    Wiki,
    country_names,
    digest,
    initialize,
    json_bytes,
    lint_wikitext,
    lookup,
    prepare,
    publish,
)
from .licenses import file_name, license_evidence, license_report
from .links import build_link_map
from .memos import dictionary_index, pack_vocabulary, vocabulary_report, vocabulary_view
from .metadata import metadata_audit
from .reporting import report_summary
from .terminology import audit_mathematical_terms
from .usage import session_usage
from .vocabulary import vocabulary
from .workflow import assemble_sections, coverage_report, plan_sections


def parser() -> argparse.ArgumentParser:
    """Build explicit read, draft, review, and save operations."""
    root = argparse.ArgumentParser(description="Malagasy Wikipedia sandbox translation tools")
    commands = root.add_subparsers(dest="command", required=True)
    init = commands.add_parser(
        "init", help="Pin source, existing article, and sandbox; no live writes",
    )
    init.add_argument("--source-lang", required=True)
    init.add_argument("--source-title", required=True)
    init.add_argument("--article-title", required=True)
    init.add_argument("--existing-title")
    init.add_argument("--job", type=Path, required=True)
    read = commands.add_parser("read", help="Read a Wikipedia mainspace page or Bot-Jagwar sandbox")
    read.add_argument("--lang", required=True)
    read.add_argument("--title", required=True)
    read.add_argument("--sandbox", action="store_true")
    read.add_argument("--output", type=Path)
    dictionary = commands.add_parser("lookup", help="Read-only English/Malagasy Wiktionary lookup")
    dictionary.add_argument("--edition", choices=("en", "mg"), required=True)
    dictionary.add_argument("--word", required=True)
    dictionary.add_argument("--output", type=Path)
    countries = commands.add_parser(
        "countries", help="Read cached Malagasy country names from Sokajy:Firenena",
    )
    countries.add_argument(
        "--refresh", action="store_true",
        help="Explicitly refresh data/country-names.json through read-only Pywikibot",
    )
    vocab = commands.add_parser(
        "vocab", help="Query the math SQLite database read-only; not dictionary verification",
    )
    vocab.add_argument("--word", help="Case/accent-insensitive substring; omit to list all entries")
    vocab.add_argument("--language", choices=("fr", "mg"), default="fr")
    vocab.add_argument(
        "--exact", action="store_true", help="Match the complete normalized source label",
    )
    vocab.add_argument("--output", type=Path)
    audit = commands.add_parser(
        "vocab-audit", help="Find possible untranslated French math terms; report only, no editing",
    )
    audit.add_argument("--draft", type=Path, required=True)
    audit.add_argument("--output", type=Path)
    validate = commands.add_parser(
        "validate", help="Offline structural lint; not translation review",
    )
    validate.add_argument("--draft", type=Path, required=True)
    section_plan = commands.add_parser(
        "sections-plan", help="Offline, non-overwriting section inputs from any pinned source",
    )
    section_plan.add_argument("--job", type=Path, required=True)
    section_plan.add_argument(
        "--ranges", type=Path, help="JSON inclusive line ranges; full coverage",
    )
    section_plan.add_argument("--level", type=int, choices=range(1, 7), default=2)
    assemble = commands.add_parser(
        "sections-assemble", help="Offline candidate only; root draft and review gates unchanged",
    )
    assemble.add_argument("--job", type=Path, required=True)
    assemble.add_argument(
        "--output", type=Path, help="New directory inside job; default: job/assembly",
    )
    assemble.add_argument("--native-citations", action="store_true",
                          help="Literal citation fields; preserve every populated metadata field")
    assemble.add_argument(
        "--link-map", help="Job-relative map from links-build; opt-in prose mapping",
    )
    coverage = commands.add_parser(
        "coverage", help="Offline raw-markup inventory/differences; not editorial approval",
    )
    coverage.add_argument("--job", type=Path, required=True)
    coverage.add_argument("--draft", type=Path, required=True)
    coverage.add_argument("--output", type=Path)
    citations = commands.add_parser(
        "citation-audit", help="Offline short-citation/antecedent candidates; never repairs",
    )
    citations.add_argument("--job", type=Path, required=True)
    citations.add_argument("--draft", default="draft.wiki", help="Job-relative draft path")
    citations.add_argument("--output", type=Path)
    metadata = commands.add_parser(
        "metadata-audit", help="Offline file/template evidence gaps; no license approval",
    )
    metadata.add_argument("--job", type=Path, required=True)
    metadata.add_argument("--draft", default="draft.wiki", help="Job-relative draft path")
    metadata.add_argument("--evidence", action="append", default=[])
    metadata.add_argument("--output", type=Path)
    license_check = commands.add_parser(
        "license-report", help="Pinned image rights/attribution/version evidence; never approves",
    )
    license_check.add_argument("--job", type=Path, required=True)
    license_check.add_argument("--evidence", required=True, help="Job-relative API metadata JSON")
    license_check.add_argument("--filename", required=True, help="Exact bare filename")
    license_check.add_argument("--output", type=Path)
    license_capture = commands.add_parser(
        "license-evidence", help="Read image rights metadata using existing Wikipedia credentials",
    )
    license_capture.add_argument("--filename", required=True, help="Exact bare filename")
    license_capture.add_argument("--output", type=Path)
    links = commands.add_parser(
        "links-build", help="Offline interlanguage map from explicit cached Wikipedia batches",
    )
    links.add_argument("--job", type=Path, required=True)
    links.add_argument("--source-lang", required=True)
    links.add_argument("--evidence", action="append", required=True,
                       help="Job-relative cached langlink response; repeat for batches")
    links.add_argument(
        "--local-evidence", action="append", default=[],
        help="Job-relative cached Malagasy query.pages; required for colon-target namespace proof",
    )
    links.add_argument("--output", type=Path)
    index = commands.add_parser(
        "dictionary-index", help="Offline exact-word index; retains missing/failed lookup statuses",
    )
    index.add_argument("--job", type=Path, required=True)
    index.add_argument("--lookup", action="append", required=True,
                       help="Job-relative lookup JSON; repeat for multiple replies")
    index.add_argument("--output", type=Path)
    memo = commands.add_parser(
        "vocabulary-report", help="Offline sense groups/conflicts; statuses and memos unchanged",
    )
    memo.add_argument("--job", type=Path, required=True)
    memo.add_argument("--vocabulary", required=True, help="Job-relative vocabulary JSON")
    memo.add_argument("--lookup", action="append", default=[], help="Job-relative lookup JSON")
    memo.add_argument("--output", type=Path)
    view = commands.add_parser(
        "vocabulary-view", help="Offline paginated current decisions; not evidence validation",
    )
    view.add_argument("--job", type=Path, required=True)
    view.add_argument("--vocabulary", default="vocabulary.json", help="Job-relative memo path")
    view.add_argument("--offset", type=int, default=0)
    view.add_argument("--limit", type=int, default=20)
    view.add_argument("--section", help="Exact section_id filter")
    view.add_argument("--term", help="Exact source_term filter; never merges senses")
    view.add_argument("--include-evidence", action="store_true",
                      help="Include direct evidence paths/archive pointers for selected records")
    view.add_argument("--output", type=Path)
    pack = commands.add_parser(
        "vocabulary-pack", help="New lean candidate + lossless auxiliary archive; no adoption",
    )
    pack.add_argument("--job", type=Path, required=True)
    pack.add_argument("--vocabulary", required=True, help="Job-relative vocabulary list")
    pack.add_argument("--output", type=Path, required=True, help="New directory inside job")
    usage = commands.add_parser(
        "session-usage", help="Offline OpenCode session-counter JSON; never queries live server",
    )
    usage.add_argument("--input", type=Path, required=True, help="Session list/API data response")
    usage.add_argument("--session", action="append", default=[],
                       help="Exact ID; default roots only")
    usage.add_argument("--output", type=Path)
    for operation in (read, dictionary, vocab, audit, coverage, citations, metadata,
                      license_check, license_capture, links, index, memo, view, usage):
        operation.add_argument(
            "--summary", action="store_true",
            help="Require --output; save complete JSON, print only hash/signals/counts",
        )
    broker = commands.add_parser("broker", help="Scoped broker operation; no raw HTTP/shell")
    broker.add_argument("--socket", type=Path, required=True)
    broker.add_argument("--capability-file", type=Path, required=True)
    broker.add_argument("--action", required=True)
    broker.add_argument("--arguments", type=Path, required=True)
    for command in ("prepare", "publish"):
        operation = commands.add_parser(command, help="Render proposal" if command == "prepare" else
                                        "Autonomously save an exact prepared proposal to sandbox")
        operation.add_argument("--job", type=Path, required=True)
        if command == "publish":
            operation.add_argument(
                "--approve", help="Optional proposal SHA-256; autonomous mode does not require it",
            )
    return root


def main(argv: list[str] | None = None) -> int:
    """Dispatch one tool, returning nonzero for all failed gates or remote failures."""
    args = parser().parse_args(argv)
    try:
        if getattr(args, "summary", False):
            if args.output is None:
                raise ValueError("--summary requires --output; complete evidence must be retained.")
            if args.output.exists() or args.output.is_symlink():
                raise ValueError(f"Output exists; preserve it: {args.output}")
        broker_socket = os.getenv("MGWIKI_BROKER_SOCKET")
        capfile = os.getenv("MGWIKI_CAPABILITY_FILE")
        if args.command == "broker":
            from .broker import loads
            from .control import client

            result = client(args.socket, args.capability_file, args.action,
                            loads(args.arguments.read_bytes()))
            print(json.dumps(result, ensure_ascii=True, indent=2))
            return 0 if result.get("ok") else 1
        if broker_socket or capfile:
            if not broker_socket or not capfile:
                raise ValueError("Both broker socket and capability file required; no fallback.")
            if args.command in {"vocabulary-view", "vocabulary-pack", "session-usage"}:
                raise ValueError(f"{args.command} unsupported by configured broker; no fallback.")
            if args.command in {
                "init", "read", "lookup", "countries", "prepare", "publish", "sections-plan",
                "sections-assemble", "vocab", "vocab-audit", "coverage", "links-build",
                "dictionary-index", "vocabulary-report", "citation-audit", "metadata-audit",
                "license-report", "license-evidence",
            }:
                return _broker_dispatch(args, Path(broker_socket), Path(capfile))
        remote_commands = {"init", "read", "countries", "prepare", "publish", "license-evidence"}
        wiki = Wiki() if args.command in remote_commands else None
        if args.command == "init":
            result = initialize(wiki, args.job, args.source_lang, args.source_title,
                                args.article_title, args.existing_title)
            result = {"job": str(args.job), "destination": result["destination"],
                      "status": "draft_only", "source_url": result["source"]["url"]}
        elif args.command == "lookup":
            result = lookup(args.edition, args.word)
        elif args.command == "countries":
            result = country_names(wiki, refresh=args.refresh)
        elif args.command == "vocab":
            result = vocabulary(args.word, language=args.language, exact=args.exact)
        elif args.command == "vocab-audit":
            result = audit_mathematical_terms(args.draft)
        elif args.command == "sections-plan":
            result = plan_sections(args.job, ranges=args.ranges, level=args.level)
        elif args.command == "sections-assemble":
            result = assemble_sections(
                args.job, output=args.output, native_citations=args.native_citations,
                link_map=args.link_map,
            )
        elif args.command == "coverage":
            result = coverage_report(args.job, args.draft)
        elif args.command == "citation-audit":
            result = citation_audit(args.job, args.draft)
        elif args.command == "metadata-audit":
            result = metadata_audit(args.job, args.evidence, args.draft)
        elif args.command == "license-report":
            result = license_report(args.job, args.evidence, args.filename)
        elif args.command == "license-evidence":
            filename = file_name(args.filename)
            result = license_evidence(filename, wiki.file_metadata(filename))
            result.update(origin="wiki_image_info_read",
                          source_api="https://mg.wikipedia.org/w/api.php", captured_at=time.time())
        elif args.command == "links-build":
            result = build_link_map(
                args.job, args.evidence, args.source_lang, local_files=args.local_evidence,
            )
        elif args.command == "dictionary-index":
            result = dictionary_index(args.job, args.lookup)
        elif args.command == "vocabulary-report":
            result = vocabulary_report(args.job, args.vocabulary, args.lookup)
        elif args.command == "vocabulary-view":
            result = vocabulary_view(args.job, args.vocabulary, offset=args.offset,
                                     limit=args.limit, section=args.section, term=args.term,
                                     include_evidence=args.include_evidence)
        elif args.command == "vocabulary-pack":
            result = pack_vocabulary(args.job, args.vocabulary, args.output)
        elif args.command == "session-usage":
            raw = args.input.read_bytes()
            result = session_usage(json.loads(raw), sessions=args.session)
            result["source"] = {"path": str(args.input), "sha256": digest(raw)}
        elif args.command == "read":
            result = wiki.snapshot(args.lang, args.title, sandbox=args.sandbox)
        elif args.command == "validate":
            errors = lint_wikitext(args.draft.read_bytes().decode("utf-8"))
            print(json.dumps({"valid": not errors, "errors": errors}, ensure_ascii=True))
            return int(bool(errors))
        elif args.command == "prepare":
            result = prepare(wiki, args.job)
        else:
            result = publish(wiki, args.job, args.approve)
        if (getattr(args, "output", None)
                and args.command not in {"sections-assemble", "vocabulary-pack"}):
            write_new({args.output: json_bytes(result)})
        if getattr(args, "summary", False):
            result = report_summary(args.command, result, args.output)
        # JSON escapes preserve Unicode even on ASCII/Latin-1 terminal streams.
        # Local evidence files remain UTF-8; printing must not turn a successful
        # lookup/prepare/save into an apparent failure after its side effects.
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0
    except Exception as exc:
        # A failed save may already have reached Wikimedia: retain the unconfirmed receipt.
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}, ensure_ascii=True),
              file=sys.stderr)
        return 1


def _broker_dispatch(args, socket: Path, capfile: Path) -> int:
    """Compatible CLI surface; scoped run identity cannot be replaced by caller flags."""
    from .control import client

    if getattr(args, "job", None) is not None:
        status = client(socket, capfile, "status", {})
        if not status.get("ok"):
            print(json.dumps(status, ensure_ascii=True))
            return 1
        if args.job.name != status["result"]["run"]:
            raise ValueError("CLI job does not match broker capability run.")
    parameters = {}
    if args.command == "init":
        manifest = {"intent": status["result"]["intent"], "source_language": args.source_lang,
                    "source_title": args.source_title, "article_title": args.article_title}
        if args.existing_title is not None:
            manifest["existing_title"] = args.existing_title
        parameters = {"expected_manifest": manifest}
    elif args.command == "read":
        parameters = {"language": args.lang, "title": args.title, "sandbox": args.sandbox}
    elif args.command == "lookup":
        parameters = {"edition": args.edition, "word": args.word}
    elif args.command == "countries":
        parameters = {"refresh": args.refresh}
    elif args.command == "sections-plan":
        if args.ranges is not None:
            raise ValueError("Broker plans full pinned source; custom ranges unsupported.")
        parameters = {"level": args.level}
    elif args.command == "sections-assemble":
        if args.native_citations or args.link_map or args.output:
            raise ValueError("Broker assembles accepted native fragments; correct workers first.")
    elif args.command == "vocab":
        parameters = {"word": args.word, "language": args.language, "exact": args.exact}
    elif args.command == "vocab-audit":
        parameters = {"draft": args.draft.as_posix()}
        # No caller-selected absolute broker paths. Use explicit broker-relative command if needed.
        if args.draft.is_absolute() or ".." in args.draft.parts:
            raise ValueError("Broker audit draft must be job-relative.")
    elif args.command == "links-build":
        parameters = {"source_language": args.source_lang, "evidence": args.evidence,
                       "local_evidence": args.local_evidence}
    elif args.command == "citation-audit":
        parameters = {"draft": args.draft}
    elif args.command == "metadata-audit":
        parameters = {"draft": args.draft, "evidence": args.evidence}
    elif args.command == "license-report":
        parameters = {"evidence": args.evidence, "filename": args.filename}
    elif args.command == "license-evidence":
        parameters = {"filename": args.filename}
    elif args.command == "dictionary-index":
        parameters = {"lookups": args.lookup}
    elif args.command == "vocabulary-report":
        parameters = {"lookups": args.lookup, "vocabulary": args.vocabulary}
    elif args.command == "coverage":
        if args.draft.absolute() != args.job.absolute() / "draft.wiki":
            raise ValueError("Broker coverage examines scoped job draft.wiki only.")
    if args.command == "publish" and args.approve is not None:
        # Optional digest pin remains useful; broker still independently verifies exact proposal.
        proposal = client(socket, capfile, "artifact", {"name": "proposal.json"})
        if (not proposal.get("ok")
                or json.loads(proposal["result"]["content"])["digest"] != args.approve):
            raise ValueError("Approval/digest does not match broker proposal.")
    aliases = {"sections-plan": "plan", "sections-assemble": "assemble"}
    action = aliases.get(args.command, args.command)
    response = client(socket, capfile, action, parameters)
    if response.get("ok") and getattr(args, "output", None):
        write_new({args.output: json_bytes(response["result"])})
        if getattr(args, "summary", False):
            response = {**response, "result": report_summary(
                args.command, response["result"], args.output,
            )}
    print(json.dumps(response, ensure_ascii=True, indent=2))
    return 0 if response.get("ok") else 1
