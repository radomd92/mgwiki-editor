# Token-efficient workflow

Scope: new work. Existing jobs/artifacts untouched; no bulk migrations. No model
or reasoning downgrade. Article prose never shortened for token targets.

## Ownership/context

- Multi-article request → mgwiki-editor queue only → fresh mgwiki-article session
  per article → offline mgwiki-section workers. Single article may stay in primary.
- Queue manifest: original article request/limits, job path, article session ID,
  status, blockers, confirmed receipt, source/deferred memory paths. No article
  bodies, complete reports or cross-article transcripts. No duplicate active owner.
- Conversation is scratch state; artifacts are the record. Persist handoffs,
  review evidence and blockers to disk as work proceeds, compact between stages,
  and re-read required pinned artifacts after compaction. A compacted summary is
  never review evidence or a save receipt.
- Existing batch continuation: finish any active operation safely, persist exact
  state/uncertain-save limits, transfer ownership explicitly before fresh child.
  Do not fork an active or uncertain operation. Missing essential handoff → retain
  work/defer; never infer a successful save from child/session completion.
- Article coordinator reads complete source/existing/sandbox and full required
  skills/guides. Workers load style + vocab and full local style references once
  per section session; no coordinator-only edition/recovery/broker setup.
- Group coherent short subsections/appendices where dependencies permit. Never
  whole-article generation. Preserve planned lead/body/appendix/local coverage.
  `sections-plan --group-max-bytes 4000` merges only adjacent short sections up to
  that many source bytes; every heading, byte and line range is retained, the first
  ID names the group, and the plan records `source_sections`, `group_bytes`,
  `headings` and `merged_ids`. Default 0 keeps one assignment per heading; grouped
  plans assemble through the unchanged gates; configured broker planning stays
  ungrouped.
- Targeted fix → same section worker/session, changed inputs plus affected context.
  Accepted unrelated sections retained. No new whole-article generation.
- Turn-reducing commands: `lookup-batch` (per-word evidence files, one turn),
  `offline-audit` (deterministic checks in one turn, separate reports), and
  `evidence-pin`/`evidence-verify` (replace ad-hoc pin/verify scripts). Same
  evidence, checks and guards; only the turn count drops. Batch ≤50 words;
  pending 502 evidence retained, resumed later per policy, never polled.

## Reusable local commands

Prefer sections-plan, sections-assemble, coverage, dictionary-index,
vocabulary-report, citation-audit, metadata-audit, vocab-audit,
transcription-audit. Custom script only
for missing functionality, not a new per-job copy of existing operations.
Batch independent offline checks in one shell invocation when useful; remote
Wikipedia/dictionary operations remain serial per coordinator through shared gate.
No shell sleep/poll loops or parallel remote requests.

Supported report/read/lookup commands accept `--output NEW_PATH --summary`:

```bash
python3 -m mgwiki_editor vocabulary-report --job runs/JOB --vocabulary vocabulary.json --output runs/JOB/evidence/vocabulary-report-v1.json --summary
python3 -m mgwiki_editor coverage --job runs/JOB --draft runs/JOB/draft.wiki --output runs/JOB/evidence/coverage-v1.json --summary
```

Full JSON saved exclusively. Stdout: path, exact hash/bytes, counts, scalar signals.
Error exits unchanged; summary is not a successful editorial review or permission
to omit failures. Inspect relevant full report details before decisions. Preview,
source/local snapshots and final raw article still read completely. Reuse only
actual hash-bound unchanged checks; changes invalidate affected evidence and
require fresh preparation. Every live revision/account/save/readback guard stays.

## Bounded evidence slices

Large job evidence (media reviews, dictionary batches, vocabulary memos) must not
enter model context whole. Page it:

```bash
python3 -m mgwiki_editor json-slice --job runs/JOB --path evidence/media-editorial-review-v01.json \
  --key files --offset 0 --limit 20 --field filename --field decision --field reason
```

Job-relative JSON file only; `--key` addresses one exact array path (omit for a
root array). `--offset/--limit` page it (limit 1-100); `--field` repeats to keep
only named fields. Output pins the source path, SHA-256 and byte size, reports
`total_items`/`next_offset` and the omitted field names. The source file is never
modified, nothing is inferred, merged or completed, and the slice is not a review
or approval. Under a configured broker the command fails closed; no direct-IO
fallback. Use `vocabulary-view` for memo records and `vocabulary-pack` for a lean
candidate plus lossless auxiliary archive.

## Current vocabulary vs history

```bash
python3 -m mgwiki_editor vocabulary-view --job runs/JOB --limit 20
python3 -m mgwiki_editor vocabulary-view --job runs/JOB --section 00-lead --offset 20 --limit 20
```

