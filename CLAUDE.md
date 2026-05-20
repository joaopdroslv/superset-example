# CLAUDE.md

Project context for Claude Code sessions on this repo.

## What this is

A minimalist, "production-shaped" Apache Superset deployment running entirely in
Docker Compose. Built for learning and local exploration — *not* a real prod
deployment (Superset officially recommends Kubernetes for prod), but every
choice here mirrors what a small prod setup would look like: Postgres metadata
DB, Redis cache + Celery broker, separate worker / beat / app containers,
healthchecks, secrets via `.env`, Talisman + CSRF on.

A second, optional Compose file spins up a sandbox **MySQL 8** instance so the
user has something to connect Superset *to* (datasource), in addition to its
metadata DB.

## Stack

| Piece                | Image / version           | Role                                                          |
| -------------------- | ------------------------- | ------------------------------------------------------------- |
| `superset`           | `apache/superset:4.1.1`   | Gunicorn web app on port 8088                                 |
| `superset-worker`    | same                      | Celery worker (async SQL Lab, alerts & reports)               |
| `superset-worker-beat` | same                    | Celery beat scheduler                                         |
| `superset-init`      | same                      | One-shot: migrations + admin user + (optional) demo dashboards |
| `postgres`           | `postgres:16-alpine`      | Superset metadata DB                                          |
| `redis`              | `redis:7-alpine`          | Cache (DBs 1–4), results backend (DB 5), Celery broker (DB 0) |
| `mysql-test` *(opt)* | `mysql:8.4`               | Sandbox datasource. Only present when tests compose is loaded |

## Layout

```
.
├── CLAUDE.md                         # this file
├── .env                              # SHARED infra secrets — MYSQL_* only — gitignored
├── .env.example                      # template, safe to commit
├── .gitignore
├── .dockerignore
├── superset/                         # self-contained Superset stack
│   ├── .env                          # Superset-specific secrets (SUPERSET_*, ADMIN_*, POSTGRES_*) — gitignored
│   ├── .env.example                  # template, safe to commit
│   ├── superset_config.py            # Python config, mounted at /app/pythonpath/
│   ├── requirements-local.txt        # extra pip packages installed on container boot
│   ├── docker/
│   │   └── docker-compose.yml        # the Superset stack (postgres + redis + app + worker + beat)
│   └── scripts/
│       └── run.sh                    # entry point for the Superset stack
├── docker/
│   └── docker-compose.tests.yml      # shared MySQL sandbox — datasource for Superset AND target for seed
├── seed/                             # standalone seeder package (see "Seeder" section)
│   ├── pyproject.toml                # makes `pip install -e seed/` work
│   ├── requirements.txt              # equivalent dep list for non-install workflows
│   ├── .env.example                  # optional standalone-mode env template
│   ├── config.yml                    # tunable knobs (counts, weights, probabilities)
│   ├── config.py                     # YAML loader → typed `CONFIG` dataclass
│   ├── __init__.py
│   ├── db.py                         # engine + SessionLocal factory, env auto-discovery
│   ├── init.py                       # `python -m seed.init` — table creation only
│   ├── enums/                        # controlled vocabularies (one .py per model)
│   │   ├── __init__.py
│   │   ├── customer.py               # Gender, CustomerSegment, AcquisitionChannel
│   │   ├── seller.py                 # SellerType
│   │   └── order.py                  # SalesChannel, OrderStatus, PaymentMethod, Currency
│   ├── core/                         # per-table seeders + master orchestrator
│   │   ├── __init__.py
│   │   ├── factories.py              # shared Faker, seeded RNG, geo + catalog ref data
│   │   ├── categories.py
│   │   ├── sellers.py
│   │   ├── products.py
│   │   ├── customers.py
│   │   ├── orders.py                 # also seeds order_items + computes totals
│   │   └── run.py                    # `python -m seed.core.run` — orchestrator
│   ├── models/                       # SQLAlchemy 2.x ORM models
│   │   ├── __init__.py
│   │   ├── base.py                   # DeclarativeBase + TimestampMixin
│   │   ├── customer.py
│   │   ├── seller.py
│   │   ├── category.py
│   │   ├── product.py
│   │   └── order.py                  # Order + OrderItem
│   ├── docker/                       # containerized seeder runtime
│   │   ├── Dockerfile                # python:3.11-slim + requirements.txt
│   │   └── docker-compose.yml        # one-off `seed` service, reaches MySQL via host.docker.internal
│   └── scripts/
│       └── run.sh                    # entry point for the seeder (Docker-based)
```

## Usage

Each standalone has its own entry script. Both resolve their own location, so
they can be called from any working directory.

**Superset stack** (`./superset/scripts/run.sh`):

```bash
./superset/scripts/run.sh              # pull images, start the stack, tail init logs
./superset/scripts/run.sh ps           # container status
./superset/scripts/run.sh logs [svc]   # tail logs (default: superset)
./superset/scripts/run.sh shell        # Superset Python REPL inside the app container
./superset/scripts/run.sh down         # stop, keep volumes
./superset/scripts/run.sh nuke         # stop AND drop volumes (data loss; confirms)
./superset/scripts/run.sh <anything>   # forwarded to `docker compose`
```

