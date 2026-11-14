# Usage and configuration

This document covers setup, Pywikibot configuration, the end-to-end CLI workflow,
dictionary and cache contracts, and the harness's guarantees and limits. For an
overview, see the [README](../README.md).

## Scope and repository hygiene

The harness translates articles into Malagasy and saves checked MediaWiki
wikitext only to `Mpikambana:Bot-Jagwar/<article-title>` on
<https://mg.wikipedia.org>. Mainspace is read-only. No article has been published
by installing or testing this harness.

Translation jobs under runs/, build/test artifacts, environment files and private
credentials are excluded from Git. Keep authentication material outside this
checkout; .gitignore is a precaution, not a complete secret scanner. Review staged
changes before committing. Never commit ~/botjagwar or copy its credentials here.

The adapted style references retain their own attribution and license notices;
see [NOTICE](../NOTICE).

## Repository files
* .opencode/agents/mgwiki-editor.md: agent and permission rules.
* .opencode/agents/mgwiki-article.md: fresh single-article batch coordinator.
* .opencode/agents/mgwiki-section.md: offline section translation/editing subagent.
* .opencode/agents/mgwiki-issues-solver.md: later offline deferred-issue proposals.
* docs/issue-recovery.md: autonomous issue memo, guarded 5xx recovery/outage alerts.
* .opencode/commands/mgtranslate.md: /mgtranslate entry point.
* .opencode/skills/mgwiki-style/SKILL.md: Malagasy style guide and output contract.
* .opencode/skills/mgwiki-style/references/manual-of-style.wiki: locally adapted
  English Wikipedia MoS with source-revision attribution and Malagasy overrides.
* .opencode/skills/mgwiki-style/references/words-to-watch.wiki: all warning groups,
  source examples, contextual usage and protected quotation/title/citation rules.
* .opencode/skills/mgwiki-edition/SKILL.md: required edition workflow.
* .opencode/skills/mg-vocab/SKILL.md: evidence-backed vocabulary memo procedure.
* docs/edition-protocol.md: full new/existing article edition protocol.
* docs/prompts/malagasy-translation-prompt.txt: standalone translation prompt.
* mgwiki_editor/: Pywikibot CLI, dictionary client, validation, proposal, and save.
* mgwiki_editor/network.py: shared pacing, overload cooldowns, API-only transport.
* tests/: offline regression tests with fake Wikipedia/dictionary boundaries.
* data/country-names.json: cached direct mainspace titles from Sokajy:Firenena.
* data/vocabulary/kajy-mathematics.sqlite: indexed, queryable French–Malagasy
  mathematics candidates, with original spellings, provenance and review flags.
* data/vocabulary/kajy-mathematics.json: preserved import for offline DB rebuilds.
* data/vocabulary/kajy-mathematics-review.md: persistent glossary review issues.
* mgwiki_editor/vocabulary.py: offline glossary import, SQLite build/read-only query.
* mgwiki_editor/terminology.py: possible untranslated-French-math audit, never edits.
* scripts/build_vocabulary_db.py: offline, non-overwriting SQLite snapshot builder.

Python workflow: docs/script-workflow.md. Reusable section planning, candidate
assembly, coverage via CLI: sections-plan, sections-assemble, coverage. Historical
article recipes: scripts/legacy/; not active workflow. No new root-level recipes.
Cached links/dictionary/vocabulary: links-build, dictionary-index, vocabulary-report.
Shared evidence/write guards: mgwiki_editor/artifacts.py. Reports never approve review.
Citation/metadata/rendering checks: docs/editorial-checks.md. Offline citation-audit,
metadata-audit, transcription-audit; scoped template-info/source-expand/render-check
broker actions;
license-evidence for guarded live rights metadata, license-report for cached claims;
control doctor for optional broker prerequisites. No automatic evidence/gate clearance.

Policy implementation: docs/policy-enforcement.md; deployment/API:
docs/broker-deployment.md. Typed ALLOW/DENY/DEFER evaluator, durable SQLite journal,
guarded execution/recovery, issue/section/evidence lifecycle, scoped Unix/MCP
broker and Linux isolation launcher implemented. Broker-configured CLI has no
direct-operation fallback. Default CLI uses existing guarded Wiki/Pywikibot auth;
no new broker socket/token required. Credentials unchanged, original guards retained.
Tests use fake services/local isolation; production OpenCode/credentials/services
not reconfigured. Whole-tool-process isolation and trusted launch intent required
before claiming hard enforcement. No article saved by implementation/testing.