Exact `--term`/`--section` filters; no substring, case, plural or sense merging.
Offsets index filtered matches; record_index always original memo ordinal.
Source hash, total/matching counts and next_offset expose incomplete paging.
Current definitions/wording/status exact; auxiliary fields/evidence paths omitted
and identified. View does not validate raw evidence, resolve terms or approve.
Add `--include-evidence` to list exact direct evidence paths/archive pointers for
selected records without replaying historical check objects; read relevant files.

New entries: one current sense/choice/definition/status record; raw lookups and
coordinator checks/history stored once in evidence. Keep relevant raw dependencies
directly in evidence_files. Do not append job-wide history/review objects to every
entry. Existing editorial-state.json review_evidence can bind shared reviews once
with exact hashes; never fabricate review attestations.

Optional large-memo candidate:

```bash
python3 -m mgwiki_editor vocabulary-pack --job runs/JOB --vocabulary assembly/worker-vocabulary.json --output runs/JOB/vocabulary-candidate-v1
```

Creates new vocabulary.json + details.json; source/root artifacts unchanged.
Current decision fields stay inline. Auxiliary JSON values content-addressed once
in archive, with per-record field mappings. Every original direct evidence path
retained; archive path added to each record, so existing proposal hashing binds
archive AND raw dependencies. No new implicit/transitive manifest format.
No status upgrade or semantic deduplication. Archive source hash retains lineage.
Coordinator reviews relevant archived fields before adopting; unknown material
meaning still blocks even when an auxiliary field describes uncertainty. Do not
blindly adopt a compact view as a review. Exact archive values + current records
allow original-record reconstruction (remove packed_details/archive evidence
suffix, restore mapped fields). Raw source file itself remains unchanged.
Prepared/save-attempt jobs and already-packed input refused. No automatic adoption,
rebase or review gate writes. Keep archive after adoption; deleting it blocks
preparation. Configured broker supports existing --summary reporting; new view,
pack and usage commands currently fail closed there, never fall back to direct IO.

## Offline usage measurement

```bash
python3 -m mgwiki_editor session-usage --input SESSION_COUNTER_SNAPSHOT.json --output runs/BATCH/usage-before.json
```

Input: saved OpenCode session list or API `{ "data": [...] }` response. No live
server/statistics request. Default sums unique roots only; repeat `--session ID`
for exact selection. Parent+child aggregates rejected; counter aggregation
semantics not assumed. Input, cache read/write, output, reasoning separate;
reasoning not added to output. No invoice/provider price inferred. Retain scope,
model, article/job IDs and before/after snapshots for meaningful comparison.

Measure per accepted article: input/cache/output/reasoning, calls/repair passes,
memo bytes, elapsed time, provider charges when available. Use representative
ordinary/math/medical articles for later authorized trials; no wiki writes during
harness development. Budget exhaustion → retained incomplete/deferred work, never
skipped sections/review/save checks. No unmeasured savings claims.

## Disk-first sessions and compaction

Conversation is scratch state; artifacts are the record. Coordinators write
handoffs, notes, review evidence, receipts and blockers to disk as they go, then
let compaction trim the transcript between stages — after each accepted section
batch and before whole-article review. After compaction, re-read the required
pinned artifacts (snapshots, section files, handoffs, review evidence, final raw
draft/preview) instead of trusting summarized conversation. A compacted summary is
never review evidence, an editorial attestation or a save receipt. Do not compact
across an uncertain save; reconcile the receipt first. Compaction is harness-driven,
so the instruction is not a guarantee: if the session compacts while a save receipt
is unconfirmed, stop article work, reconcile the destination and the local receipt
through the paced gateway, and only then continue. If a worker session compacts,
it re-reads its assignment and pinned inputs before writing; it must never
continue from a summary alone. V2 exposes `compaction.auto`, `compaction.keep.tokens`,
`compaction.buffer` and `experimental.background_compaction`; none are set here, so
the harness default applies and no runtime compaction has been recorded. Changing
them is a deliberate policy decision, not a token shortcut.

## Model/reasoning pilot (opt-in, no default change)

All roles currently run gpt-6.1-sol/high. Optional pilot: routine section drafting
on a lower reasoning variant; high reasoning stays mandatory for coordinator review
gates, medical/legal/living-person content, naming/identity decisions and final
assembly. Run per session via the TUI/model selector or an explicit temporary
config override; do not change project defaults or agent files for the pilot.
Trial design: pick one ordinary + one math article already covered by the current
workflow baseline; run session-usage before/after; compare draft SHA-level
coverage, vocabulary statuses, citation/link inventories and review-gate outcomes.
Accept only when the coordinator's full editorial review finds no new unresolved
meaning, coverage loss or citation damage. Quality regressions end the pilot.
