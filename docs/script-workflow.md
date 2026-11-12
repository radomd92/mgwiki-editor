# Generic Python workflow

Active code: `mgwiki_editor/`. Entry point: `python3 -m mgwiki_editor`.
Token/context policy and lean commands: [token-efficient-workflow.md](token-efficient-workflow.md).
Maintenance/import tools: `scripts/`.
Historical article recipes: `scripts/legacy/`; originals preserved, not imported by active code.

Default auth: unchanged external Pywikibot configuration/credentials through guarded
CLI/Wiki. No trusted-host socket/token setup required. Optional broker routing remains
fail-closed when explicitly configured. Existing review/account/sandbox/revision/
proposal/receipt/cooldown guards apply; no strict isolation claim for ordinary CLI.

Shared modules:

| Module | Reusable responsibility |
| --- | --- |
| `artifacts.py` | Job-contained evidence, exact-byte hashes, exclusive writes |
| `workflow.py` | Ordered section inputs, candidate assembly, coverage |
| `wikitext.py` | Raw inventories, grouped references, literal citations |
| `links.py` | Cached langlink batches, redirect chains, prose/caption mapping |
| `memos.py` | Exact dictionary indexes, sense-specific vocabulary reports |

Article names, term lists, aliases, omissions, naming decisions → explicit job inputs;
never shared algorithm constants. Archived recipe hashes unchanged.

## Offline section mechanics

After normal guarded `init`, coordinator reads complete pinned source/existing/sandbox.
Then:

```bash
python3 -m mgwiki_editor sections-plan --job runs/JOB
```

Default: split parsed headings through level 2; lead, subsections, appendices retained.
No regex splitting inside nowiki/templates. `--level 3` permits smaller assignments.
Coordinator reviews section boundaries; topic/merge decisions remain manual.

Custom ranges: `--ranges path/to/ranges.json`. Inclusive, 1-based lines; ordered,
contiguous, complete source coverage required. Example:

```json
[
  {"id": "00-lead", "start": 1, "end": 10},
  {"id": "01-body", "start": 11, "end": 30}
]
```

Outputs: `section-plan.json`, `section-inputs.json`, `source-inventory.json`,
`sections/<id>/source.wiki`. IDs/directories job-relative; jobs remain relocatable.
Pinned inputs/fragments hashed. Existing outputs/section directories block overwrite.
Existing article, sandbox, draft, notes, vocabulary, source issues, review gates untouched.

Delegate translation/editing section-by-section to `mgwiki-section`; not whole-article
generation. Workers produce `section.wiki`, `notes.wiki`, `vocabulary.json` in assigned
directory. Vocabulary: list, or object containing `terms`/`entries`; evidence paths
section-relative, including `../../evidence/name.json` for shared pinned evidence.
Paths outside job, missing evidence, malformed handoffs rejected. Worker statuses and
source issues still require coordinator review; notes are not machine approval.

```bash
python3 -m mgwiki_editor sections-assemble --job runs/JOB
python3 -m mgwiki_editor coverage --job runs/JOB --draft runs/JOB/assembly/draft.wiki --output runs/JOB/coverage.json
```

Assembly: new `assembly/` candidate directory. `--output runs/JOB/assembly-v2` selects
another new directory. Root `draft.wiki`, `vocabulary.json`, `review.json`, notes and
source issues never replaced. Missing/empty/blocked sections, changed pinned inputs,
dangling/conflicting named references block assembly. Reference keys include group;
definitions stay at original section positions. No externalization/restoration guess.
Worker indentation/trailing whitespace retained; assembly adds separators only.
Prepared jobs or save-attempt receipts require fresh job, never automated rebase.
Legacy plans lack input manifests: create fresh job/plan; no in-place conversion.

Candidate outputs: draft, Markdown handoffs, worker vocabulary, integrated plan,
inventory, citation-conversion ledger, hashed input manifest. Vocabulary evidence paths
remain **job-relative**, not assembly-relative; statuses/meanings unchanged. No automatic
deduplication, dictionary verification, naming substitution or unresolved→verified changes.
Optional `--native-citations`: convert only `cite ...`/`citation` templates to literal
source-key/value metadata; all populated parameters and author counts retained. Unknown
templates untouched. Output remains candidate, not polished bibliography or reviewed prose.

Coverage: raw-markup inventories for links, categories, references, templates, URLs,
file occurrences, galleries; differences plus template filename candidates. Counts
are signals, not translation completeness, Commons/license checks or semantic matches.
No fetching images/external references, no source-contradiction gate, no automatic
omission authorization. Coordinator checks infobox/transcluded content, local categories,
translated anchors, same-topic links, captions, terminology, citations and local merges.

Only after actual whole-article reconciliation: coordinator adopts candidate text and
merges vocabulary/evidence into normal root artifacts; retains existing notes/source-issue
history. Then normal validate/prepare/editorial review/guarded publish. No new command
sets review gates, publishes, auto-retries uncertain saves or weakens existing guards.

## Cached link evidence

```bash
python3 -m mgwiki_editor links-build --job runs/JOB --source-lang en --evidence evidence/links-000.json --evidence evidence/links-045.json --output runs/JOB/link-map.json
python3 -m mgwiki_editor sections-assemble --job runs/JOB --link-map link-map.json --output runs/JOB/assembly-linked
```

