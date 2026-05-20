# superset/

Self-contained Apache Superset stack. One command brings up the web app,
Celery workers, Postgres metadata DB, and Redis.

> **Not** a real production deployment — Superset officially recommends
> Kubernetes for prod. The choices here mirror what a small prod setup
> *would* look like (Postgres metadata, Redis cache + Celery broker,
> separate worker / beat / app containers, healthchecks, secrets via
> `.env`, Talisman + CSRF on) — but it's all one host, one compose project.

## Stack

| Service                | Image                     | Role                                                          |
| ---------------------- | ------------------------- | ------------------------------------------------------------- |
| `superset`             | `apache/superset:4.1.1`   | Gunicorn web app on port 8088                                 |
| `superset-worker`      | same                      | Celery worker — async SQL Lab, alerts & reports               |
| `superset-worker-beat` | same                      | Celery beat scheduler                                         |
| `superset-init`        | same                      | One-shot: migrations + admin user + (optional) demo data      |
| `postgres`             | `postgres:16-alpine`      | Superset metadata DB                                          |
| `redis`                | `redis:7-alpine`          | Cache (DBs 1-4), results backend (DB 5), Celery broker (DB 0) |

## Layout

```
superset/
├── README.md
├── .env / .env.example       Superset-specific config (SUPERSET_*, ADMIN_*, POSTGRES_*)
├── superset_config.py        Python config — mounted at /app/pythonpath/
├── requirements-local.txt    extra pip packages installed on container boot
├── docker/
│   └── docker-compose.yml    the stack
└── scripts/
    └── run.sh                entry point
```

Shared infra config (`MYSQL_*` for the test MySQL) lives in the project-root
`.env`, not here. The test MySQL itself lives in
`../docker/docker-compose.tests.yml` because it's used by the seeder too.

## How to run

You just cloned the repo. Run these:

1. **Fill the env files** — they're gitignored, so you start from the templates:

   ```bash
   cp .env.example .env                       # root: shared infra (MYSQL_*)
   cp superset/.env.example superset/.env     # Superset secrets
   ```

   Open both and replace every `change-me-...` value. The script refuses to
   start while any placeholder remains.

2. **Bring up the stack:**

   ```bash
   ./superset/scripts/run.sh
   ```

   First run pulls base images (~2 GB: postgres, redis, mysql, superset) and
   builds the custom `superset-with-drivers` image (bakes in `psycopg2-binary`,
   `pymysql`, `cryptography`). The script then tails `superset-init` —
   migrations + admin-user creation + (if `SUPERSET_LOAD_EXAMPLES=yes`) the
   demo dashboards. Expect 3-5 min extra on first run while examples load.

3. **Open the UI:** <http://localhost:8088>. Log in with the `ADMIN_USERNAME`
   / `ADMIN_PASSWORD` you set in `superset/.env`.

4. *(optional)* **Add the test MySQL as a data source** — Settings → Database
   Connections → +, then paste:

   ```
   mysql+pymysql://tester:<MYSQL_PASSWORD>@mysql-test:3306/testdb
   ```

   The host is `mysql-test` (the Compose service name on the internal Docker
   network), **not** `localhost`. From the host machine (DBeaver, mysql CLI),
   use `127.0.0.1:${MYSQL_PORT}` instead.

If `MYSQL_*` placeholders aren't filled, the test MySQL container will refuse
to start — same gate as Superset.

## Usage

```bash
./superset/scripts/run.sh              # bring up everything, tail init logs
./superset/scripts/run.sh ps           # container status
./superset/scripts/run.sh logs [svc]   # tail logs (default: superset)
./superset/scripts/run.sh shell        # Python REPL inside the app container
./superset/scripts/run.sh down         # stop, keep volumes
./superset/scripts/run.sh nuke         # stop AND drop every volume (data loss)
./superset/scripts/run.sh <anything>   # forwarded to docker compose
```

Env flags:

- `NO_TESTS=1` — skip `docker/docker-compose.tests.yml` (start Superset
  without the test MySQL).

The script refuses to start if `.env` (root) or `superset/.env` is missing,
or if either still contains a `change-me-...` placeholder. Missing files are
auto-copied from the matching `.env.example`.

## Configuration touchpoints

### `superset_config.py`

