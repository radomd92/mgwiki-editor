"""Build the queryable mathematics database offline from the preserved JSON import."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> None:
    """Create a new SQLite file; existing databases and pinned job evidence stay intact."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from mgwiki_editor.vocabulary import (
        VOCABULARY_CACHE,
        VOCABULARY_DATABASE,
        build_vocabulary_database,
    )

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=VOCABULARY_CACHE)
    parser.add_argument("--output", type=Path, default=VOCABULARY_DATABASE)
    args = parser.parse_args()
    print(json.dumps(build_vocabulary_database(args.source, args.output), ensure_ascii=True))


if __name__ == "__main__":
    main()