`NO_TESTS=1` skips `docker-compose.tests.yml` even if it exists. The script
refuses to start if `.env` is missing or still contains any `change-me-...`
placeholder.

**Seeder** (`./seed/scripts/run.sh`) — fully containerized, no host venv:

```bash
./seed/scripts/run.sh                  # seed (additive; skips populated tables)
./seed/scripts/run.sh --reset          # wipe schema + reseed (DESTRUCTIVE)
./seed/scripts/run.sh init             # create the tables only
./seed/scripts/run.sh shell            # interactive bash in the seeder container
./seed/scripts/run.sh build            # rebuild the seeder image
```

The seeder container reaches the test MySQL via `host.docker.internal` on the
host-exposed port (`$MYSQL_PORT`, default 3307), so it doesn't need to share a
Docker network with the Superset stack. Run `./superset/scripts/run.sh` first
to bring up MySQL.

## Path conventions (important when editing Compose)

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

## Configuration touchpoints

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

## Connecting Superset to the test MySQL

After `./scripts/run.sh`, in the Superset UI:

1. **Settings → Database Connections → + Database**
2. Either pick MySQL from the wizard or paste the SQLAlchemy URI directly:
   ```
   mysql+pymysql://${MYSQL_USER}:${MYSQL_PASSWORD}@mysql-test:3306/${MYSQL_DATABASE}
   ```

The hostname is **`mysql-test`** (the Compose service name on the internal
Docker network), *not* `localhost`. From the host machine, use `127.0.0.1` and
`${MYSQL_PORT}` (default `3307`, picked to avoid clashing with any local MySQL
on 3306).

## Seeder (`seed/`)

A **self-contained Python package** at the project root. Designed to be cloned
or copied into any project that needs reproducible synthetic data in a
relational DB — it does not depend on this repo's `src/`, `docker/`, or
`scripts/`. By default it targets the `mysql-test` MySQL exposed at
`127.0.0.1:${MYSQL_PORT}`, but a fully-formed `SEED_DATABASE_URL` overrides
everything.

Installable via `pip install -e seed/` (registers `seed-init` and `seed-run`
console scripts) or runnable without install via `python -m seed.core.run`
from the directory that contains the `seed/` directory.

**Env auto-discovery** (`seed/db.py::_locate_env_file`): looks at
`SEED_ENV_FILE` → `seed/.env` → nearest `.env` walking up. Process env vars
always win — `.env` only fills in missing keys. This lets the package
piggy-back on a parent project's `.env` (this repo's case) *or* read its own
`seed/.env` when dropped into a project that doesn't have one.

Schema (`seed/models/`) — an e-commerce / marketplace shape designed to
unlock a wide range of BI questions: geographic (country/state/city on both
customers and per-order shipping address), payment mix (method, installments,
currency), channel attribution (sales channel + customer acquisition channel),
demographics (gender, age via birth_date), and seller economics (1P vs 3P,
commission, rating).

Entity map:
```
customers ──< orders ──< order_items >── products >── categories (self-referential)
                                  │           │
                                  └──> sellers <──┘
```

Key design choices that affect query patterns:

- **Geographic dims are denormalized**: `customers.{country,state,city}` for
  "where do my customers live" and `orders.ship_{country,state,city}` for
  "where do orders ship to" (these can differ — same customer, different
  delivery address). Country uses ISO-3166 alpha-2 ("BR", "US"), state stays
  free-form (60 chars).
- **Order totals are decomposed**: `subtotal`, `shipping_cost`, `tax_amount`,
  `discount_amount`, `total` all live on `Order` so Superset can chart "tax
  burden by state" or "shipping share of revenue" without re-aggregating from
  line items.
- **Snapshots on `OrderItem`**: `unit_price`, `unit_cost`, and `seller_id` are
  captured at sale time. **Do not** rewrite reports to join through
  `products.price` / `products.seller_id` — those reflect *current* values and
  will break historical margin and seller-attribution numbers.
- **Sellers carry their own geography and `commission_rate`**: enables platform-
  revenue reports (`SUM(unit_price * quantity * commission_rate)`) and 1P-vs-3P
  comparisons (`Seller.seller_type`).
- **Categories are self-referential**: `category.parent_id` enables a single-
  level taxonomy (parent → subcategory) for drill-downs in Superset.
- **`Customer.signup_at`** is distinct from `created_at`: the seeder can
  backdate signups to produce cohorts; `created_at` remains row-insert time.
- `Base` and `TimestampMixin` live in `models/base.py`; the mixin adds
  `created_at` / `updated_at` managed by MySQL `NOW()` / `ON UPDATE`.
