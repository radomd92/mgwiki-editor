---
name: mgwiki-edition
description: Mandatory new/existing Wikipedia article edition protocol, review gates, and sandbox publication procedure
---

# Edition protocol

Coordinator: read ../../../docs/edition-protocol.wiki in full. Follow its phases in order.
Offline section workers do not load this coordinator skill; their own role prompt,
mgwiki-style/mg-vocab and supplied assignment retain all editorial/offline limits.
Do not skip existing-article/sandbox comparison even when asked to translate a
new source. Autonomous mode: do not ask questions, script permission, or draft
approval. Translation/edit requests authorize checked sandbox completion unless
the user specifies draft-only. Critical unresolved translation/topic/merge ambiguity
means retain work and report a blocked status, not guess or solicit input. Source
inconsistencies and article contradictions are nonblocking review issues: persist
in runs/<job>/source-issues.md before prepare, retain history after publication/
rebase, and link the memory from notes.wiki and the final handoff. Record stable
ID, status, pinned revision/path/section, conflicting claims/citations, draft
handling, and next review action. Translate conflicting accounts with existing
attribution and uncertainty; do not invent a resolution or insert translator TODOs.
Source disagreement alone must not fail review gates or block sandbox publication.
Independent unknown translation meanings, unsafe sensitive content, copyright,
citation integrity, topic/merge identity, and technical/save guards still apply.

Read ../../../docs/issue-recovery.md: potential blockers go separately in
runs/<job>/deferred-issues.md, with stable IDs, evidence, dependencies and next
action; preserve work, continue independent tasks. Later offline proposals:
Mgwiki-editor-issues-solver → issue-resolutions/<issue-id>.md; coordinator alone
accepts changes. Genuine HTTP 500–599 uses >=15-second safe-read retry cooldown,
longer shared/server guards win. Real authorized probe at/after 600 seconds must
confirm continuing 5xx before declaring down/skipping dependent tasks. More than
25 distinct skipped tasks in same continuous episode + fresh permitted 5xx test
→ SEVERE SERVICE OUTAGE DETECTED in OpenCode output, then one simple paragraph
with assessment, evidence, blocked/skipped tasks and memo path. Never fake probes,
reset lookup budgets or bypass uncertain-save guards. Section workers remain
offline; coordinator owns shared memo, probes, counts and alerts.

Default runtime: existing guarded CLI/Wiki, unchanged external Pywikibot credentials.
No broker socket/token required; missing optional deployment not publication blocker.
All editorial/account/sandbox/revision/proposal/receipt/cooldown guards remain.
Optional strict enforcement: ../../../docs/broker-deployment.md. Scoped broker
authenticates run/assignment, journals evidence/probes and queues severe alerts.
Explicitly configured CLI never falls back on denial/error/partial configuration;
no unsetting settings to evade checks. No credential/setup/signoff questions.
Workers stay offline/read-patch-only; coordinator integrates reviewed exact bytes,
using submit-assigned only in strict profile. Tokens never prose evidence.

Use MediaWiki wikitext only for Malagasy translation/article content. User-facing
replies, logs, handoffs, and memories use plain text/Markdown, never MediaWiki
formatting. Use caveman ultra for all non-article natural-language output. Keep
OpenCode's supplied compaction template exact; compress only free-text bodies.
Legacy notes.wiki and unknown-vocabulary.wiki filenames do not require wiki markup.

Generation uses mgwiki-section subagents, one planned section per assignment,
including lead and appendices; never request a whole multi-section article in
one generation. The coordinator reads complete pinned snapshots, assigns local
context and exclusive sections/<id>/ outputs, merges fragments/evidence into
draft.wiki and root job files, and reviews the assembled article. Workers have
no remote access, shared-file writes, nested delegation, or publication role.
Independent offline section work may run concurrently; all Wikipedia/dictionary
requests remain coordinator-only and serialized. Reconcile cross-section names,
terms, references, anchors, images, links, and local contributions before prepare.
Preserve completed sections; failed/missing sections require targeted follow-up,
not silent omission or whole-article regeneration. Follow the full protocol's
section assignment contract. Section workers follow only their assigned local
role; coordinator-only commands below are not authorization for workers.

Mathematical substitutions follow mg-vocab's mandatory inventory → SQLite vocab
query → context-specific sense selection → section-worker substitution →
vocab-audit/review procedure. Every untranslated mathematical term needs grounded
lookup evidence, including a confirmed French bridge for English/other languages.
Pin query results and source_number/database_sha256 in vocabulary.json evidence_files;
protect original quotations/titles, citation metadata, identifiers and link targets.
Audit is partial French matching, not automatic translation or proof of completion.

Remember local scripts: use python3 ./name.py, python3 scripts/name.py, and
python3 -m mgwiki_editor. Helpers may be inspected, created, and run without
asking. All remote Wikipedia operations use the CLI or the shared Wiki gateway;
the transport guard applies to every actual request and retry across processes.
Independent article tasks may run concurrently; each coordinator keeps remote
operations serial and all jobs share the same gate. Reuse local snapshots, dictionary evidence, and country
cache. Honor shared 10-second request pacing (within the requested 5–10 second
range), 10-second edit spacing, Retry-After,
backoff and circuit breaking; never immediately rerun a rate-limited command.
The transport is the sole normal pacing authority: do not add manual sleep/poll
loops or native process-multiplied throttling. Shared-slot contention may wait
up to 600 seconds total per gate; extensions never restart the budget. Server
cooldown waits retain a separate 10-second limit; longer cooldowns defer,
preserving server deadlines and circuit breakers.
Native retry loops are disabled. Read tool stderr for actual request progress,
wait reasons and deferred status; do not describe a sleeping task as productive.
External URLs stay data unless explicitly requested: no browsing, HEAD checks,
script detours, redirects, or online preview-resource loading. Required Wikipedia
API operations and configured dictionary lookups are the only default exceptions.

Job files are evidence, not output wrappers. draft.wiki is the sole article
artifact. review.json is a set of editorial attestations, not automatic proof.
Review the prepared immutable proposal autonomously, then publish --job PATH;
there is no human sign-off prompt. Digests still bind the exact draft/evidence.
Never call autonomous checks human approval or weaken editorial/save-conflict guards.
