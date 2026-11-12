# Scoped broker: operation + deployment

Optional strict profile, not default authentication. User selected existing guarded
CLI/Wiki with unchanged external Pywikibot credentials; no broker socket/token
required for ordinary work. Missing optional deployment alone not publication
blocker. This document's deployment requirements apply only when selecting strict
broker execution. Explicitly configured broker still fails closed; no silent fallback.
All modes retain editorial/account/sandbox/revision/proposal/receipt/transport guards.

Implemented/tested locally; no production OpenCode/service/credential configuration
changed. Tests use fake HTTP/Wiki and local Unix sockets. Namespace/adversarial
worker tests pass here. No live Wikipedia/dictionary/account verification or save.

## Trust boundary

- Agent tools: credential-free, no direct egress. Trusted broker: installed code,
  private jobs/journal, existing external credentials, guarded actual requests.
- **Isolate entire tool-execution process.** Isolating one helper/MCP client does
  not constrain unrestricted tools in parent OpenCode server or other MCP servers.
- Runtime read-only; dedicated work writable; exact scoped capability/socket only.
  Never mount host root/home/proc/run, credential directory, private broker tree,
  or another worker's capability. No arbitrary HTTP/eval/execute/delete/move RPC.
- Pure dataclasses/role strings are not capabilities. Unrestricted Python/shell
  outside this boundary retains its OS privileges. No false hard-enforcement claim.
- Editorial records prove attestations bind bytes, not factual truth, neutrality,
  fluency, topic identity or licensing. Actual autonomous editorial review required.

## Trusted host setup — not agent tools

Examples only, not executed during implementation. Use operator-controlled runtime
outside agent writes, Python 3.11+, existing Pywikibot/mwparserfromhell dependencies.
No package download, credential copy, existing access-right changes or login prompt
authorized here. Keep scoped capabilities outside project/Git/prose/progress logs.
Stage cached `data/country-names.json` at private workspace's same relative path;
configure existing cached mathematics SQLite path. Reference data only, no
credential copy or per-article external fetch. Missing cache -> retained/deferred
work, not invented country/terminology evidence.

Create **new** private workspace/store; never adopt/overwrite an existing job:

```sh
python3 -m mgwiki_editor.control create --workspace /srv/mgwiki/private --state /srv/mgwiki/private/policy.sqlite
```

Trusted launcher binds original user request, not agent-provided publication claims.
Example manifest, only for an actual user-authorized translation:

```json
{
  "intent": "sandbox_edit",
  "source_language": "en",
  "source_title": "Water",
  "article_title": "Rano"
}
```

Intent: `sandbox_edit`, `draft_only`, `development`. Optional `existing_title`.
Critical missing/ambiguous identity -> memo/blocked, no questions or guessing.
Strict planner supports full pinned source; custom partial ranges explicitly
unsupported, never silently converted into full/partial publication.

```sh
python3 -m mgwiki_editor.control provision --workspace /srv/mgwiki/private --state /srv/mgwiki/private/policy.sqlite --run water-001 --manifest /srv/mgwiki/operator-intent.json --capability-output /srv/mgwiki/private/water-001.cap
```

New capability file mode 0600; token never printed. Default 24h expiry, max 30 days.
Trusted `control renew` takes same workspace/state/run/output/expiry options, no
manifest: preserves original intent, receipts and gates. Neither admin operation
exists in RPC/MCP. No agent can renew/promote its own capability.

Config outside agent writes; replace UID with actual verified host client UID:

```json
{
  "workspace": "/srv/mgwiki/private",
  "state": "/srv/mgwiki/private/policy.sqlite",
  "socket": "/srv/mgwiki/private/broker.sock",
  "allowed_uid": 1000,
  "dictionary_url": "http://192.168.1.155:8000",
  "vocabulary_database": "/srv/mgwiki/reference/kajy-mathematics.sqlite"
}
```

```sh
python3 -m mgwiki_editor.control serve --config /srv/mgwiki/broker.json
```

One serial worker; existing sockets never removed at startup. Shared request state
must remain common across processes/languages; no alternate identities/homes/gates
to evade cooldowns. Credential path stays existing external Pywikibot directory;
missing access blocks, never prompts for secrets or changes permissions.

