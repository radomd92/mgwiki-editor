# Reusing the historical article scripts

The 117 recipes under `scripts/legacy/` translated nine articles by hand. They are
preserved byte-for-byte with a hash manifest and are **not** a safe generic
workflow: some execute on import, carry job-specific paths/revisions, replace
text globally, or set review gates. Their value is the repeated method they
record, not the individual commands.

This page maps that method onto current reusable commands and documents which
patterns future articles should reuse.

## Recurring pattern → reusable form

| Legacy pattern | Examples | Current reusable form |
| --- | --- | --- |
| Pin source, existing page, sandbox and exact evidence; targeted snapshots | `*_setup.py`, `*_job.py`, `*_rebase.py` | `init`, `read`, `job.json`, digest-bound artifacts; fresh rebase job instead of scripted rebase |
| Section planning and worker-sized inputs | `*_plan.py`, `programming_workers.py` | `sections-plan`, grouped plans, `sections/<id>/source.wiki` |
| Readable review copies and reference extraction | `*_plan.py`, `*_native.py` | Raw snapshots plus offline preview; `reference_inventory`, named-reference checks |
| Link/file/category/local-page evidence batches | `*_evidence.py`, `*_names.py`, `*_identity.py` | `links-build`, `metadata-audit`, `license-evidence`, `countries`; cache every batch in the job |
| Dictionary/term inventory and serialized lookups | `*_terms.py`, `*_lookup.py`, `*_more_terms.py` | `lookup`, `lookup-batch`, `dictionary-index`, pinned `evidence/lookup-*.json` |
| Vocabulary merge, aliases, dedupe, evidence binding | `*_vocabulary.py`, `*_finalize.py`, `*_finish_memo.py` | `vocabulary-report`, `vocabulary-view`, `vocabulary-pack`; keep sense groups and evidence paths |
| Translation assembly and native citations | `*_integrate.py`, `*_native.py` | `sections-assemble`, optional `--native-citations`; never regenerate sections |
| Targeted review repairs | `*_review_fixes.py`, `*_precision_fixes.py`, `*_close_review.py` | Edit the draft or delegate the affected section; rerun `validate` + `offline-audit` |
| Coverage and reference safety checks | `*_coverage*.py`, `*_markup_safety.py`, `*_final_review.py` | `coverage` (files, URLs, named references), `citation-audit`, `metadata-audit`, `offline-audit` |
| Template existence and parameter rendering | `tmp_biol_sex_template_info2.py`, `tmp_biol_sex_param_test.py` | `template-info`, `source-expand`, `render-check` broker actions; never assume a source template works locally |
| Source disagreement memory | `earthquake_source_issues.py`, `programming_*` memos | `runs/<job>/source-issues.md`, stable IDs, nonblocking review issues |
| Retain work when blocked; handoff | `*_retain.py`, `*_finish_memo.py`, `*_followup.py` | Keep the job directory and notes; report status/blockers; no gate waiver |
| Final editorial review and gate attestation | `*_final_review.py`, `*_finalize.py` | Manual whole-article review, then `prepare`/`publish`; gates are attestations, never scripted proof |

## Patterns worth reusing for every article

1. **One evidence cache per job.** Lookups, link maps, file metadata and local
   extracts are written once, reused, and referenced from `vocabulary.json`.
   Never refetch merely because a later script wants the same value.
2. **Term ledger, not a word list.** Each non-trivial term keeps source sense,
   domain, simple-English definition, Malagasy definition, chosen wording,
   alternatives rejected and evidence paths. Old recipes that recorded only
   `English → Malagasy` lost the reasoning.
3. **Separate lexical evidence from article facts.** Dictionaries and the Kajy
   glossary attest wording candidates; they do not verify claims, identity or
   official names.
4. **Reconcile the assembled draft, not just sections.** The recurring
   `*_vocabulary.py`/`*_finish_memo.py` step caught terms that appeared in the
   article but not in the section memo, untranslated source terms and competing
   choices. Use `terminology-audit` and review its report before setting the
   terminology gate.
5. **Compare references by name/group.** File and URL coverage alone missed
   dropped or conflicting named references. `coverage` now reports missing/extra
   named references and definition conflicts as review candidates.
6. **Record omissions and repairs.** Keep reasons, affected section, evidence and
   whether an omission was user-authorized. Do not silently delete or "fix"
   source disagreement.
7. **Raw review before rendered review.** Read the complete raw draft, then inspect
   the offline preview and diff. Section-worker completion is not article review.
8. **Retain work on failure.** A blocked job stays intact with notes, evidence and
   a clear next action. Do not regenerate the article or retry an uncertain save.
9. **Handoff is a summary, not proof.** Counts, hashes and paths help the next
   session; they do not replace missing sections, review evidence or receipts.

## Patterns to leave in the archive

- Import-time execution, hardcoded `/tmp/opencode` inputs and job paths.
- Global `text.replace()` fixes for prose, names or citations.
- Reusing a job directory, resetting review flags, or programmatically setting
  gates to make preparation pass.
- Treating a failed lookup, a dictionary miss or an old revision as confirmed
  evidence.
- Rebasing by script without a fresh initialized job and exact read-back.
- Copying per-article alias tables into shared code; keep those as job evidence.

## Mining a legacy script

When a new article needs something a recipe did, extract the method:

1. Identify the job-specific constants, paths and one-off aliases.
2. State the reusable operation without the constants.
3. Add a deterministic offline command or extend an existing one; report, do not
   auto-edit.
4. Add offline tests with synthetic fixtures.
5. Document when the coordinator must use it and what remains editorial.
6. Record the source script and reason in `notes.wiki`; never import the legacy
   script into current code.

## New or strengthened reusable checks

- `terminology-audit --job runs/JOB --draft runs/JOB/draft.wiki` compares
  vocabulary decisions with the assembled text: missing chosen expressions,
  possible untranslated English source terms, competing choices and definition
  variants. Reports only; `--strict` makes review findings exit nonzero.
- `coverage` now compares named references by group/name and flags missing,
  extra and conflicting definitions.
- `transcription-audit` covers geminated consonants and `/o/`, `/u/` review.
- `offline-audit` batches the deterministic checks into separate reports.
- The lint gate requires every `Jereo koa` entry to be a live article link, red
  links included, so See also lists are never flattened to plain text.

## Limits

These checks operate on raw markup and exact strings. They do not prove
translation quality, pronunciation, link identity, source support, or that an
omission was justified. The coordinator still performs the complete editorial
review and owns every gate.
