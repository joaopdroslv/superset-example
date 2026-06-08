# Path conventions (important when editing Compose)

Three compose files now live at different depths:

| File                                | env_file        | mount sources                                   |
| ----------------------------------- | --------------- | ----------------------------------------------- |
| `superset/docker/docker-compose.yml`| `../.env`       | `../superset_config.py`, `../requirements-local.txt` |
| `docker/docker-compose.tests.yml`   | `../.env`       | (no host mounts — uses named volume only)       |
| `seed/docker/docker-compose.yml`    | `../../.env`    | `..` (the `seed/` package) → `/workspace/seed:ro` |

Two env files at different scopes:

- **`.env`** at the project root → shared infra (`MYSQL_*`). Read by
  `docker/docker-compose.tests.yml`, by the seeder (`SEED_DB_PORT` derives
  from `MYSQL_PORT`), and by both scripts via `--env-file .env`.
- **`superset/.env`** → Superset-only secrets (`SUPERSET_*`, `ADMIN_*`,
  `POSTGRES_*`). Read by `superset/docker/docker-compose.yml`'s
  `env_file: ../.env` and by `superset/scripts/run.sh` via a second
  `--env-file superset/.env` flag (Compose merges multiple env files).

Every script does `cd "$(dirname "$0")/../.."` to land at the project root
before invoking docker compose.

Paths inside each compose file are resolved **relative to that file's
directory**. `${VAR}` interpolation reads from `--env-file .env` (always the
project-root `.env`, because the scripts force cwd there).

The seeder compose intentionally does NOT join the Superset stack's network —
it talks to MySQL via `host.docker.internal:${MYSQL_PORT}`. This keeps the
seeder package portable: dropping `seed/` into another project doesn't require
knowing that project's compose network name.

- `${VAR}` interpolation reads from `--env-file .env` (resolved relative to the
  caller's cwd, which the script forces to the project root).

When the `tests.yml` override is merged in, Compose merges service mappings.
The `depends_on` block under `superset` in `tests.yml` adds `mysql-test` to the
existing dependency list — it does **not** replace it.
