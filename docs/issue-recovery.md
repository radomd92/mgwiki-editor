# Deferred issues + service recovery

Agent policy; not a new CLI retry daemon. Read before coordinator work. Autonomous
mode default unless user specifies otherwise: no questions, approval prompts, or
credential requests during run. Resolve only from authorized evidence. Never guess
material facts or weaken review/save/network guards to keep moving.

## Durable issue memo

Potential blockers → `runs/<job>/deferred-issues.md`, separate from article prose,
`vocabulary.json`, and nonblocking `source-issues.md`. Before successful init, use
`runs/<run-id>/deferred-issues.md`; do not fabricate `job.json` or pinned snapshots.
Keep existing work; continue independent tasks. Stop only dependent work when
critical input, meaning, identity, safety, citation, or save state remains unknown.
Missing sections still block full-article completion; skipped never means complete.

Each issue records:
- Stable issue ID; article/job; section/task IDs; open/blocked/skipped/resolved status.
- Exact uncertainty/error; evidence paths, source revisions, citations where known.
- Blocking scope/dependencies; work retained; safe fallback used and its rationale.
- Attempt timestamps/results; service identity; next eligible retry; next action.
- Resolution history, evidence, coordinator acceptance; never erase prior failures.

Link memo from `notes.wiki` and final handoff; retain after publication/rebase.
Unknown material meanings remain unresolved in `vocabulary.json` too; memo never
waives gates. Source disagreements stay nonblocking in `source-issues.md`; link
their IDs rather than relabeling them as blockers. Markdown/plain text, caveman
ultra commentary; machine data and verbatim evidence exact. No secrets in memos.

Later resolution: delegate explicit issue IDs to `mgwiki-issues-solver`,
with memo, pinned local evidence, and exclusive
`runs/<job>/issue-resolutions/<issue-id>.md` output. Solver proposes evidence-backed
fixes or records missing evidence, never invents a resolution. No need to invoke
solver during blocked run. Coordinator alone accepts proposals, updates shared
memo/evidence, delegates article corrections to `mgwiki-section`, rechecks affected
gates, and freshly prepares changed proposals. Solver cannot fetch or publish.

## HTTP 5xx recovery

Genuine HTTP 500–599, including 502 → suspect transient restart, not proven cause.
Retry safe, idempotent reads several times while recovery window remains open.
Minimum cooldown: 15 seconds after failed response. Longer `Retry-After`, shared
request pacing, exponential backoff, circuit breaker, or persisted per-lookup
budget wins. Never retry uncertain writes; confirm through existing paced
receipt/read-back procedure or retain blocked status. No hidden/native retries,
parallel requests, manual shell sleep/poll loops, or alternate-host/tool bypass.

Use existing guarded CLI/tool operation; each real retry consumes normal request
budget. Persist next eligible attempt; resume due retries between useful offline
tasks, without minute-long blocking waits. Existing ten-retry dictionary budget
remains intact. After its exhaustion, do not replay that lookup or reset its
budget; a later authorized, known-good read may test service health instead.
If no useful work or due permitted retry remains, retain deferred status/deadline
and hand off; never claim ten minutes were observed without timed evidence.

Exact structured dictionary `type=error/status=502/details.type=NoPage` is
missing-page evidence, not outage. Preserve raw body/status. Arbitrary `NoPage`
text is not enough. HTTP 429/maxlag/ratelimited retain overload handling, not 5xx
classification. Other failures (auth, missing input, malformed data) stay distinct.

## Ten-minute outage test

Persist service-scoped ledger in `deferred-issues.md`: service/tool identity,
outage episode ID, first qualifying failure UTC/time, actual probes with response
timestamps/status/evidence, next eligible probe, last success, dependent task IDs,
and deduplicated skipped count. Redact credentials; separate unrelated services.
Restore ledger on resume; do not reset first failure to extend retry window.

Ten minutes = 600 seconds since first qualifying failure. At/after deadline,
test service with a real authorized read-only request through existing guarded
transport; use an eligible retry or known-good minimal read, not cached failed
output. No external URL/HEAD/health endpoint guessing. A timer, retained lookup
result, gate refusal, or unrelated tool failure is not a service test.

Continued qualifying 5xx on that test with no intervening successful service
response → mark service down; skip its remaining dependent tasks for this run,
recording each stable task ID and reason. Successful/missing-page replies end
continuous outage episode; a later 5xx starts a new episode. Non-5xx failure does
not prove recovery or continuous 5xx outage; retain unknown/deferred status.
If cooldown prevents deadline probe, defer test until allowed; never bypass
15-minute circuit or report a confirmed outage solely from elapsed time.

After down classification, batch dependent skips against recent real probe
evidence (at most 15 seconds old). If stale, retest when allowed before extending
confirmed skipped count; otherwise record pending/deferred tasks, not tested skips.
Repeated attempts, duplicate task IDs, memo entries, and retry attempts do not
inflate count. Independent services/offline tasks continue. Optional dictionary
outage may use accurately reviewed descriptive translation; required missing
evidence/sections or save checks still block publication. Never silently drop
article scope or claim skipped work succeeded.

## Severe outage output

More than 25 distinct tasks skipped = at least 26, within same continuously down
service episode. Before alert, test service again when eligible; no intervening
success, and fresh qualifying 5xx required. Cooldown/unknown result → alert check
deferred, not invented confirmation. Deduplicate alert per episode; persist alert
time and task IDs. A recovered/new episode starts its own count, retaining history.

Emit exact line in OpenCode output, not only memo:

SEVERE SERVICE OUTAGE DETECTED

Then one simple paragraph: service identity; observed outage duration/probe times
and statuses; assessment (restart suspected, cause unconfirmed); count and all
blocked/skipped task IDs; retained-work/memo path; next safe action. No per-task
progress spam. Final handoff includes alert if triggered and both blocked/skipped
status and memo path. Alert never authorizes skipped review/save guards.
