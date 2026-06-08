# Configuration touchpoints

- **`superset/superset_config.py`** — single source of truth for Superset
  behavior. Reads `SUPERSET_SECRET_KEY`, `POSTGRES_*`, and `REDIS_*` from env.
  Has separate Redis DBs for each cache type (metadata=1, data=2, filter
  state=3, explore form data=4, results backend=5, Celery broker=0). Feature
  flags, Talisman, CSRF, and proxy-fix are configured here.

- **`superset/docker/docker-compose.yml`** — uses YAML anchors
  (`x-superset-image`, `x-superset-env`, `x-superset-volumes`) plus
  `<<: *anchor` merge keys to avoid repetition across the four Superset
  services. Preserve this pattern when adding services — don't expand the
  anchors inline.

- **`superset/requirements-local.txt`** — pip-installed on every container
  boot by the Superset image's `docker-bootstrap.sh`. `pymysql` and
  `cryptography` are enabled by default (needed by `mysql-test`). Other
  drivers are commented.

- **`.env` (root) / `superset/.env`** — split by ownership:
  - Root `.env` holds **shared infra** vars (`MYSQL_*`) consumed by the test-
    MySQL compose and the seeder.
  - `superset/.env` holds **Superset-only** vars (`SUPERSET_*`, `ADMIN_*`,
    `POSTGRES_*`).
  Both have `.env.example` siblings — keep variables in lockstep with the
  template. Real values go in `.env` (gitignored); examples use
  `change-me-...` placeholders.
