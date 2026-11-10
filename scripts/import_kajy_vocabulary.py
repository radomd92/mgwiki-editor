"""One-off, offline import of the user-requested Kajy post's saved JSON feed."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> None:
    """Create a new evidence cache from a local response; never overwrite a cache."""
    # Support the project's documented python3 scripts/name.py invocation
    # without installing packages or relying on a caller's PYTHONPATH.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from mgwiki_editor.core import now
    from mgwiki_editor.vocabulary import import_kajy_feed

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feed", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = import_kajy_feed(args.feed.read_bytes(), retrieved_at=now())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"output": str(args.output), "entry_count": result["entry_count"]}))


if __name__ == "__main__":
    main()
