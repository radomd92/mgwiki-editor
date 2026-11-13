# Security policy

## Supported versions

The project is pre-1.0. Security fixes target the current `main` branch and the
latest tagged release, if any. Older snapshots are not maintained.

## Reporting a vulnerability

Please do **not** open a public issue for a suspected vulnerability, leaked
credential or privacy problem.

Use GitHub's private vulnerability reporting for this repository
("Security" tab → "Report a vulnerability"). If that is unavailable, contact the
maintainer through the repository owner profile and include only the minimum
detail needed to establish contact.

Include, when possible:

- affected version or commit
- a description of the impact
- reproduction steps using synthetic data
- whether credentials, live wiki pages or user data may be involved

Do not include real bot passwords, OAuth tokens, cookies, private keys, personal
data or copyrighted article text in a report.

## Credential handling

- Pywikibot configuration and credentials live outside the checkout; the
  harness only reads the directory named by `PYWIKIBOT_DIR`.
- Never commit `.env` files, `user-config.py`, `user-password.py`, `.pywikibot/`,
  capability tokens or cookie files.
- `.gitignore` is a precaution, not a complete secret scanner. Review staged
  changes before pushing.
- Do not paste credentials into agent prompts, dictionary requests, issue
  reports, logs or test fixtures.

## Scope and limitations

The CLI enforces proposal digests, fixed destination/account/namespace checks,
revision and create guards, transport pacing and uncertain-write handling. It is
a procedural safeguard, not an operating-system sandbox: an operator with
arbitrary shell access and valid credentials can bypass it. Use OS isolation and
narrowly scoped credentials when stronger separation is required.

The harness is designed to write only to
`Mpikambana:Bot-Jagwar/<article-title>` on `mg.wikipedia.org`. Mainspace writes,
page moves, account changes and Wikidata edits are out of scope and must be
treated as security bugs if a code path enables them.

## What is not a vulnerability

- The lack of a bundled license on third-party style references (their own
  attribution and share-alike notices apply; see [`NOTICE`](NOTICE)).
- Rate limiting, cooldowns, intentional refusal to retry uncertain saves, or
  refusal to access external links.
- The documented limitation that agents can run local scripts with ordinary shell
  tools when the operator grants those permissions.