Single source of truth for app behavior. Reads `SUPERSET_SECRET_KEY`,
`POSTGRES_*`, `REDIS_*` from env at startup. Highlights:

- Separate Redis databases for each cache concern: metadata (DB 1), data (2),
  filter state (3), explore form data (4), results backend (5), Celery broker
  (0). Keeps eviction independent.
- Feature flags enabled: `ALERT_REPORTS`, `EMBEDDED_SUPERSET`, `DASHBOARD_RBAC`,
  `DRILL_TO_DETAIL`, `DRILL_BY`, `HORIZONTAL_FILTER_BAR`.
- `TALISMAN_ENABLED = True`, `WTF_CSRF_ENABLED = True`, `ENABLE_PROXY_FIX = True`
  (ready to sit behind nginx / traefik).
- SQLAlchemy engine options with `pool_pre_ping` to survive idle disconnects.

### `requirements-local.txt`

Pip-installed by the Superset image's `docker-bootstrap.sh` on every container
boot. `pymysql` and `cryptography` are enabled by default (needed to connect
to the test MySQL with MySQL 8.4's `caching_sha2_password` default). Other
drivers — ClickHouse, Snowflake, BigQuery, Trino, Redshift, Athena — are
commented and ready to uncomment.

For production, you'd bake these into a custom Dockerfile that
`FROM apache/superset:4.1.1` and pre-installs them.

### `superset/.env` (and `.env.example`)

Holds every Superset-specific secret: `SUPERSET_SECRET_KEY`, the admin user
fields, `POSTGRES_*`, plus `SUPERSET_PORT` and `SUPERSET_LOAD_EXAMPLES`. The
example file documents each variable; copy it to `.env` and replace the
`change-me-...` placeholders.

Shared infra (`MYSQL_*`) lives in the project-root `.env` instead — both the
test MySQL and the seeder consume it, so it doesn't belong here.

## Connecting data sources

After `./superset/scripts/run.sh`, open <http://localhost:8088> and log in.
Then **Settings → Database Connections → +** and paste a SQLAlchemy URI.

A couple of examples:

```
# The local test MySQL started alongside Superset
mysql+pymysql://tester:<MYSQL_PASSWORD>@mysql-test:3306/testdb

# A Postgres elsewhere on your machine
postgresql+psycopg2://user:pass@host.docker.internal:5432/dbname
```

The hostname `mysql-test` is the compose *service name* — resolved on the
Docker network — not `localhost`. From the host machine (e.g. DBeaver), use
`127.0.0.1:${MYSQL_PORT}`.

## Common edits

- **Bumping the Superset version**: change the `x-superset-image` anchor at
  the top of `docker/docker-compose.yml`, then
  `./superset/scripts/run.sh pull && ./superset/scripts/run.sh up -d`.
  The `superset-init` container runs any pending migrations on boot.
- **Adding a new DB driver**: uncomment in `requirements-local.txt`, then
  `./superset/scripts/run.sh restart superset superset-worker`. The bootstrap
  reinstalls the file on every start.
- **Regenerating the secret key**: change `SUPERSET_SECRET_KEY` in
  `superset/.env`. This invalidates user sessions and any encrypted-at-rest
  secrets (data-source passwords stored in the metadata DB). For real prod
  use the `superset re-encrypt-secrets` CLI.

## Tearing it down

```bash
./superset/scripts/run.sh down    # stops containers, keeps volumes
./superset/scripts/run.sh nuke    # stops AND drops volumes — data loss
```

`nuke` drops every named volume, *including* `mysql_test_data`. The seeder's
data goes with it. If you only want to reset Superset (keep the test MySQL
data), use plain `down` and then `docker volume rm` on the specific Superset
volumes.

## Path conventions

The compose file lives at `superset/docker/docker-compose.yml`. The script
`cd`s to the project root first, then invokes:

```
docker compose --project-directory . \
  -f superset/docker/docker-compose.yml \
  -f docker/docker-compose.tests.yml \
  --env-file .env --env-file superset/.env \
  ...
```

Two `--env-file` flags merge values: project-root `.env` (`MYSQL_*`) plus
`superset/.env` (everything else). Inside the compose file, mounts use paths
relative to the compose file's directory — `../superset_config.py`,
`../requirements-local.txt`, `env_file: ../.env`.