`--evidence` paths: job-relative, explicit, repeatable. Input: cached MediaWiki
`formatversion=2` query responses, optionally wrapped as `{"response": ...}`.
Required: `query.pages` list, source pages with `ns: 0`, Malagasy langlinks with
`lang: "mg"` and `title`. Example:

```json
{
  "response": {
    "query": {
      "pages": [
        {"ns": 0, "title": "Source topic", "langlinks": [{"lang": "mg", "title": "Kendrena"}]}
      ],
      "redirects": [{"from": "Source alias", "to": "Source topic"}]
    }
  }
}
```

No metadata fetching. `--source-lang` must match `job.json` when present. Batch order
irrelevant; all supporting files/hashes retained. Only recorded normalization/redirect
edges followed. Conflicting mappings, cycles, API errors/warnings and incomplete
continuation responses rejected. Section/interwiki redirects and missing terminal
evidence remain explicitly unresolved; no same-topic inference.

Colon titles are not automatically namespaces: `Star Trek: Voyager` can be mainspace.
Supply `--local-evidence evidence/mg-pages.json` (repeatable) for colon targets.
Required: separate cached Malagasy `query.pages` snapshots identifying exact existing
title with `ns: 0`; source snapshots cannot double as Malagasy namespace proof.
Non-mainspace/missing/contradictory namespace evidence never authorizes a target.
Local evidence hashes retained in `local_artifacts`, rechecked on load and bound into
assembly inputs. No API requests or namespace-prefix guesses.

Assembly `--link-map`: opt-in. Map rebuilt against pinned evidence before use; changed
responses or hand-edited target assertions rejected. Rebuild/review corrected evidence,
not bypass validation. Prose, headings, tables, file captions, gallery captions supported.
Labels/filenames/display options unchanged; no automatic country/name replacements or
plain-text relinking. Unmapped prose links → original displayed text + decision ledger.
Explicit source-map entries win over inferred already-local membership when names collide;
do not reapply source mapping to an already-adapted candidate with ambiguous titles.
Unverified cross-page anchors omitted when mapping; same-page/already-local anchors
retained with review flags. Existing category links stay exact except inert-to-live
conversion; foreign Category: links stay inert; no category targets invented.

Templates, refs, original italic titles, quotations, code/math/nowiki, external URLs and
external-link titles remain protected. Unknown containers unchanged, not blindly walked.
Protected links recorded where parser exposes them. Citation conversion runs afterward,
so metadata cannot accidentally become prose for mapping. Remaining foreign/protected
links and templates need coordinator adaptation; candidate is not publication-ready.
`link-decisions.json` records occurrences/actions; assembly manifest binds map/evidence.

## Dictionary and vocabulary reports

```bash
python3 -m mgwiki_editor dictionary-index --job runs/JOB --lookup evidence/lookup-en-term.json --lookup evidence/lookup-mg-term.json --output runs/JOB/dictionary-index.json
python3 -m mgwiki_editor vocabulary-report --job runs/JOB --vocabulary assembly/worker-vocabulary.json --lookup evidence/lookup-en-term.json --output runs/JOB/vocabulary-report.json
```

Explicit job-local files only; no all-runs scans, cross-job copying, dictionary requests
or external URL access. Dictionary identity: exact edition/word; 404 replies lacking
those fields may use their exact recorded `/wiktionary-pages/{en|mg}/{word}` URL.
URL/metadata identity mismatch rejected. Case, accents, plurals, editions stay separate.
All replies retained—including failed/missing/conflicting responses; none wins by
filename, order or recency. Input hashes pinned. No invented URL, definition or sense.

Vocabulary report accepts list or `terms`/`entries` wrapper. Evidence paths job-relative
(assembly worker vocabulary already rebased). Records/statuses unchanged. Groups require
exact language + term + source sense + domain; unclassified records remain separate.
Different senses/domains never collapsed. Same-sense wording, definition or status
differences reported; coordinator reconciles explicitly. Dictionary candidates are not
automatically attached to senses or treated as verification.

Missing fields/evidence, unresolved records, distinct uncertain English term count
reported. Above 100 → `unknown_vocabulary_memo_required: true`; no claim memo already
exists, meanings resolved, or review passed. Coordinator classifies names/idioms,
keeps source disagreements separately in `source-issues.md`, creates required Markdown
memo content under supported filename, binds evidence and performs actual sense review.
No report changes shared notes, vocabulary, review gates or source-issue history.

## Save and validation guards

Prepare/publish hash captured draft, state, review, vocabulary and note bytes before use,
not only files observed before/after checks. A concurrent A→B→A edit cannot render/save
transient B under A's proposal. Existing revision, preview, receipt and read-back guards
remain required; tests use fakes, never live saves.

Markdown lint ignores literal contents of `code`, `pre`, `nowiki`, `syntaxhighlight`,
`source` tags. Surrounding Markdown and independent unsafe-element/directive/placeholder
guards remain active. Gallery inventories parse caption links/templates/references and
declared files, including PDF/DjVu/audio—not just image extensions.

Successful dictionary responses (including normal 404 misses) reset overload streaks;
persisted cooldown deadlines stay intact. No automatic retry or extra sleeping.

## Future helpers

- Reusable algorithms → package functions + CLI + offline tests.
- Article choices → job-local JSON/evidence; never module constants or shared defaults.
- No imports from `scripts/legacy/`; no new root-level article recipes.
- Harness development/tests authorize no remote edits.