## Installation
Run from this project directory. Python 3.11 or newer required.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[test]'
.venv/bin/python -m mgwiki_editor --help
```

The reference deployment reuses Pywikibot configuration, credentials and cookies
in `/home/jagwar/.pywikibot`; an explicitly set PYWIKIBOT_DIR overrides it.
Nothing is copied into this checkout.
The process account needs access to that private directory and its configuration.
Installing or testing the repository does not verify live authentication.
Do not make credentials world-readable. Run under the owning account or have an
administrator grant narrowly scoped access, including Pywikibot's runtime writes.

For a different deployment, configure Pywikibot outside this checkout and set
PYWIKIBOT_DIR to its private directory containing user-config.py. Example
non-secret settings (do not overwrite existing configuration):

```python
family = 'wikipedia'
mylang = 'mg'
usernames['wikipedia']['mg'] = 'Bot-Jagwar'
user_agent_description = 'mgwiki-editor; User:Bot-Jagwar; checked sandbox translations'
maxlag = 5
max_retries = 2
socket_timeout = (10, 30)
```

For the reference deployment, authenticate interactively using Pywikibot's
supported login workflow, for example
`PYWIKIBOT_DIR=/home/jagwar/.pywikibot .venv/bin/pwb login -family:wikipedia -code:mg`.
The external pwb command does not inherit the harness's Python-only default;
pass PYWIKIBOT_DIR explicitly when invoking it directly.
Keep bot passwords, OAuth credentials, cookies, and user-password.py private and
outside this checkout. Never paste credentials into an agent prompt or dictionary
request. Use an account permitted to edit its own sandbox and respect Wikimedia
bot policies and rate limits; this harness does not assert bot approval.

If using a virtual environment, activate it before starting OpenCode so the
agent's python3 resolves to that environment. OpenCode discovers the project
agent/skills automatically. Select mgwiki-editor or invoke:

```text
/mgtranslate https://en.wikipedia.org/wiki/Water ; Malagasy title: Rano
```

Command arguments are prompt text, not shell interpolation. No fixed model or
provider is imposed. Existing sessions may require selecting the new agent.

## Translation workflow
The agent loads the style skill and both local style references, without fetching
the source guides per article. New Malagasy text uses amin' ny / an' Andriamanitra /
amin' izao spacing; foreign acronyms have Malagasy parenthetical translations;
retained foreign terms, full foreign agency names and book/movie/paper titles
use MediaWiki italics. Full agency names also have Malagasy parenthetical glosses.
Names retain original order, explicitly including Chinese/Japanese/Korean/
Vietnamese names; verified Malagasy names use surname first, given names last.
Never guess name components. Protected quotations, titles and citation metadata
are not rewritten to impose prose spelling/order or remove words-to-watch.
The caution list is not a banned-word filter. These are local harness conventions,
not a claim that English Wikipedia rules automatically bind Malagasy Wikipedia.

Use a fresh job directory for each independent translation or rebase.

```bash
python3 -m mgwiki_editor init --source-lang en --source-title Water --article-title Rano --job runs/water-001
python3 -m mgwiki_editor lookup --edition en --word water --output runs/water-001/lookup-en-water.json
python3 -m mgwiki_editor lookup --edition mg --word rano --output runs/water-001/lookup-mg-rano.json
```

init pins complete source, existing Malagasy mainspace, and sandbox snapshots.
Use --existing-title if the intended Malagasy mainspace title differs from the
source's mg interlanguage link. Missing source is an error; missing target is a
normal new-page case. Redirects require explicit resolution. Existing sandbox
text becomes the initial draft; existing mainspace text is used when no sandbox
exists. Source and existing .wiki files are reference copies; job.json holds the
canonical pinned snapshots used for conflict detection.

Follow docs/edition-protocol.md. The coordinator reads the complete snapshots,
plans ordered sections (including lead and appendices), and delegates each to
mgwiki-section with local evidence and its own sections/<id>/ output directory.
Workers write section.wiki, notes.wiki and vocabulary.json locally; independent
sections may run concurrently, but workers cannot fetch remote data or publish.
Only the coordinator makes paced Wikipedia/dictionary requests, assembles
draft.wiki, merges shared notes/vocabulary, and checks cross-section consistency.
Missing/blocked sections require targeted follow-up, not whole-article generation.
Set review.json gates true only after real checks of the assembled article.

The mgwiki-section agent uses OpenCode V2's edit permission action to expose
the patch tool; a permission named patch does not enable that tool. Its default
deny rule keeps shell, network and nested delegation unavailable. Edit allowances
cover only section.wiki, notes.wiki and vocabulary.json beneath
runs/*/sections/*/. Shared job files, pinned inputs and project files stay denied.
The static rules do not select one dynamic assignment: workers must still honor
their coordinator-assigned exclusive directory. This is not OS-level isolation.
If patch is unavailable or denied, the worker reports blocked rather than
claiming a successful handoff or using another tool to bypass permissions.

```bash
python3 -m mgwiki_editor validate --draft runs/water-001/draft.wiki
python3 -m mgwiki_editor prepare --job runs/water-001
```

The agent reviews draft.wiki, changes.diff, preview.html offline, and proposal.json.
Compare existing
mainspace and sandbox content as well as the foreign source. A newly created
sandbox has an all-additions diff; this does not replace mainspace merge review.
Autonomous mode does not ask questions, tool/script permissions, or draft approval.
After successful editorial review, save the exact prepared proposal:

```bash
python3 -m mgwiki_editor publish --job runs/water-001
```

Optional --approve FULL_SHA256_FROM_PROPOSAL pins an explicit digest for callers
who want that check; it is no longer required. Digests still protect exact
content/evidence. Receipts record autonomous versus explicit-digest mode.
An actual translation/edit request authorizes sandbox completion; draft-only or
no-save instructions override it. Harness setup/tests never authorize saving.
Unresolvable missing input or translation/topic/merge uncertainty means preserve
work, record a blocked result, and stop without asking or guessing. Source
inconsistencies and article contradictions are nonblocking review issues: retain
them in runs/<job>/source-issues.md for later user review, not as failed gates.
Record stable ID, status, pinned revision/path/section, conflicting claims/citations,
draft handling, and next review action. Workers report issues in their notes.wiki;
the coordinator consolidates the memory before prepare and links it in the handoff.
Open issues survive publication and rebase, with history intact. Translate accounts
faithfully with existing attribution/uncertainty; never invent a reconciliation.
Independent unsafe content, copyright, citation integrity, unresolved translation
meaning, topic/merge identity, and technical/save guards remain mandatory.
Potential blockers go separately in runs/<job>/deferred-issues.md; independent
tasks continue. Later assign issues/local evidence to mgwiki-issues-solver;
coordinator alone accepts its issue-resolutions/<issue-id>.md proposals. See
docs/issue-recovery.md: safe HTTP 5xx retries >=15 seconds apart, longer guards
win; real permitted probe at/after 600 seconds confirms persistent outage before
dependent tasks are skipped. More than 25 distinct skipped tasks in same outage
requires fresh 5xx test and SEVERE SERVICE OUTAGE DETECTED in OpenCode output,
plus one simple paragraph with assessment, evidence, all blocked tasks and memo
path. These are agent instructions, not a new CLI background retry mechanism;
existing transport, dictionary lookup budgets and uncertain-save guards remain.
publish checks exact artifact hashes, live revisions, current rendering,
fixed account/site/namespace, and server-side revision/creation guards. It saves
synchronously with translation attribution and no cosmetic rewriting, then
reads back exact content. receipt.json confirms success or records an uncertain
attempt. An unconfirmed attempt blocks retries; inspect the live sandbox with
read --lang mg --title 'Mpikambana:Bot-Jagwar/Rano' --sandbox before any reconciliation.
Never delete a receipt merely to retry. Start a fresh reviewed job after resolving
the state. There is no force/mainspace/username override.

The fixed account is Bot-Jagwar; OAuth must identify that exact account. The
external credential directory remains /home/jagwar/.pywikibot; its filesystem
owner need not match the wiki account. Jobs prepared for the former Jagwar
sandbox are not accepted: initialize a fresh job, inspect existing texts, prepare
a new proposal, and autonomously review its exact draft. Never rewrite old job
snapshots or proposals to migrate them. No account migration authorizes a save.

## Dictionary contract
Default origin: http://192.168.1.155:8000. Override with MGWIKI_DICTIONARY_URL for a
trusted origin. Only GET /wiktionary-pages/{en|mg}/{encoded word} is called.
No /translations or /jobs endpoints: some of those publish Wiktionary edits.
The response is a list of entries with language, entry, part_of_speech,
definitions, and optional translations/additional_data. Page language and entry
language differ: mg/rano also contains non-Malagasy entries. Lookup filters by
entry language while retaining the raw evidence. The model selects a sense and
translates its definition; the CLI is not a translation engine.

For unfamiliar terms, define the intended sense in simple English and translate
that definition into Malagasy. If a lookup fails or supplies no suitable word,
use an accurate descriptive expression with the English term in parentheses
when useful. Record definition_origin as dictionary or editorial_simple_english;
never claim a manual definition came from a dictionary. A missing preferred word
alone need not block a draft; genuinely unresolved material meanings still do.

Medical terms use a Malagasy transcription or established equivalent followed
by (na [Malagasy explanation]); asthma is asma. The explanation must not invent
medical claims about the subject. Above 100 distinct uncertain English vocabulary
items (101 or more), keep unknown-vocabulary.wiki in the job for later review,
with sense, tentative wording and next action. Include it in the relevant
vocabulary.json evidence_files so proposal hashes protect that evidence too.
The list and threshold never waive editorial gates or exact content-integrity checks.

External references and External links URLs are preserved, not accessed by any
tool or script by default. No browsing, HEAD checks, DOI resolution, external
image/resource loading, redirects, package downloads or helper-script detours.
The agent does not request permission to do these; external research needs an
explicit user request. Inspect HTML previews offline, without loading resources.
Required Wikipedia CLI operations
and read-only dictionary lookup remain allowed. Unvisited sources must not be
described as verified. Unresolved factual disagreements alone do not block saving:
record them in source-issues.md and preserve source attribution/uncertainty.

During setup, the mg/rano and en/atom read endpoints were confirmed against the
provided service; /openapi.json was absent and /swagger.json listed no paths.
Repository route definitions supplied the actual contract. Network availability
and dictionary quality are not guaranteed. Missing pages (404), missing entry
languages, malformed data, and outages remain distinguishable. HTTP on the LAN
is unencrypted: send words only, never credentials or sensitive source material.

Dictionary HTTP 502: preserve bounded error-body evidence. Exact structured
type=error/status=502/details.type=NoPage means the service explicitly reports a
missing page, despite its incorrect HTTP status; record status=missing with
http_status=502 and missing_reason=backend_NoPage. Other 502s remain failed, never
invented missing words. They schedule up to ten retries after the initial attempt,
at least 15 seconds after each failed response; longer Retry-After wins. Per-lookup
budgets/deadlines persist in the shared state directory's dictionary-retries.json.
lookup returns retained failed evidence plus retry metadata before a deadline or
after exhaustion, without contacting the service. Resume due lookups between
useful translation/review work; no hidden retry, sleep, polling, or parallel worker
loop. Ordinary successful/missing replies end only that lookup's retry streak.
HTTP 429/503 and Wikimedia cooldown/circuit guards remain unchanged. A 502 alone,
pending retry, or exhausted retry budget does not block reviewed, accurate
descriptive translation; unresolved material meaning and other editorial/save
guards remain independent blockers. No automatic review attestation/publication.

## Mathematics vocabulary cache
The user-requested Kajy post, "ireo voambolana matematika malagasy" (19 April
2011), supplies 507 rows in data/vocabulary/kajy-mathematics.sqlite. JSON is retained
as the original import; runtime queries use SQLite. Its JS-only page required
the same post's Blogger feed to obtain the bilingual table. Source URL, author,
timestamps, feed/content hashes, source numbers and original cell text accompany
the candidates. No English equivalents or definitions are invented.

```bash
python3 -m mgwiki_editor vocab --language fr --word 'équation' --output runs/water-001/kajy-equation.json
python3 -m mgwiki_editor vocab --language fr --word equation --exact
python3 -m mgwiki_editor vocab --language mg --word 'fampimirana'
python3 -m mgwiki_editor vocab-audit --draft runs/water-001/draft.wiki --output runs/water-001/math-audit-01.json
```

Reads/searches are offline, case/accent-insensitive; source spellings stay intact.
The tool uses mode=ro, query_only, and bound SQL parameters. The entries table
exposes source_number, table_row, french, malagasy, indexed normalized keys,
candidate status and JSON-encoded source_cells/review_flags; metadata retains
source provenance and the original JSON hash. Query results include the exact
database_sha256 for job evidence. No refresh or remote write exists.
Offline rebuild to a new path (existing DBs are never overwritten):

```bash
python3 scripts/build_vocabulary_db.py --output data/vocabulary/new-mathematics.sqlite
```

Read mg-vocab and the persistent review memory
before selecting a candidate: split rows, placeholder numbering, suspected typos,
polysemy and alternatives require sense-specific handling, not global replacement.
This blog is terminology evidence, not dictionary verification or article-fact
authority. Keep normal sense checks and definitions; pin used results through job
vocabulary.json evidence_files. External research still needs an explicit request;
do not refetch per article. Source disagreements alone remain nonblocking.

For each untranslated mathematical term, the agent must inventory occurrences,
interrogate the DB, select the intended sense, then delegate grounded Malagasy
substitutions to section workers. English terms require a confirmed French sense
bridge; no English mappings are silently invented. Cover prose, headings,
captions, tables and displayed labels, while protecting quotations, names/titles,
citation metadata, formulae, exact link targets, identifiers, filenames and URLs.
Every inventory item must be translated/descriptively explained or deliberately
retained with reason. Re-audit and review the assembled draft; a zero-match audit
is not full coverage. vocab-audit reports possible French matches, never rewrites
the draft or chooses among competing senses. Existing jobs stay untouched unless
an article-edit task authorizes their revision. No blind global replacement.

## Country-name cache
Use the exact matching Malagasy page titles and diacritics from Sokajy:Firenena
to normalize country names in new prose. The saved list is in
data/country-names.json, with category URL, retrieval time and membership scope.

```bash
python3 -m mgwiki_editor countries
python3 -m mgwiki_editor countries --refresh
```

The first command reads the local cache only, without Wikipedia requests. If
missing, it asks for explicit refresh. The second fetches direct mainspace
members through Pywikibot and atomically replaces the cache only after checking
the result. An empty/failed fetch preserves the previous cache. Reuse the list
across translations instead of refetching per article; refresh when necessary.

The category is not a complete geopolitical registry: general/index pages,
historic states, territories and variants may appear, and countries categorized
elsewhere may be absent. Check identity, do not assume sovereignty, and use
verified local-page evidence for missing names rather than guessing a match.
Keep original quotations, bibliographic titles, identifiers and URLs unchanged.
Copy any naming evidence used into the job and list it in vocabulary.json
evidence_files to bind it to the proposal; never replace a prepared job's copy when
refreshing the shared cache. No command edits Wikipedia or changes categories.

CLI console JSON escapes Unicode so ASCII/Latin-1 terminals can display results
without reporting a false failure after saving local evidence. Evidence files
and article drafts remain UTF-8, preserving the original characters exactly.
When the process locale itself is not UTF-8, use PYTHONUTF8=1 for non-ASCII
command-line titles as well; console escaping alone cannot repair misdecoded
arguments. For example:

```bash
PYTHONUTF8=1 python3 -m mgwiki_editor read --lang mg --title 'Nôrvezy'
```

## Guarantees and limits
Use MediaWiki wikitext only for Malagasy translation/article content. Replies,
logs, handoffs, and memories use plain text/Markdown and caveman ultra; article
prose is never compressed. Compaction keeps OpenCode's supplied Markdown template
exact, using ultra only in free-text bodies. New commentary in legacy notes.wiki
and unknown-vocabulary.wiki files also uses plain text/Markdown. Existing pinned
source evidence stays unchanged. Internal prompts retain OpenCode's definition
format; CLI JSON, HTML previews, and diff files keep their required formats.
Tooling/memory artifacts are never pasted into Wikipedia. source-issues.md, when
present, is hashed into the proposal: later changes require fresh preparation,
but unresolved source issues are not publication blockers. Older jobs without
that memory remain supported; never rewrite historical evidence merely to migrate it.

Lint rejects common Markdown, broken named-reference reuse, missing native
reference renderers, inert [[:Sokajy:...]] article categories, live foreign
Category: links, interwiki links, and placeholders. It
permits MediaWiki * and # lists and {| tables. Markdown and MediaWiki share some
syntax; no lexical validator can prove the absence of all Markdown. Raw-text and
rendered autonomous editorial review remain mandatory. For predictable reference validation,
use native `<references />` instead of reference-rendering templates.

Rendered previews reject parser errors and language links. Live Sokajy membership
is expected article output. They do not automatically verify every local template parameter,
link topic, media license, source claim, grammar, or translation. Review gates are
attestations, not machine evidence of linguistic correctness. Render changes can
be benign (dynamic templates) but still require fresh preparation and review.

The CLI is a procedural safeguard, not a security sandbox against a malicious
agent/user with arbitrary shell access or credentials. Shell/edit tools are
allowed without prompts; scripts still must obey the project network and sandbox
policy. An unguarded script could bypass the CLI: arbitrary shell access means
this is not an OS network sandbox. Digests bind content, not human sign-off.
Use OS isolation/restricted credentials if stronger separation is needed.
Source/mainspace revisions are checked immediately before saving, but Wikimedia
cannot atomically lock three independent pages. Destination revision/create
guards protect against lost updates; later source changes require a new edition.

## Autonomous scripts and Wikimedia load
Local Python scripts remain available as persistent agent knowledge. Inspect/run
any task-relevant script with python3 ./name.py or python3 scripts/name.py; create
helpers as needed, without asking. Helpers that contact Wikipedia use
mgwiki_editor.core.Wiki, or call mgwiki_editor.network.install_wikimedia_transport()
before constructing Pywikibot sites. Do not use arbitrary scripts to evade guards.
No interactive login/password/captcha prompts: unavailable credentials block the
task with a local draft, not a request to the user.

The transport guards actual HTTP attempts, including Pywikibot retries, sharing
a locked state file across CLI processes and languages at
$XDG_STATE_HOME/mgwiki-editor/wikimedia-requests.json (default ~/.local/state/…).
Only required HTTPS Wikipedia APIs and central-auth API endpoints are allowed;
redirects are rejected. Requests are spaced by 10 seconds, the conservative end
of the requested 5–10 second range; edits are at least 10 seconds apart. Longer
server cooldowns take precedence. Dictionary requests share pacing because they may
cause upstream reads. Independent article translation tasks may run concurrently;
each coordinator keeps remote operations serial through the same shared gate.
Reuse job evidence/caches; no within-job parallel fetching or per-paragraph rendering.

429/503, maxlag and ratelimited stop the current command and persist exponential
backoff starting at 30 seconds plus jitter. Retry-After seconds and HTTP dates
are honored without truncation. Three consecutive overloads open a 15-minute
circuit. Shared-slot contention may wait up to 600 seconds total per gate;
repeated extensions do not restart the budget. Server cooldown waits retain a
separate 10-second gate limit; longer cooldowns defer immediately. Cooldowns are
preserved, not shortened or reset. This queue budget does not extend socket
timeouts, replay HTTP requests, or authorize concurrent writes to one sandbox.
Do not immediately rerun a failed command, poll aggressively, reset shared state,
or switch account/process to evade cooldowns. Socket timeouts and maxlag=5
provide additional bounds. Uncertain writes are never
automatically resubmitted. These limits reduce load, not guarantee zero 429s.

Only the shared transport owns normal pacing. Native Pywikibot throttling can
multiply delays by its registered process count; it is disabled after the shared
guard is installed. Native retry sleeps are disabled too. Do not add shell sleep
loops or wait between local-only steps. A command can need several API requests;
tool stderr emits compact request-start/response and wait/deferred events so
actual work is visible. Diagnostics omit page titles, bodies and credentials;
normal command-result JSON remains on stdout.

## Verification

```bash
python3 -m pytest
ruff check mgwiki_editor tests
ruff format --check mgwiki_editor tests
```

Tests are offline. Live Wikipedia login/read/render/save must be smoke-tested by
the operator with their own credentials; harness setup does not perform edits.
