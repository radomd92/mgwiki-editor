# Token-efficiency audit — 2026-11-12

Read-only investigation. No agent settings, article artifacts, save guards, credentials, or remote wiki pages changed. Numbers: local OpenCode V2 API snapshots; not provider invoices. No external research.

## Measured usage

Five batch coordinator sessions; child usage not independently summed. Do not assume these numbers represent all project usage or add child totals without checking aggregation semantics.

| Session | Input | Output | Cache read | Reasoning |
| --- | ---: | ---: | ---: | ---: |
| ses_e38846283ffesUthOGFSbmQ7CJ | 28,285,862 | 1,524,477 | 1,040,752,768 | 908,069 |
| ses_e38819831ffeRb0wBEo20qNIbX | 16,088,661 | 1,016,868 | 711,492,864 | 402,224 |
| ses_e387dfd80ffeXkYHJTwi98h9Pi | 10,629,817 | 953,050 | 510,946,560 | 459,055 |
| ses_e387ea1a6ffeCjQh8tA1Urxdhg | 9,438,249 | 526,115 | 365,474,048 | 292,835 |
| ses_e3d8eddb1ffe3nXLtelTAwGsxc | 17,816,922 | 1,083,830 | 756,213,120 | 654,867 |
| Total | 82,259,511 | 5,104,340 | 3,384,879,360 | 2,717,050 |

Cache read: 97.48% of input + output + cache read. Reasoning shown separately; do not assume additive billing semantics. API reports cost=0; cannot establish actual provider charges. Output includes workflow/code/evidence generation, not solely article text.

Concrete request amplification, session ses_e38846283ffesUthOGFSbmQ7CJ:

- msg_1cf7e1452001CvJQAiZ4Wat37K: input137, output48, reasoning17, cache-read353024.
- msg_1cf7d7d3e001siZXbmv9BEeYu0: input432, output679, reasoning516, cache-read351488.

Tiny tool steps repeatedly carry ~350k cached context. 10,000 such calls would account for ~3.5B cache tokens; illustrative arithmetic, not measured call count.

## Local overhead

- `AGENTS.md`, section-agent prompt, mandatory skills, full style references, edition/recovery docs: ~121 KB combined before source/evidence. Runtime inclusion/deduplication varies; byte count is not token count.
- `.opencode/agents/mgwiki-section.md:36` and `docs/edition-protocol.wiki:192-194`: each section worker loads three skills plus style references. Fresh workers repeat setup, including tiny appendix assignments.
- `runs/math-function-20261110/draft.wiki`: 101,898 bytes. Root vocabulary: 12,717,669 bytes / 635 records; 2,630 JSON files under job. Memo field values: dictionary_checks ~7.27 MB; historical dictionary_checks_before_current112 ~647 KB; evidence_files ~1.06 MB. Repeated serialization/readback can dwarf article text; file size alone does not prove every byte reached model.
- `runs/netherlands-20261110`: draft262021bytes; vocabulary6378478bytes / 620 records. 48,605 evidence-file references, 1,486 distinct paths; up to99 references/record. Repeated coordinator batch-review fields add substantial bulk.
- `runs/currency-20261110`: 197 vocabulary records / 8,326 evidence-path mentions; up to190 references/record.
- Existing reusable operations already available: sections-plan, sections-assemble, coverage, dictionary-index, vocabulary-report, citation-audit, metadata-audit. See `mgwiki_editor/cli.py`. Avoid generating per-job replacements for supported deterministic work.
- `mgwiki_editor/memos.py:127-129`: vocabulary-report includes complete records. LLM-facing compact views could omit repeated records while retaining full immutable evidence on disk.
- Sampled coordinator and section sessions use gpt-6.1-sol/high. Lower reasoning/model cost needs quality trial, not automatic blanket replacement.

## Priorities

