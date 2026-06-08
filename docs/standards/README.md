# Project Standards

Each file in this folder is a focused, independently-editable rule-set imported by [`CLAUDE.md`](../../CLAUDE.md) via Claude Code's `@`-syntax. The rules become part of every conversation automatically.

## Files

| File | Scope |
|------|-------|
| [`path-conventions.md`](./path-conventions.md) | How the three Compose files and two `.env` scopes resolve paths and `${VAR}` interpolation. |
| [`configuration.md`](./configuration.md) | Config touchpoints (`superset_config.py`, compose anchors, `requirements-local.txt`, env files) and the patterns to preserve. |
| [`common-edits.md`](./common-edits.md) | Recipes for routine changes — version bump, new DB driver, secret-key rotation, first-boot behavior. |
| [`gotchas.md`](./gotchas.md) | Traps to avoid — container hostnames, `nuke` data loss, YAML merge keys, line endings, CSRF exempt list, `OrderItem` snapshot rule. |

## Adding a new standard

1. Create `docs/standards/<topic>.md` with the rule.
2. Add an `@docs/standards/<topic>.md` import to `CLAUDE.md` under a matching heading.
3. Log it as a decision record (`/log-decision`).

Keep each file narrow and focused. If a file starts to mix concerns, split it.
