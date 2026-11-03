"""CLI tools for the mgwiki-editor agent; machine results go to JSON, not article text."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import (
    GuardError,
    Wiki,
    country_names,
    initialize,
    lint_wikitext,
    lookup,
    prepare,
    publish,
    write_json,
)


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
    validate = commands.add_parser(
        "validate", help="Offline structural lint; not translation review",
    )
    validate.add_argument("--draft", type=Path, required=True)
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
        wiki = Wiki()
        if args.command == "init":
            result = initialize(wiki, args.job, args.source_lang, args.source_title,
                                args.article_title, args.existing_title)
            result = {"job": str(args.job), "destination": result["destination"],
                      "status": "draft_only", "source_url": result["source"]["url"]}
        elif args.command == "lookup":
            result = lookup(args.edition, args.word)
        elif args.command == "countries":
            result = country_names(wiki, refresh=args.refresh)
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
        if getattr(args, "output", None):
            if args.output.exists():
                raise GuardError("Output exists; choose a new evidence file.")
            write_json(args.output, result)
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
