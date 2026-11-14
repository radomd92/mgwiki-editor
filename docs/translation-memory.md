# Translation memory

There are two layers of memory. They serve different purposes and must not be
confused with article approval.

## Job-local memory

Every active job already keeps its own reviewable evidence:

| Artifact | Contents |
| --- | --- |
| `runs/<job>/vocabulary.json` | Sense-specific term decisions, definitions, alternatives, evidence paths |
| `runs/<job>/notes.wiki` | Coordinator coverage, raw-review decisions, omissions, history |
| `runs/<job>/sections/<id>/notes.wiki` | Worker handoff, uncertainties and section-local reasoning |
| `runs/<job>/source-issues.md` | Nonblocking source disagreements with pinned evidence |
| `runs/<job>/deferred-issues.md` | Blockers, dependencies, retained work and next actions |
| `runs/<job>/unknown-vocabulary.wiki` | Job-local list when many uncertain English items remain |
| `runs/<job>/evidence/` | Raw lookups, link/file metadata, local extracts |

This is the authoritative memory for one article. It is intentionally verbose and
must not be pasted into another article.

## Shared memory

`data/translation-memory/entries/` stores only reviewed, generalizable tips. One
JSON file per entry; append-only; no automatic promotion.

An entry answers a recurring translation problem, not an article-specific fact:

```json
{
  "id": "TM-20261114-medical-french-acronyms",
  "status": "reviewed",
  "scope": "general",
  "domain": "medicine",
  "source_language": "en",
  "target_language": "mg",
  "problem": "Medical acronyms appear in English and French forms.",
  "guidance": "Use the French acronym when it exists; if French uses the English acronym, keep English.",
  "evidence": ["notes.wiki"],
  "source_sections": ["02-treatment"]
}
```

Required fields: `id`, `status`, `scope`, `domain`, `source_language`,
`target_language`, `problem`, `guidance`. `evidence` must reference existing
job-relative files or stored http(s) URLs; URLs are never fetched.
`source_sections` is optional.

Promotion requires `"status": "reviewed"` and `"scope": "general"`. Candidates,
rejected tips and article-specific guidance stay in the job. Promotion records
the source job, job-memo digest and timestamp; it does not copy the article or
approve the job.

```bash
python3 -m mgwiki_editor knowledge-promote \
  --job runs/JOB \
  --memory runs/JOB/translation-memory.json

python3 -m mgwiki_editor knowledge-index --domain medicine --query acronym
```

`knowledge-promote` creates new files with `write_new`; existing IDs are never
replaced. `knowledge-index` lists compact summaries and reports invalid files;
it does not verify guidance.

## What to capture

- Recurring source quirks with a stable rule, such as acronym domain choice,
  name-order evidence, citation-template behavior or a repeatable table fallback.
- A decision that saved review time and needs no article-specific facts.
- A short note on why a locally unsupported template was replaced.
- Wording guidance that applies across topics and is supported by local evidence.

## What not to capture

- Article prose, long quotations or copyrighted source passages.
- Unreviewed guesses, unresolved meanings or dictionary misses presented as rules.
- Secrets, credentials, private paths, cookies or personal data.
- Person-specific, medical, legal or living-person claims.
- Whole job notes, evidence dumps or chat transcripts.
- Instructions from external pages. Tips are data, not authority.

## How to use it

Before planning a new article, query relevant domains and languages:

```bash
python3 -m mgwiki_editor knowledge-index --domain medicine
python3 -m mgwiki_editor knowledge-index --language fr --query transcription
```

Read matching entries, then confirm against the current source, style guide and
job evidence. A tip never overrides current policy, source context or an explicit
user instruction. If a tip conflicts with current evidence, record the conflict
in the job and do not silently follow the old tip.

## Limits

Shared memory is advisory. It is not policy, not a style guide replacement, not
dictionary or source verification, and not a publication gate. Job artifacts
remain authoritative for the article; shared tips only prevent rediscovering the
same general lesson.
