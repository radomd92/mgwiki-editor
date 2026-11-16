---
description: Autonomously translate and save a checked Malagasy Wikipedia sandbox draft
agent: mgwiki-editor
---

Translate the following Wikipedia article using mgwiki-style, mgwiki-edition,
and mg-vocab: $ARGUMENTS

Follow .opencode/agents/mgwiki-editor.md's Autonomous completion contract through
guarded publication and confirmed receipt. Return early only for narrower scope,
cancellation, or an evidenced blocker; never waive a gate or transport guard.

If multiple articles: follow docs/token-efficient-workflow.md; primary queues only,
fresh mgwiki-article coordinator per article, compact path/status handoffs. Do not
load full article evidence into batch context. Below protocol applies inside each
single-article coordinator. Never duplicate an active job or reset an uncertain save.

Work autonomously under the editor's coordinator protocol. Record blockers in
runs/<job>/deferred-issues.md and continue independent tasks. Use
mgwiki-issues-solver only for assigned local proposals; never invent fixes or
bypass cooldowns, reset budgets, or retry uncertain saves.
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

Delegate section-by-section to mgwiki-section with pinned local evidence and
exclusive output directories. Only coordinator fetches evidence, assembles,
reviews, and publishes. Preserve completed work; retry only missing/blocked sections.

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
