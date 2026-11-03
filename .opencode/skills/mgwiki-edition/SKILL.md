---
name: mgwiki-edition
description: Mandatory new/existing Wikipedia article edition protocol, review gates, and sandbox publication procedure
---

# Edition protocol

Read ../../../docs/edition-protocol.wiki in full. Follow its phases in order.
Do not skip existing-article/sandbox comparison even when asked to translate a
new source. Autonomous mode: do not ask questions, script permission, or draft
approval. Translation/edit requests authorize checked sandbox completion unless
the user specifies draft-only. Critical unresolved ambiguity means retain work
and report a blocked status, not guess or solicit input.

Remember local scripts: use python3 ./name.py, python3 scripts/name.py, and
python3 -m mgwiki_editor. Helpers may be inspected, created, and run without
asking. All remote Wikipedia operations use the CLI or the shared Wiki gateway;
the transport guard applies to every actual request and retry across processes.
No parallel wiki workers. Reuse local snapshots, dictionary evidence, and country
cache. Honor shared 10-second request pacing (within the requested 5–10 second
range), 10-second edit spacing, Retry-After,
backoff and circuit breaking; never immediately rerun a rate-limited command.
The transport is the sole normal pacing authority: do not add manual sleep/poll
loops or native process-multiplied throttling. A gate waits at most 10 seconds;
longer cooldowns defer the task immediately while preserving server deadlines.
Native retry loops are disabled. Read tool stderr for actual request progress,
wait reasons and deferred status; do not describe a sleeping task as productive.
External URLs stay data unless explicitly requested: no browsing, HEAD checks,
script detours, redirects, or online preview-resource loading. Required Wikipedia
API operations and configured dictionary lookups are the only default exceptions.

Job files are evidence, not output wrappers. draft.wiki is the sole article
artifact. review.json is a set of editorial attestations, not automatic proof.
Review the prepared immutable proposal autonomously, then publish --job PATH;
there is no human sign-off prompt. Digests still bind the exact draft/evidence.
Never call autonomous checks human approval or weaken editorial/conflict guards.
