# CLAUDE.md

Project context for Claude Code sessions on this repo.

A minimalist, "production-shaped" Apache Superset deployment running entirely in
Docker Compose, with an optional sandbox MySQL datasource and a standalone
synthetic-data seeder. This file is an **index** — the detail lives under
[`docs/`](docs/), split into *reference* (what the project is) and *standards*
(rules to follow when editing).

## Reference — what the project is & how it's structured

- [docs/reference/overview.md](docs/reference/overview.md) — what this is + the
  full container stack (images, roles, ports).
- [docs/reference/layout.md](docs/reference/layout.md) — annotated directory
  tree of the whole repo.
- [docs/reference/usage.md](docs/reference/usage.md) — running the Superset
  stack and the seeder via their `run.sh` scripts, plus connecting Superset to
  the test MySQL.
- [docs/reference/seeder.md](docs/reference/seeder.md) — the `seed/` package:
  schema / entity map, design choices, execution modes, config, and how to
  drop it into another project.

## Standards — conventions & rules to follow when editing

- [docs/standards/path-conventions.md](docs/standards/path-conventions.md) —
  how the three Compose files and two `.env` scopes resolve paths and variables.
- [docs/standards/configuration.md](docs/standards/configuration.md) — the
  config touchpoints (`superset_config.py`, compose anchors,
  `requirements-local.txt`, env files) and the patterns to preserve.
- [docs/standards/common-edits.md](docs/standards/common-edits.md) — recipes
  for routine changes (version bump, new driver, secret rotation, first boot).
- [docs/standards/gotchas.md](docs/standards/gotchas.md) — traps to avoid
  (container hostnames, `nuke` data loss, YAML merge keys, line endings, CSRF
  exempt list, `OrderItem` snapshot rule).