## Isolated client / OpenCode integration

Standard-library-only stdio MCP client:

```sh
python3 -m mgwiki_editor.control mcp --socket /run/mgwiki/broker.sock --capability-file /run/mgwiki/capability
```

Register via installed OpenCode V2 MCP mechanism. No guessed configuration fields/
hooks or global settings edits shipped. Provider/control-plane connectivity needs
separately restricted IPC. Current sandbox grants no arbitrary network exception.
Verify **all** native/remote tools use restricted profile before actual deployment.
Unverified setup -> blocked publication, retained memo, no direct-Wiki fallback.

Local inspection, no service requests:

```sh
python3 -m mgwiki_editor.control sandbox-check --work /srv/mgwiki/agent-work --code /srv/mgwiki/agent-runtime
```

Explicit launch; executable must exist in mounted `/usr` or `/app`:

```sh
python3 -m mgwiki_editor.control sandbox-run --work /srv/mgwiki/agent-work --code /srv/mgwiki/agent-runtime --socket /srv/mgwiki/private/broker.sock --capability-file /srv/mgwiki/private/water-001.cap --private-root /srv/mgwiki/private --private-root /home/jagwar/.pywikibot -- /app/bin/approved-tool-server
```

Dedicated runtime/work disjoint, private roots outside both. Launcher clears env,
closes inherited FDs, drops capabilities, disables privilege gain/nested user
namespaces; private mount/pid/net/user namespaces, `/proc`/home/tmp. Kernel/tool
failure -> fail closed, no fallback. Launch from standalone trusted process, not
threaded app using `preexec_fn`. For staged Python source use fixed trusted
entrypoint adding `/app` to `sys.path`; never user-controlled broker `PYTHONPATH`.

Paired `MGWIKI_BROKER_SOCKET` / `MGWIKI_CAPABILITY_FILE` routes compatible existing
CLI commands through broker. Partial settings/mismatched run/denial/connection
failure -> no fallback. Without broker settings, default CLI uses existing guarded
Wiki/Pywikibot authentication. No credential changes or new socket/token required;
original checks retained, **not strict capability/isolation mode**.

### Checked activation with existing authority

Trusted host only; never broker/MCP action. Broker must already run with an existing
scoped grant. Activation neither starts broker nor provisions/renews capabilities.
Keep host specification outside agent writes, owner-only regular file, <=64KiB.
All paths absolute/no symlinks; config/socket/capability under declared private
roots; existing private roots disjoint from existing runtime/work directories.
Config, socket and capability owned by invoking UID, no group/other permissions.
Host must protect parent directories and runtime from untrusted replacement.

Example `/srv/mgwiki/private/activation-water-001.json` (data, not executed):

```json
{
  "work": "/srv/mgwiki/agent-work",
  "code": "/srv/mgwiki/agent-runtime",
  "socket": "/srv/mgwiki/private/broker.sock",
  "capability_file": "/srv/mgwiki/private/water-001.cap",
  "private_roots": ["/srv/mgwiki/private", "/home/jagwar/.pywikibot"],
  "executable": ["/app/bin/approved-tool-server"],
  "run": "water-001",
  "manifest": {
    "intent": "sandbox_edit",
    "source_language": "en",
    "source_title": "Water",
    "article_title": "Rano"
  },
  "tool_scope": "whole_tool_process"
}
```

`executable`: argument array, absolute executable inside mounted `/usr` or `/app`,
never shell text. `manifest`: exact originally provisioned object, including optional
`existing_title`; no intent promotion. `tool_scope` accepts only `whole_tool_process`.

```sh
python3 -m mgwiki_editor.control activate --config /srv/mgwiki/private/activation-water-001.json --check-only
python3 -m mgwiki_editor.control activate --config /srv/mgwiki/private/activation-water-001.json
```

First command validates mounts and makes one authenticated Unix `status` request
(10s timeout), checking exact run/manifest/intent and unchanged grant/socket. No
launch, Wikipedia/dictionary/account request or save. Second repeats checks, then
launches existing fail-closed isolation profile; nonzero child result -> CLI exit1,
actual child `returncode` retained in JSON. Errors -> exit1, no permissive fallback.
No token/config contents returned; report pins config SHA256.