1. Fresh coordinator per article; batch manager holds only job IDs, states, paths, blockers. No cross-article transcript replay. Preserve independent article coordinators and serialized guarded wiki operations.
2. Run deterministic plan/assemble/audit/index steps through reusable CLI. Return counts, failures, changed IDs, artifact paths/hashes—not full successful reports. Batch independent local checks into one tool result. Never hide evidence needed for actual editorial review.
3. Normalize NEW vocabulary evidence: immutable lookup/check objects once; per-sense records reference IDs/paths. Keep global provenance once in a bound manifest. Preserve transitive hashing, exact sense/edition/status identity, history, and preparation integrity. Requires schema/guard tests; never bulk-rewrite prepared jobs.
4. LLM receives current decisions + relevant evidence, not every historical snapshot/review. Keep history on disk. Reopen raw evidence where needed; never represent summaries as reviewed originals.
5. Consolidate duplicated instructions; separate worker editorial rules from coordinator transport/publication procedures. Current rules explicitly require full guides: changing that needs a deliberate policy revision, not silent omission. Keep all substantive editorial/network/save restrictions.
6. Group coherent short subsections under existing section-planning allowance. Keep exclusive worker outputs; no whole-article generation. Resume same section worker for targeted corrections; avoid regenerating accepted prose.
7. One complete source/local comparison and full final editorial/raw/preview review; reuse hash-bound unchanged checks between passes. Changes invalidate dependent checks, not automatically every unrelated check. Live revision/account/proposal/readback guards always remain.
8. Pilot lower reasoning for routine section drafting; retain strongest review for difficult/sensitive content. This reduces cost/latency, not necessarily token count or preserves quality automatically.
9. Budget visible per article/stage: fresh input, cache read, output, reasoning, calls, repairs, provider charge if available. Budget exhaustion preserves work and reports incomplete; never skips gates or marks missing sections complete.

## Validation

Compare representative ordinary, mathematical, and medical articles against current workflow. Measure tokens per accepted article, cache replay, tool turns, memo bytes, repair passes, elapsed time, and actual provider charges. Require equivalent meaning, fluent Malagasy, source/local coverage, protected citations/names, terminology evidence, and unchanged publication guards. No defensible savings percentage before this trial.

## Diagnostics limits

Two stats CLI attempts interrupted around server restarts; output empty. Cause not established; no further stats invocation. Small authenticated local API reads succeeded. DB not modified or externally inspected: 6.5GB DB, only ~1.6GB disk free, insufficient space for straightforward backup. Disk pressure separate operational risk; no cleanup performed.

## Implemented follow-up

User authorized implementation. New batch routing: fresh mgwiki-article coordinator
per article; section workers skip only coordinator edition/recovery/broker setup,
retain full local style references. Existing article jobs untouched; no wiki edits,
model downgrade, automatic migration or save-guard changes.

New CLI: --summary with exclusive full-report output; vocabulary-view with exact
filters/pagination/optional evidence paths; vocabulary-pack with lossless auxiliary
archive and unchanged direct raw-evidence binding; offline session-usage. Existing
full-output CLI behavior retained. New commands fail closed under configured broker
until that profile supports them; existing broker reports support --summary.

Read-only byte comparison: all records in current-decision views, pages of100,
including page metadata/omitted-field names; no original file changed:

| Job | Original memo bytes | All current-view pages bytes | Records | View-byte reduction |
| --- | ---: | ---: | ---: | ---: |
| math-function-20261110 | 12,717,669 | 877,611 | 635 | 93.10% |
| netherlands-20261110 | 6,378,478 | 1,232,471 | 620 | 80.68% |
| currency-20261110 | 640,493 | 251,996 | 197 | 60.66% |

Current-decision view omits historical checks/raw evidence; not equivalent to full
review. These are serialization-byte reductions, NOT measured token/billing or
end-to-end savings. Relevant raw evidence still needs review. Live orchestration
and ordinary/math/medical article quality trial remain unmeasured; harness work
does not authorize publication. Usage snapshots permit later same-scope comparison.
