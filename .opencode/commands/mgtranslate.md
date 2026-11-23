---
description: Autonomously translate and save a checked Malagasy Wikipedia sandbox draft
agent: mgwiki-editor
---

Translate the following Wikipedia article using mgwiki-style, mgwiki-edition,
and mg-vocab: $ARGUMENTS

Apply .opencode/agents/mgwiki-editor.md's Autonomous completion contract: staged text,
pending gates, audits, section handoffs are intermediate. Continue through guarded
sandbox publication/confirmed receipt. Early return: explicit draft-only/review-only,
cancellation or evidenced safety/service/runtime blocker; no gate/transport waiver.

Multiple articles: docs/token-efficient-workflow.md; primary queues only, fresh
mgwiki-article per article, path/status handoffs only, no full evidence in batch
context. Below: single-article protocol. No duplicate active job/uncertain-save reset.

Autonomous: initialize job, inspect existing Malagasy/sandbox, prepare/review
Malagasy MediaWiki wikitext, save checked proposal to
Mpikambana:Bot-Jagwar/<article-title> unless draft-only/no-save. No questions or
tool/script/draft approval. Infer only unambiguous missing titles from context;
otherwise retain work, report blocker without asking.
Follow docs/issue-recovery.md: record potential blockers separately in
runs/<job>/deferred-issues.md; continue independent tasks. Later local proposals
come from mgwiki-issues-solver in issue-resolutions/<issue-id>.md, not
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

Delegate translation/editing section by section to mgwiki-section, lead/appendices
included: pinned local evidence, separate sections/<id>/ outputs. No whole-article
generation. Only coordinator fetches Wikipedia/dictionary evidence, assembles
draft.wiki, merges evidence, reviews whole-article consistency, publishes. Offline
sections may run concurrently; remote requests may not. Preserve completed sections;
request targeted fixes for missing/blocked work before preparation.

Unfamiliar vocabulary: define sense in simple English, translate definition into
Malagasy; English in parentheses when useful. Medical terms: Malagasy transcription
plus Malagasy explanation `(na …)`; asthma = asma. Follow mg-vocab's
unknown-vocabulary.wiki procedure above 100 distinct uncertain items. No external
reference browsing or permission requests merely to browse. Accurate descriptive
wording allowed; unresolved critical meanings/publication integrity gates remain.
No external-link access through any tool or script unless I explicitly request
it; required Wikipedia API and configured read-only dictionary calls are allowed.

Normalize Malagasy country names using data/country-names.json, cached from
mgwiki's Sokajy:Firenena. Use countries for local reads; countries --refresh only
for explicit cache population/refresh, never automatically for every article.
