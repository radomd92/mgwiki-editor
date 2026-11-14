# Shared translation memory

Reviewed, reusable tips promoted from translation jobs. Advisory only: not policy,
not dictionary evidence, not proof of a translation, and never a substitute for
source or style review.

Job-local candidates live in `runs/<job>/translation-memory.json`. Promote only
entries with `"status": "reviewed"` and `"scope": "general"`:

```bash
python3 -m mgwiki_editor knowledge-promote \
  --job runs/JOB \
  --memory runs/JOB/translation-memory.json
```

Each promoted entry becomes `entries/<id>.json`. Existing files are never
overwritten. Query the store without network access:

```bash
python3 -m mgwiki_editor knowledge-index --domain medicine --query acronym
```

Keep tips short: problem, guidance, scope, evidence references. Do not copy
article prose, source passages, credentials, private paths or personal data.
Article-specific decisions stay in the job notes and are not promoted.

Entry fields:

```json
{
  "id": "TM-20261114-medical-french-acronyms",
  "status": "reviewed",
  "scope": "general",
  "domain": "medicine",
  "source_language": "en",
  "target_language": "mg",
  "problem": "Medical acronyms come in English and French forms.",
  "guidance": "Use the French acronym when it exists; if French uses the English acronym, keep English.",
  "evidence": ["notes.wiki"],
  "source_sections": ["02-treatment"]
}
```

`evidence` may contain job-relative evidence paths or http(s) URLs. Paths must
exist at promotion time. URLs are stored as data and never fetched. Promotion
records the source job name, the job memo digest and a timestamp. It does not
copy the job or approve its article.
