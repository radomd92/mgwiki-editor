# Broker, citation, metadata and rendering checks

Local implementation; no production activation or remote save implied. Default
execution uses existing guarded Wiki/Pywikibot credentials, unchanged. Optional
strict broker operations use run capability, coordinator role and evidence journal;
ordinary CLI requires no broker socket/token. Shared transport pacing always applies.
No worker network access, unscoped HTTP, fallback, capability self-provisioning,
credential changes, package downloads or external-reference access.

## Broker readiness

```sh
python3 -m mgwiki_editor.control doctor
```

Uses paired MGWIKI_BROKER_SOCKET/MGWIKI_CAPABILITY_FILE. Alternatively supply both
--socket and --capability-file; explicit flags never mix with ambient settings.
Inspects descriptor types, symlinks, ownership and owner-only permissions. Reads
no token contents, connects nowhere, starts nothing, changes no access rights.
Exit1: missing/unsafe prerequisite. Exit0: local descriptors present, **not verified
deployment**, account, isolation, authorization or service availability. Capability
loader separately rejects group/world-readable or wrong-owner files; no chmod fix.

Trusted host setup remains docs/broker-deployment.md. Once trusted launcher supplies
isolated process/configuration, authenticated broker status can inspect run. Doctor
never manufactures capability or adopts an old job to remove deployment blocker.
Doctor checks optional strict-profile readiness only; missing configuration does not
block default guarded CLI work. Do not run activation/setup merely for normal auth.

Trusted-host activation now available:

```sh
python3 -m mgwiki_editor.control activate --config /srv/mgwiki/private/activation.json --check-only
```

Unlike doctor, authenticates existing scoped grant via local broker `status`.
Without `--check-only`, launches host-approved isolated complete tool process.
Protected config contract/examples: docs/broker-deployment.md. No self-issued
authority, service setup, account verification or proven full-tool integration.

## Citation antecedents

```sh
python3 -m mgwiki_editor citation-audit --job runs/example --output runs/example/citation-audit-01.json
```

Purelocal: exact source.wiki/default draft.wiki hashes, scoped optional --draft,
decoded reference groups/names, dangling/conflicting definitions, op.cit./loc.cit./
ibid. and plain author/page shortrefs. Searches explicit local bibliography/ref
entries for author-label candidates. Same surname/page overlap is **not an identified
work/edition/quotation connection**. Even unique candidate stays review-required;
no correction or gate mutation. Unknown antecedent stays needs-evidence. Empty draft
reported explicitly. URLs remain data; no original work or reference fetched.

Configured CLI routes through broker citation-audit; no direct fallback. Broker
arguments: optional draft, job-relative. Broker records derived report provenance.
Actual evidence-backed article correction still assigned to section worker.

## Metadata collection / audit

Broker actions via existing mgwiki tool or CLI broker --action/--arguments:

| Action | Arguments | Result / limits |
| --- | --- | --- |
| template-info | titles:1..50 explicit Template:/Endrika: titles | Actual mg namespace10, revision IDs/timestamps/sha1/main-slot content; missing/redirect bodies preserved, no redirect following or parameter-contract inference |
| source-expand | index:nonnegative integer | One exact call from pinned source inventory templates list, source revision/hash/context retained; no caller-supplied text/title/language |
| image-info | filename | Existing mgwiki availability/extmetadata read, now also image timestamp/sha1; no image resource fetch |
| metadata-audit | evidence:job-relative JSON files; optional draft | Derived scoped file/template/expansion gaps; no license/contract approval |

Source expansion uses **current template dependencies**, not reconstructed historical
expansion at source revision. Raw output supplies candidates for exact file/variant
mapping; not license or same-topic proof. Missing/unsafe index, changed pinned source
or frozen run rejected before request. All metadata requests serialized/paced by
existing transport; no retry loop, external resources, guessed flag filenames.

```sh
python3 -m mgwiki_editor metadata-audit --job runs/example --evidence evidence/image-info-01.json --evidence evidence/template-info-01.json --output runs/example/metadata-audit-01.json
```

Offline cached evidence only; configured CLI routes broker. Matching expansion calls
add exact returned file candidates. Country page_image_free never substitutes for
file license/availability. Commons file may have missing local description page
and still imageinfo/shared repository: preserve distinction. Conflicting snapshots
retained, not silently selected. License restrictions/raw imageinfo preserved;
license_approved/parameter_contract_approved remain false, even metadata present.
Review actual restrictions/context/compatibility separately. Evidence file hashes
are byte provenance, not authenticated origin or editorial judgment by themselves.

## Image-license evidence

License evidence = retained file-version/license/author/restriction metadata;
not purchase, guessed permission or automatic legal clearance. No image, license
URL, author link or external reference fetched. Embedded HTML remains raw data.

