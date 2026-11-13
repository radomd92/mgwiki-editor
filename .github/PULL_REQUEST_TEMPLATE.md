## Summary

<!-- What changes, and why? Link related issues. -->

## Scope

- [ ] Code / CLI
- [ ] Agent prompts, skills or policy docs
- [ ] Tests or fixtures only
- [ ] Documentation

## Checks

- [ ] `python3 -m pytest` passes offline
- [ ] `ruff check mgwiki_editor tests` passes
- [ ] `ruff format --check mgwiki_editor tests` passes
- [ ] No credentials, `runs/` job data, generated artifacts or copied external
      resources are included
- [ ] Editorial, pacing, cooldown, uncertain-save, account and sandbox guards are
      unchanged or the change is explained below
- [ ] Adapted style references keep their attribution and license notices

## Safety notes

<!-- Any manual smoke test, live-wiki check, or limit reviewers should know about.
     Development and tests must never publish a Wikipedia edit. -->
