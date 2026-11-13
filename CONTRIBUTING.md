# Contributing to mgwiki-editor

Thanks for your interest. This project is a pre-1.0 harness for checked Malagasy
Wikipedia sandbox translations. Contributions are welcome, but the safety and
editorial guards are part of the product, not incidental code.

## Before you start

- Read [`AGENTS.md`](AGENTS.md) for the project policy that binds every agent
  role.
- Read [`docs/usage.md`](docs/usage.md) for setup and the guarded workflow.
- For changes to agent behavior or prompts, also read
  [`docs/edition-protocol.md`](docs/edition-protocol.md),
  [`docs/token-efficient-workflow.md`](docs/token-efficient-workflow.md) and
  [`docs/policy-enforcement.md`](docs/policy-enforcement.md).

## Development setup

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[test]'
```

## Checks

Run all three before opening a pull request:

```bash
python3 -m pytest
ruff check mgwiki_editor tests
ruff format --check mgwiki_editor tests
```

Tests must stay offline. Use fakes for Wikipedia, dictionary and broker
boundaries; never add a test that logs in, edits a wiki page, downloads packages
or fetches external links. If a change genuinely needs live verification, describe
the manual smoke test in the pull request instead of automating it.

## What not to commit

- `runs/` job data, credentials, cookies, `user-config.py`, `user-password.py`,
  `.env` files or Pywikibot state
- generated build/test artifacts such as `build/`, `__pycache__/`, `.coverage`,
  `.pytest_cache/` and `.ruff_cache/`
- copied Wikipedia images or other non-free external resources

`runs/` is intentionally ignored. If a bug needs a reproduction, reduce it to a
small synthetic fixture under `tests/`.

## Scope of changes

- Keep mainspace, page-move, account and Wikidata writes out of scope.
- Preserve the fixed destination, account, digest and revision guards.
- Do not weaken request pacing, cooldown, uncertain-save or secret-handling rules.
- Keep Malagasy article output separate from developer-facing Markdown/plain text.
- Keep adapted style references attributed; do not remove license or revision
  notices.
- Prefer small, focused commits with a clear reason. Conventional Commit subjects
  are welcome but not required.

## Reporting issues

Use the [issue tracker](https://github.com/radomd92/mgwiki-editor/issues) for
bugs and feature requests. Redact credentials, cookies, tokens, private paths and
article text that should not be public. For vulnerabilities, follow
[`SECURITY.md`](SECURITY.md) instead of opening a public issue.