Default live collection, using unchanged existing Wikipedia auth/transport:

```sh
python3 -m mgwiki_editor license-evidence --filename 'Exact image.svg' --output runs/example/license-01.json
```

Calls existing `Wiki.file_metadata` via guarded mgwiki API only. No new credential
management, broker, service or grant. Output records `origin=wiki_image_info_read`,
API/capture time/raw response and same conservative classifications. Standalone
capture is not protected broker-journal provenance. Reusing local bytes through
license-report still marks cached origin unverified. No publication or gate mutation.
If broker settings explicitly configured, same command routes broker with no fallback.

| Broker action | Arguments | Result / limits |
| --- | --- | --- |
| license-evidence | filename:exact bare filename | Guarded mgwiki imageinfo read; exact namespace6/title matching; raw response, version timestamp/SHA1, rights fields; journal-bound capture |
| license-report | evidence:job-relative JSON; filename:exact bare filename | Offline derivation from pinned image-info/raw response or capsule; no remote read |

Standalone cached report:

```sh
python3 -m mgwiki_editor license-report --job runs/example --evidence evidence/image-info-01.json --filename 'Exact image.svg' --output runs/example/license-01.json
```

Output exclusive: existing path refused. Configured CLI routes broker, no direct
fallback. Inputs unchanged. Report includes input byte SHA256 and canonical JSON
response SHA256; latter not hash of original transport bytes. Raw response retained.
Exact title absent/ambiguous, malformed/failed/continued/warning response -> error;
no guessed file or redirect mapping. Missing imageinfo remains unavailable; missing
local description may coexist with shared-repository imageinfo.

Origins:
- `wiki_image_info_read`: default CLI guarded live metadata read, existing external
  Pywikibot authentication; no broker-authenticated provenance claim.
- `unverified_cached_input`: standalone/historical input; embedded origin/approval
  claims ignored. Byte hash alone not authenticated source.
- `broker_image_info_read`: guarded live read, broker capture time/API recorded.
- `broker_pinned_file_metadata`: broker reuse only when protected journal kind
  (`image-info`/`license-evidence`) and exact input hash match. Changed bytes lose
  authenticated-origin label. Derived report time not substituted for capture time.

Canonical Creative Commons URI candidates: BY/BY-SA, CC0; public-domain mark remains
claim requiring review. URI lookalikes/unknown forms unrecognized. NC/ND or explicit
`NonFree=true` -> not free-reuse candidate. BY/BY-SA with false attribution-required
flag -> conflicting metadata. Unsupported licenses retained without guessed identity.
All classifications conservative metadata claims, **not approvals**.

Every capsule/version has `license_approved=false`. Retain raw Artist/Credit/
Attribution/UsageTerms/Restrictions/Permission fields; inspect requirements and
actual intended use separately. `version_fields_present` means timestamp/SHA1 fields
exist, not verified version identity. Restriction flags (e.g. `insignia|noresize`),
authorship, jurisdiction, personality/trademark rights and exact source-template
file mapping still require review. Cached flag candidates never establish source
flag expansion or clear map rights/template contracts. No article/gate changes.

## Rendering and Cite graph

Broker render-check takes no arguments. Requires accepted full section scope and
assembled draft; never accepts alternate title/text. RENDER_PREVIEW policy checks
fixed sandbox destination/shared transport. Can run before editorial attestations
to inspect parser output without falsely setting gates. Pins exact draft/HTML hashes
and HTML/report as evidence; stage/review/proposal/receipt unchanged. Does not load
HTML resources. Frozen/save-attempt runs refused; no save occurs.

Structural lint/inventory now includes delayed core #tag:ref/#tag:references and
list-defined references, decodes XML names/groups, keeps inner default citation
distinct from outer note group, requires each renderer. Duplicate/dynamic attributes,
raw nested refs, conflicting definitions rejected instead of silently ignored.
Unknown arbitrary templates not expanded by offline parser.

Wiki.render additionally checks HTML error classes, missing-template redlinks,
dangling Cite anchors, duplicate Cite IDs and active script/iframe elements. Existing
parser category/langlink rejection and live render digest guards unchanged. Render
success proves structure only; whole-article translation, license, attribution,
template semantics and raw/offline preview editorial review still mandatory.

## Tests / authorization boundary

Tests use fake Wiki/API, local strings/sockets and isolated fixtures only. No live
account, metadata probe, reference URL, image download or save. Source disagreements
remain nonblocking; genuine missing meaning/provenance/rights still deferred.
Optional strict deployment is not default-auth blocker. New checks never fabricate
missing citation antecedents or clear gates.