`whole_tool_integration=host_declared_not_automatically_proven`: host declaration,
not proof arbitrary executable contains every tool or safe provider IPC. Check-only
does not launch/prove namespaces. Successful process exit proves neither complete
OpenCode integration nor account/rights/editorial/save readiness. Trusted host must
verify full-tool/control-plane integration separately; no generic network grant.

## Typed operations

MCP tool `mgwiki`: `{ "action": "status", "arguments": {} }`. Newline-JSON Unix
envelope: schema 1, capability, command, arguments. Closed command/field schemas;
duplicate keys/nonfinite JSON rejected; max message 6MB; peer UID verified.

| Actions | Required data / purpose |
| --- | --- |
| `status`, `init` | `{}`; status or pin trusted manifest, no caller-selected alternate identity |
| `artifact` | `name`; optional 1-based `offset`, `limit<=2000`; exact UTF-8 chunks/full digest/next offset |
| `artifact-history` | `name`, optional `sha256`; own-artifact archived bytes, never delete/reset |
| `plan` | Optional heading `level`; full ordered lead/body/appendix plan |
| `plan-local` | `id,source=existing|sandbox,start,end,after`; pinned local-only contribution, explicit integration position; no unseen source text |
| `assign`, `revoke-assignment` | Existing `id`; assign also `role=section_worker|issue_solver`; no coordinator delegation |
| `submit` | `name,content`, optional `expected_sha256`; exclusive/compare-and-replace, history kept |
| `submit-assigned` | Same + protected `worker_capability`; coordinator imports offline output under child's exact scope; audit says proxy |
| `accept-section`, `assemble` | `id,note` / `{}`; exact source/fragment evidence, all accepted/current sections, no missing scope fallback |
| `read`, `lookup` | `language,title[,sandbox]` / `edition=en|mg,word`; permitted reads only; no caller-selected dictionary origin |
| `countries`, `vocab`, `vocab-audit` | Cache read/explicit refresh; `word,language=fr|mg,exact`; optional job-relative audit `draft`; no dictionary verification from Kajy |
| `links-query`, `image-info`, `category-info` | `language,titles` / `filename` / `titles`; <=50-title API metadata batches, no resource download |
| `template-info`, `source-expand` | `titles` explicit local namespace10 revision bodies / `index` exact pinned-source template call; no caller-supplied expansion text |
| `license-evidence`, `license-report` | `filename` exact bare file / `evidence,filename` pinned file metadata; version/license/attribution/restriction capsule, never rights approval |
| `citation-audit`, `metadata-audit`, `render-check` | Local antecedent candidates / pinned metadata gaps / guarded full assembled-draft sandbox parse; diagnostics never editorial approval |
| `coverage`, `links-build` | `{}` / `source_language,evidence[,local_evidence]`; pinned offline inventories/maps |
| `dictionary-index`, `vocabulary-report` | Pinned `lookups`; report optionally job-relative `vocabulary`; no invented senses |
| `record-issue` | `id,kind,details,next_action,blocking,evidence[,section]`; source also conflicting `claims=[{claim,citation},...]`, `handling`, nonblocking |
| `accept-issue` | `id,note,evidence`; solver proposal required, no automatic review/save clearance |
| `review` | All `gates`, `note,evidence`; optional `omissions={images:{name:reason},urls:{url:reason}}`, genuine `category_evidence` |
| `prepare`, `attest-proposal`, `publish` | `{}` / exact `digest,note` / `{}`; actual autonomous raw/offline review, exact hashes/live revisions/account, durable claim/read-back |
| `reconcile` | `{}`; read-only unknown-save check; never resubmit, unchanged baseline revision not proof of new save |
| `task-depend`, `skip` | Planned section `task,service` / registered `tasks,service`; service `dictionary|wiki|mgwiki`, fresh actual failed probe |
| `service-probe`, `resume` | `service` / recorded safe-read `task`; real observed response flag; never reset lookup budget/replay writes |
| `ack-alert` | `episode`; output before acknowledgement, durable at-least-once delivery |