- **Controlled vocabularies live in `seed/enums/`**, not on the columns. The DB
  columns are plain `String(...)` (no MySQL ENUM constraint) for flexibility,
  but the enum classes (`Gender`, `OrderStatus`, `PaymentMethod`, ...) are the
  source of truth. Model `default=` values reference enum members, and the
  seeder should pick random values from the enums — never hard-code the
  strings inline.

Two execution modes:

**Containerized (default — no host Python required):**

```bash
# bring up MySQL via the Superset stack first:
./superset/scripts/run.sh

# populate everything (creates tables if missing, then seeds):
./seed/scripts/run.sh              # additive; skips populated tables
./seed/scripts/run.sh --reset      # wipe schema + reseed (DESTRUCTIVE)
./seed/scripts/run.sh init         # only create the tables
```

**Host Python (alternative — useful for editing & debugging in your IDE):**

```bash
# from the project root (the directory that contains seed/)
python -m venv .venv
. .venv/Scripts/activate           # PowerShell: .venv\Scripts\Activate.ps1
pip install -e seed/               # or: pip install -r seed/requirements.txt

python -m seed.init                # or: seed-init  (after pip install -e)
python -m seed.core.run            # or: seed-run
python -m seed.core.run --reset
```

The seeder pipeline (`seed/core/`) runs in FK-safe order:
`categories → sellers → products → customers → orders + order_items`.
Each step commits its own rows and the next step issues `SELECT` queries to
fetch the FKs it needs — seeders never pass objects to each other.

Every tunable knob lives in **`seed/config.yml`** — row counts, RNG seed,
geographic / demographic / payment weights, order-lifecycle probabilities,
free-shipping threshold, tax rate, items-per-order range, etc. The seeders
import a typed `CONFIG` object from `seed.config`; no constants live in the
seeder modules. Same `random_seed` → same dataset. Point at a different
preset with `SEED_CONFIG_PATH=/path/to/other.yml python -m seed.core.run`.

Default volumes (per `config.yml`): ~22 categories, 20 sellers, 200 products,
500 customers, 2 000 orders with 1–5 line items each.

DB connection variables (`MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`,
`MYSQL_PORT`) come from the auto-discovered `.env` (see env-discovery order
in the section intro). Override the host/port with `SEED_DB_HOST` /
`SEED_DB_PORT`, or replace the URL entirely with `SEED_DATABASE_URL`, when
running from inside a container on the same network as the DB.

**Dropping `seed/` into another project**: copy the directory, replace
`seed/models/` and `seed/enums/` to match the target schema, rewrite the
`*_TREE` / `BRANDS_BY_SUBCATEGORY` reference data in `seed/core/factories.py`,
edit `seed/config.yml`. The orchestrator in `seed/core/run.py` stays the
same — only the per-table seeders need rewriting to match the new schema.

## Common edits — what to remember

- **Bumping the Superset version**: change the `x-superset-image` anchor at
  the top of `superset/docker/docker-compose.yml`. Then
  `./scripts/run.sh pull && ./scripts/run.sh up -d` — the `superset-init`
  container will run any pending migrations on boot.

- **Adding a new DB driver**: uncomment it in `superset/requirements-local.txt`,
  then `./scripts/run.sh restart superset superset-worker`. The bootstrap
  script re-installs the file on every start, no rebuild needed.

- **Regenerating the secret key**: change `SUPERSET_SECRET_KEY` in `.env`. This
  will invalidate existing user sessions and any encrypted-at-rest secrets in
  the metadata DB (DB connection passwords). For a learning environment that's
  fine; in real prod, Superset has a key-rotation CLI (`superset re-encrypt-secrets`).

- **First boot is slow**: the bootstrap pip-installs `pymysql` + `cryptography`
  on every container start. For real prod this should be baked into a custom
  Dockerfile that `FROM apache/superset:4.1.1` and pre-installs the extras.

## Gotchas

- **Don't use `localhost` from inside containers** to reach other services. Use
  the service names: `postgres`, `redis`, `mysql-test`.

- **`./scripts/run.sh nuke` deletes datasource data too** — `mysql_test_data`
  is one of the named volumes it drops. There is no separate "drop only metadata"
  command; reach for `docker volume rm` directly if you need finer control.

- **YAML merge keys (`<<: *anchor`)** are a YAML 1.1 feature. Docker Compose v2
  supports them, but some linters / IDEs flag them as deprecated. They are
  intentional here — keep them.

- **Windows line endings**: this repo is being developed on Windows. The shell
  script (`scripts/run.sh`) needs LF line endings to run under Git Bash / WSL.
  If git is configured to convert to CRLF, add a `.gitattributes` with
  `*.sh text eol=lf` to prevent that. (Not added yet; flag it if it becomes a
  problem.)

- **The `WTF_CSRF_EXEMPT_LIST`** in `superset_config.py` lists endpoints that
  internal Superset XHRs hit without a CSRF token. If you upgrade Superset and
  routes get renamed, these will silently start 400ing — re-check against the
  official `superset_config.py` reference for the version you're on.
