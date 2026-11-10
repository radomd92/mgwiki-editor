---
description: Autonomously translate and save a checked Malagasy Wikipedia sandbox draft
agent: mgwiki-editor
---

Translate the following Wikipedia article using mgwiki-style, mgwiki-edition,
and mg-vocab: $ARGUMENTS

Work autonomously: initialize a job, inspect existing Malagasy and sandbox text,
prepare and review Malagasy MediaWiki wikitext, and save the checked proposal to
Mpikambana:Bot-Jagwar/<article-title> unless I specify draft-only/no-save. Do not
ask questions or request tool/script/draft approval. Infer unambiguous missing
titles from context; otherwise retain work and report a blocker without asking.
Follow docs/issue-recovery.md: record potential blockers separately in
runs/<job>/deferred-issues.md; continue independent tasks. Later local proposals
come from Mgwiki-editor-issues-solver in issue-resolutions/<issue-id>.md, not
invented fixes. Genuine HTTP 5xx:
>=15-second safe-read retry cooldown, longer transport/server guards win;
after 600 seconds confirm down via real permitted service test, skip dependent
tasks. More than 25 distinct skipped tasks in same continuous outage + fresh
5xx test → SEVERE SERVICE OUTAGE DETECTED in OpenCode output, followed by one
simple assessment paragraph including evidence, blocked tasks and memo path.
Never bypass cooldowns, reset lookup budgets, or retry uncertain saves.
Local python3 scripts are available: inspect/run/create task-relevant helpers.
Independent article tasks may run concurrently; keep each job's remote calls
serial through the shared paced Wikipedia gateway. Shared-slot contention may
wait up to 600 seconds total per gate; server cooldown waits retain a separate
10-second limit. No parallel fetching within a job, immediate retries
after HTTP 429, or blind save retries. Use MediaWiki wikitext only for Malagasy
translation/article content. User-facing replies, progress logs, handoffs, and
memories use plain text or Markdown, never MediaWiki formatting. Use caveman ultra
for all non-article natural-language output, including memory prose.
Internal compaction summaries and conversation checkpoints follow
OpenCode's supplied Markdown template exactly, preserving required headings,
order, labels, and structure. Do not translate, rename, compress, wrap, or convert
the template to MediaWiki wikitext. Use caveman ultra for free-text summary
bodies: remove filler and repetition, not substance. Preserve exact paths,
commands, identifiers, hashes, revisions, URLs, errors, decisions, blockers,
pending actions, authorization limits, and safety guards. Never compress required
template text or change its meaning; clarity wins.
Never compress article prose; preserve machine formats and verbatim evidence.

Source inconsistencies and article contradictions are nonblocking review issues.
Persist them before prepare in runs/<job>/source-issues.md: stable ID, status,
pinned revision/path/section, conflicting claims/citations, draft handling, and
next review action. Retain history after publication/rebase; link the memory in
notes.wiki and the final handoff. Translate conflicting accounts faithfully with
existing attribution/uncertainty, not invented reconciliation or translator TODOs.
Source disagreement alone must not block publication or fail review gates.
Independent unknown translation meanings, unsafe sensitive content, copyright,
citation integrity, topic/merge identity, and technical/save guards still apply.

Delegate translation/editing to mgwiki-section subagents section by section,
including the lead and appendices, using pinned local evidence and separate
sections/<id>/ output directories. Do not generate the whole article at once.
Only the coordinator fetches Wikipedia/dictionary evidence, assembles draft.wiki,
merges section evidence, reviews whole-article consistency, and publishes. Offline
section work may run concurrently; remote requests may not. Preserve completed
sections and request targeted fixes for missing/blocked work before preparation.

For unfamiliar vocabulary, define the sense in simple English, then translate
the definition into Malagasy; keep the English term in parentheses when helpful.
Medical terms use a Malagasy transcription plus a Malagasy explanation in the
form `(na …)`; asthma = asma. Follow mg-vocab's unknown-vocabulary.wiki procedure
above 100 distinct uncertain items. Do not browse external reference links or
request permission just to do so. Accurate descriptive wording is acceptable;
unresolved critical meanings and publication integrity gates remain mandatory.
No external-link access through any tool or script unless I explicitly request
it; required Wikipedia API and configured read-only dictionary calls are allowed.

Normalize Malagasy country names using data/country-names.json, cached from
mgwiki's Sokajy:Firenena. Use countries for local reads; countries --refresh only
for explicit cache population/refresh, never automatically for every article.