Paths job-relative in private workspace, never arbitrary host paths. Worker reads
pinned context + assigned files; writes assigned section trio or issue proposal
only. No remote requests/shared writes/nested delegation/acceptance/publication.
Existing offline OpenCode read/patch workers need no new shell/network grants:
coordinator exports pinned context, imports exact bytes via `submit-assigned`.

## Review / issues / history

Ordered sections accepted by exact hashes; source/local content, terminology,
references/anchors/images/links reconciled before whole-article review. Vocabulary
needs sense, English/Malagasy definitions, honest origin and actual pinned evidence.
Dictionary-verified claims require genuine lookup provenance; math entries need
read-only SQLite query evidence. >100 distinct uncertain English terms -> linked
Markdown memory, no article TODOs. Accurate reviewed descriptive wording remains
valid during dictionary outage; unknown material meaning remains blocked.

Generated partial markup coverage report surfaces losses; missing images/citation
URLs need explicit reasons. Existing category strings/order preserved except
inert-to-live conversion; additions require genuine mgwiki namespace evidence.
Semantic coverage, relevance, caption accuracy and safe licensing remain editorial
review.

Review/evidence snapshot binds actual referenced bytes, not merely pointer hashes.
Prepare then inspect raw text/offline HTML/diff without resource loading, attest
exact digest, publish once only if original request authorized it. No human
signoff prompt. Prepared/save-attempt jobs frozen; corrections use fresh trusted
run with earlier work retained. Old snapshots/proposals/receipts never rewritten
to migrate or bypass a failed guard.

Later issue proposals allowed on frozen/published runs without reopening save.
Coordinator acceptance invalidates old review; no automatic article rewrite/gate
clearance. Source contradictions separate/nonblocking, with revision/claims/
citations/handling/history. Material meaning/safety/copyright/identity independent.

Append-only `deferred-issues.md` projections retain legacy prose; source memory
separate. Before init: `runs/<run>.intake/`, no fake snapshots/job. Successful init
inherits exact intake lookup evidence, retains originals. Runtime telemetry does
not mutate prepared editorial snapshot; new material issues still deny publication.

## Recovery / severe output

Actual HTTP boundaries only; 15s minimum after genuine 5xx, longer Retry-After/
shared cooldown/circuit wins. Native retries disabled; transport or observation
failure fatal at Pywikibot boundary, never replays edits. Structured NoPage !=
outage. Cached failures/gate refusals/health attempts do not inflate probe/task counts.

Real failed probe at/after 600s + reliable elapsed evidence confirms down and
automatically skips pending dependent tasks. >15s-old evidence cannot extend
confirmed skips. Stable run/task IDs deduplicated within service episode; completed
work excluded. Independent local work continues. No sleep/poll retry daemon;
resume due reads between useful work or later explicit resume.

26+ distinct skips require a new permitted 5xx probe after threshold. Outbox emits
exact severe marker + one paragraph: timed evidence, assessment, all task IDs,
memo paths, next safe action. Client prints stderr + retains JSON alert. Agent
includes alert in final handoff if tool stderr not visible. Output/ack failure
retains replay warning, never hides a completed operation or retries save. Console
exactly-once across crashes impossible; logical alert deduplicated by episode.
Subsequent recovery appended to pending assessment. Reboots/clock jumps retain
history; reliable stable elapsed evidence required, no invented ten-minute wait.

## Migration / activation

Offline readiness/check details: docs/editorial-checks.md. `control doctor` checks
paired environment/explicit paths without token reads/connections/setup; never
claims deployment verified. Actual capability loading requires owner-only regular
file owned by client UID. Existing access rights never changed automatically.

```sh
python3 -m mgwiki_editor.control inspect --job runs/old-job
```

Read-only inspection; no adoption, invented review, state/cooldown/receipt reset.
Corrupt/unknown SQLite schema fails closed. Rollback must not re-enable direct
publication fallback. Offline suite + Ruff required. Actual activation additionally
needs trusted OpenCode/provider/whole-tool-process integration and account access
under deployment identity. Prerequisites tracked in
`runs/policy-enforcement/deferred-issues.md`; no credentials/setup questions.
