# mgwiki-editor

[![CI](https://github.com/radomd92/mgwiki-editor/actions/workflows/tests.yml/badge.svg)](https://github.com/radomd92/mgwiki-editor/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

An autonomous [OpenCode](https://opencode.ai) agent harness that translates
Wikipedia articles into Malagasy and saves reviewed MediaWiki wikitext to one
sandbox destination on the Malagasy Wikipedia:

> [`Mpikambana:Bot-Jagwar/<article-title>`](https://mg.wikipedia.org/wiki/Mpikambana:Bot-Jagwar)

Mainspace is read-only. The harness has no mainspace, page-move, account or
Wikidata write path. Installing or testing the harness never edits Wikipedia.

> **Status:** alpha (0.1.0). The harness is an experimental editorial tool, not a
> Wikimedia project. Review the policy in [`AGENTS.md`](AGENTS.md) before using it
> on a live wiki.

## Highlights

- **Section-by-section editing.** A coordinator pins the source, the existing
  Malagasy page and the sandbox snapshot, then delegates one section at a time
  to offline workers. Assembly and whole-article review happen in the
  coordinator, never in a single monolithic generation.
- **Evidence-bound proposals.** `prepare` renders a proposal with content and
  evidence digests; `publish` refuses to save anything that changed after
  review.
- **Guarded publication.** Fixed account, site and namespace, live revision
  checks, server-side create/edit guards, read-back verification and a receipt
  for every attempt. Uncertain writes block retries instead of being repeated.
- **Offline-first tests.** The full suite runs without Wikipedia, dictionary or
  credential access, using fake service boundaries.
- **Shared request pacing.** One cross-process transport owns rate limits,
  `Retry-After`, overload cooldowns and circuit breaking for every job.
- **Local evidence caches.** Malagasy country names, a French–Malagasy
  mathematics glossary and read-only dictionary lookups are reused across
  articles instead of refetched per translation.

## How it works

```text
request
  └─ mgwiki-editor (coordinator)
       ├─ init ............ pin source + existing + sandbox snapshots
       ├─ sections-plan ... split the article into ordered section jobs
       ├─ mgwiki-section .. translate each section offline (parallel-safe)
       ├─ assemble + review
       ├─ validate ........ structural lint (not translation review)
       ├─ prepare ......... render proposal + bind content/evidence digests
       └─ publish ......... guarded save to the Bot-Jagwar sandbox + receipt
```

Batch requests are handled by a lean queue that starts one fresh coordinator per
article. Only coordinators perform paced Wikipedia and dictionary requests;
section workers are offline and write only inside their assigned job directory.

## Requirements

- Python 3.11 or newer
- An [OpenCode](https://opencode.ai) installation to run the agent and skills
- A Pywikibot configuration and credentials for the `Bot-Jagwar` account,
  stored **outside** this checkout
- Network access only for required Wikipedia API calls and the configured
  read-only dictionary service

The reference deployment reuses Pywikibot's private directory at
`/home/jagwar/.pywikibot`. Set `PYWIKIBOT_DIR` to your own private directory
for any other deployment. Credentials, cookies and `user-password.py` must never
be committed or pasted into prompts.

## Installation

```bash
git clone https://github.com/radomd92/mgwiki-editor.git
cd mgwiki-editor
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[test]'
.venv/bin/python -m mgwiki_editor --help
```

OpenCode discovers the project agent, command and skills automatically. Select
`mgwiki-editor` or use the command entry point:

```text
/mgtranslate https://en.wikipedia.org/wiki/Water ; Malagasy title: Rano
```

Command arguments are prompt text, not shell interpolation. No model or provider
is pinned by the repository.

## First job

```bash
python3 -m mgwiki_editor init \
  --source-lang en --source-title Water --article-title Rano \
  --job runs/water-001
python3 -m mgwiki_editor lookup --edition en --word water \
  --output runs/water-001/lookup-en-water.json
python3 -m mgwiki_editor lookup --edition mg --word rano \
  --output runs/water-001/lookup-mg-rano.json
python3 -m mgwiki_editor validate --draft runs/water-001/draft.wiki
python3 -m mgwiki_editor prepare  --job runs/water-001
python3 -m mgwiki_editor publish  --job runs/water-001
```

`publish` accepts optional `--approve FULL_SHA256` to pin an exact proposal
digest. Digests always protect content and evidence, whether or not the explicit
approval flag is used.

## Repository layout

```text
.opencode/
  agents/          coordinator, batch coordinator, section worker, issue solver
  commands/        /mgtranslate entry point
  skills/          style, edition and vocabulary procedures + local references
docs/              protocol, policy, recovery, workflow and usage documentation
mgwiki_editor/     CLI, transport guards, evidence, validation, proposal, save
tests/             offline regression suite with fake service boundaries
data/              cached country names and the Kajy mathematics glossary
scripts/           vocabulary builders and historical article recipes
evidence/          example cached audit and lookup evidence
```

## Documentation

| Document | Contents |
| --- | --- |
| [`docs/usage.md`](docs/usage.md) | Setup, configuration, CLI workflow, dictionary contract, caches |
| [`docs/edition-protocol.md`](docs/edition-protocol.md) | Full new/existing article edition and review protocol |
| [`docs/token-efficient-workflow.md`](docs/token-efficient-workflow.md) | Batch queueing and section delegation |
| [`docs/editorial-checks.md`](docs/editorial-checks.md) | Citation, metadata and rendering checks |
| [`docs/policy-enforcement.md`](docs/policy-enforcement.md) | Policy model, guards and their test coverage |
| [`docs/issue-recovery.md`](docs/issue-recovery.md) | Deferred issues, service recovery and outage reporting |
| [`docs/broker-deployment.md`](docs/broker-deployment.md) | Optional broker deployment and isolation |
| [`docs/script-workflow.md`](docs/script-workflow.md) | Reusable scripts versus historical recipes |
| [`docs/prompts/malagasy-translation-prompt.txt`](docs/prompts/malagasy-translation-prompt.txt) | Standalone model-agnostic translation prompt |
| [`AGENTS.md`](AGENTS.md) | Project policy that binds every agent role |

## Safety model

- Only `Mpikambana:Bot-Jagwar/<title>` on `mg.wikipedia.org` can be written.
- Proposals bind exact article and evidence digests; changed artifacts require
  fresh preparation and review.
- Mainspace content is read-only; existing text is reconciled in the sandbox.
- Required Wikimedia API calls go through one paced, guarded transport that
  rejects redirects and non-API endpoints.
- External links, DOI resolvers, images and package downloads are never fetched
  by agents or scripts. URLs are preserved as data.
- Source contradictions are recorded as nonblocking review issues in
  `runs/<job>/source-issues.md`; unresolved translation meaning, unsafe content,
  copyright, citation integrity and identity problems still block publication.
- The CLI is a procedural safeguard, not an OS sandbox. Stronger separation
  requires OS isolation and narrowly scoped credentials.

Tests and development work never authorize a live edit. Only an explicit
translation or edit request permits a checked sandbox save, and `draft-only` or
`no-save` instructions always win.

## Conventions

Agent commentary, logs, handoffs and memories are deliberately terse (the
project calls this *caveman ultra*) to keep long translation jobs within context
budgets. This compression never applies to Malagasy article prose or to exact
evidence, identifiers, paths, revisions or citations.

New Malagasy prose follows the local style guide in
[`.opencode/skills/mgwiki-style/`](.opencode/skills/mgwiki-style/SKILL.md),
which adapts the English Wikipedia Manual of Style and Words to Watch with
explicit source attribution.

## Development

```bash
python3 -m pytest
ruff check mgwiki_editor tests
ruff format --check mgwiki_editor tests
```

The suite is offline. Live login, rendering and save behavior must be smoke
tested by an operator with their own credentials. CI runs the same checks on
Python 3.11, 3.12 and 3.13 and never publishes edits.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for workflow and review expectations.

## Security

Please read [`SECURITY.md`](SECURITY.md) before reporting a vulnerability or
handling credentials.

## License

Released under the [Apache License 2.0](LICENSE). See [`NOTICE`](NOTICE) for
third-party attribution.

The adapted style references under
`.opencode/skills/mgwiki-style/references/` derive from English Wikipedia
material and retain their own attribution and license notices.

This project is not affiliated with or endorsed by the Wikimedia Foundation.

## Acknowledgements

- English Wikipedia's Manual of Style and Words to Watch, adapted locally with
  revision attribution for Malagasy usage.
- The *Kajy* Malagasy mathematics glossary, preserved with provenance as
  translation evidence rather than dictionary verification.
- [Pywikibot](https://www.mediawiki.org/wiki/Manual:Pywikibot) and
  [mwparserfromhell](https://github.com/earwig/mwparserfromhell).
