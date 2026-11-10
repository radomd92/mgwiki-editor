# Historical article recipes

Former root-level scripts preserved here, byte-for-byte. `manifest.json` records
original paths, new paths, SHA-256. Job data/drafts under `runs/` unchanged.

**Historical, not safe generic commands.** Some scripts execute on import, modify
job artifacts, set review gates, perform network requests or attempt publication.
Do not import, batch-run or use as automatic review/publication machinery.

Historical sibling imports remain together. If intentionally replaying a recipe,
inspect entire script/dependencies first; run from repository root with package
installed or `PYTHONPATH=.`. Hardcoded paths/revisions remain historical evidence,
not current authorization. Old root-level command paths no longer exist.

Replacement: `python3 -m mgwiki_editor sections-plan`, `sections-assemble`, `coverage`.
Cached metadata/memos: `links-build`, `dictionary-index`, `vocabulary-report`;
assembly supports opt-in `--link-map`. All replacements article-independent.
See `docs/script-workflow.md`. Topic-specific editorial decisions not generalized.
