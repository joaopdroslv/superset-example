# superset-example

Local sandbox for learning Apache Superset, with a reproducible synthetic-data
pipeline. Everything runs in Docker — no host Python required beyond Docker
Desktop.

The repository is split into two self-contained domains plus a shared piece of
infrastructure:

- **[`superset/`](superset/README.md)** — Apache Superset 4.1 stack: web app,
  Celery worker + beat, Postgres metadata DB, Redis cache + broker. Brought up
  via `./superset/scripts/run.sh`.
- **[`seed/`](seed/README.md)** — standalone seeder that populates a test
  MySQL with a realistic e-commerce / marketplace dataset (11 tables, ~500
  customers, 200 products, 2 000 orders, 6 000 line items, 1 280 addresses,
  4 700 shipments, 24 000 tracking events). SQLAlchemy 2.x + Faker,
  YAML-configurable, runs in its own Docker container — no host venv needed.
- **`docker/docker-compose.tests.yml`** — the shared test MySQL. Used as a
  Superset datasource *and* as the seeder's target.

## Quick start

```bash
# 1. Copy env templates and edit the placeholders
cp .env.example .env
cp superset/.env.example superset/.env
# (edit both — replace every `change-me-...` value)

# 2. Bring up Superset + test MySQL
./superset/scripts/run.sh
# → http://localhost:8088  (login: admin / your ADMIN_PASSWORD)

# 3. Populate the test MySQL with synthetic data
./seed/scripts/run.sh

# 4. (optional) sanity-check the seed
./seed/scripts/run.sh validate

# 5. In Superset → Settings → Database Connections → +, paste:
#    mysql+pymysql://tester:<MYSQL_PASSWORD>@mysql-test:3306/testdb
```

## Layout

```
.
├── .env / .env.example       shared infra config (MYSQL_*)
├── superset/                 Superset stack — see superset/README.md
├── seed/                     synthetic-data seeder — see seed/README.md
├── docker/
│   └── docker-compose.tests.yml   shared test MySQL
└── CLAUDE.md                 context file for Claude Code sessions
```

Each domain is *self-contained*: its own `docker/`, `scripts/`, and (where
relevant) `.env` template. You can copy `superset/` or `seed/` into another
project without dragging the rest of the repo along.

## Requirements

- Docker Desktop (Linux / macOS / Windows)
- Bash for the helper scripts (Git Bash works on Windows)

## Where to go next

- **Running Superset**, configuring data sources, bumping the version → [`superset/README.md`](superset/README.md)
- **Tuning the seeder**, dropping it into another project, validation suite → [`seed/README.md`](seed/README.md)
- **Developer context** (path conventions, design decisions, gotchas) → [`CLAUDE.md`](CLAUDE.md)
