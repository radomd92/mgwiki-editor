# Token-efficient workflow

Scope: new work. Existing jobs/artifacts untouched; no bulk migrations. No model
or reasoning downgrade. Article prose never shortened for token targets.

## Ownership/context

- Multi-article request → mgwiki-editor queue only → fresh mgwiki-article session
  per article → offline mgwiki-section workers. Single article may stay in primary.
- Queue manifest: original article request/limits, job path, article session ID,
  status, blockers, confirmed receipt, source/deferred memory paths. No article
  bodies, complete reports or cross-article transcripts. No duplicate active owner.
- Existing batch continuation: finish any active operation safely, persist exact
  state/uncertain-save limits, transfer ownership explicitly before fresh child.
  Do not fork an active or uncertain operation. Missing essential handoff → retain
  work/defer; never infer a successful save from child/session completion.
- Article coordinator reads complete source/existing/sandbox and full required
  skills/guides. Workers load style + vocab and full local style references once
  per section session; no coordinator-only edition/recovery/broker setup.
- Group coherent short subsections/appendices where dependencies permit. Never
  whole-article generation. Preserve planned lead/body/appendix/local coverage.
- Targeted fix → same section worker/session, changed inputs plus affected context.
  Accepted unrelated sections retained. No new whole-article generation.

## Reusable local commands

Prefer sections-plan, sections-assemble, coverage, dictionary-index,
vocabulary-report, citation-audit, metadata-audit, vocab-audit. Custom script only
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
