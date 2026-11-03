---
description: Autonomously translate and save a checked Malagasy Wikipedia sandbox draft
agent: mgwiki-editor
---

Translate the following Wikipedia article using mgwiki-style, mgwiki-edition,
and mg-vocab: $ARGUMENTS

Work autonomously: initialize a job, inspect existing Malagasy and sandbox text,
prepare and review Malagasy MediaWiki wikitext, and save the checked proposal to
Mpikambana:Bot-Jagwar/<article-title> unless I specify draft-only/no-save. Do not
ask questions or request tool/script/draft approval. Infer unambiguous missing
titles from context; otherwise retain work and report a blocker without asking.
Local python3 scripts are available: inspect/run/create task-relevant helpers.
Use the shared paced Wikipedia gateway; no parallel fetching, immediate retries
after HTTP 429, or blind save retries. All responses: wikitext, no Markdown.

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
