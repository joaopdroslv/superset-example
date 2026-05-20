# seed/

Standalone synthetic-data seeder. Drop this directory into any project that
needs reproducible test data in a relational DB.

- **SQLAlchemy 2.x** for the ORM
- **Faker** for synthetic content
- **PyYAML** for every tunable (`config.yml`)
- **Docker** for execution — no host Python venv required
- **Reproducible**: same `random_seed` → identical dataset

The default schema is a small e-commerce / marketplace shape (customers,
sellers, products, categories with hierarchy, orders, order_items) designed
to give a BI tool like Apache Superset enough variety to be interesting:
geographic spread, payment-method mix, channel attribution, demographics,
and seller economics (1P vs 3P, commission).

## Layout

```
seed/
├── README.md
├── .env / .env.example       standalone-mode env (optional; falls back to parent .env)
├── .dockerignore
├── pyproject.toml            makes `pip install -e seed/` work
├── requirements.txt          equivalent dep list for non-install workflows
├── config.yml                tunable knobs (counts, weights, probabilities)
├── config.py                 YAML loader → typed CONFIG dataclass
├── __init__.py
├── db.py                     SQLAlchemy engine + SessionLocal factory
├── init.py                   `python -m seed.init` — create the tables only
├── docker/
│   ├── Dockerfile            python:3.11-slim + requirements.txt
│   └── docker-compose.yml    one-off `seed` service
├── scripts/
│   └── run.sh                entry point (Docker-based)
├── models/                   SQLAlchemy 2.x ORM models
│   ├── base.py               DeclarativeBase + TimestampMixin
│   ├── customer.py
│   ├── seller.py
│   ├── category.py
│   ├── product.py
│   └── order.py              Order + OrderItem
├── enums/                    controlled vocabularies referenced by the models
│   ├── customer.py           Gender, CustomerSegment, AcquisitionChannel
│   ├── seller.py             SellerType
│   └── order.py              SalesChannel, OrderStatus, PaymentMethod, Currency
└── core/                     per-table seeders + orchestrator + validator
    ├── factories.py          shared Faker, seeded RNG, geo + catalog ref data
    ├── categories.py
    ├── sellers.py
    ├── products.py
    ├── customers.py
    ├── orders.py             also seeds order_items + computes totals
    ├── run.py                `python -m seed.core.run` — orchestrator
    └── validate.py           `python -m seed.core.validate` — integrity / coverage / reliability checks
```

## How to run

You just cloned the repo. Run these (from the project root):

1. **Make sure the target MySQL is up.** The simplest path is to bring up the
   parent project's Superset stack — it also starts the shared test MySQL:

   ```bash
   ./superset/scripts/run.sh
   ```

   The seeder reads `MYSQL_USER` / `MYSQL_PASSWORD` / `MYSQL_DATABASE` /
   `MYSQL_PORT` from the project-root `.env` (filled in during Superset's
   setup). If you dropped `seed/` into a different project, point those
   variables at your MySQL instead — see [Env discovery](#env-discovery).

2. **Seed the data:**

   ```bash
   ./seed/scripts/run.sh
   ```

   First run builds the seeder image (~30 s) and seeds in ~25 s. Subsequent
   runs reuse the image. Default volumes: ~22 categories, 20 sellers, 200
   products, 500 customers, 2 000 orders, ~6 000 order items.

   The command is *additive* — it skips tables that already have rows. To
   start from scratch, use `--reset` (drops every table, then reseeds).

3. *(optional)* **Sanity-check the result:**

   ```bash
   ./seed/scripts/run.sh validate
   ```

   Runs 46 checks across integrity, reliability, and coverage. Exit code 0
   if no FAILs (WARNs allowed — they're coverage gaps, not bugs).

4. *(optional)* **Regenerate with a different shape:** edit `seed/config.yml`
   (bump `random_seed`, tweak counts / weights / probabilities), then:

   ```bash
   ./seed/scripts/run.sh --reset
   ```

## Usage

Two modes — pick one.

### Containerized (default — no host Python)

```bash
./seed/scripts/run.sh                  # additive seed; skips populated tables
./seed/scripts/run.sh --reset          # drop schema + reseed (DESTRUCTIVE)
./seed/scripts/run.sh init             # only create the tables
./seed/scripts/run.sh validate         # integrity + coverage + reliability report
./seed/scripts/run.sh shell            # bash inside the container
./seed/scripts/run.sh build            # rebuild the seeder image
./seed/scripts/run.sh <compose-cmd>    # forwarded to docker compose
```

The container reaches MySQL through `host.docker.internal:${MYSQL_PORT}` —
i.e. the host-exposed port (default 3307, set by `MYSQL_PORT` in the project-
root `.env`). Override with `SEED_DB_HOST` / `SEED_DB_PORT`, or replace the
URL entirely with `SEED_DATABASE_URL`.

This intentionally avoids joining the Superset stack's Docker network so the
package stays portable — drop it into another project with a MySQL on a host
port and it Just Works.

### Host Python (alternate — useful for IDE debugging)

```bash
python -m venv .venv
. .venv/Scripts/activate               # PowerShell: .venv\Scripts\Activate.ps1
pip install -e seed/                   # or: pip install -r seed/requirements.txt

python -m seed.init                    # or: seed-init       (console script)
python -m seed.core.run                # or: seed-run
python -m seed.core.run --reset
python -m seed.core.validate           # or: seed-validate
```

## Pipeline

The orchestrator (`seed.core.run`) runs seeders in FK-safe order:

```
categories → sellers → products → customers → orders + order_items
```

Each step commits its own rows; the next step issues fresh `SELECT` queries
to fetch the FKs it needs. Seeders never pass objects between each other —
each is independently runnable.

Key design choice — **snapshots on `OrderItem`**: `seller_id`, `unit_price`,
and `unit_cost` are captured at sale time. Historic margin and seller-
attribution reports stay correct when `Product.price` or `Product.seller_id`
later change. Do **not** rewrite reports to join through `products` for those
values.

## Schema

```
customers ──< orders ──< order_items >── products >── categories (self-referential)
                                  │           │
                                  └──> sellers <──┘
```

Highlights designed for BI:

- **Geographic dims are denormalized**: `customers.{country,state,city}` plus
  `orders.ship_{country,state,city}` (a customer can ship to a different
  address). Country uses ISO 3166-1 alpha-2 (`BR`, `US`, ...).
- **Order totals are decomposed**: `subtotal`, `shipping_cost`, `tax_amount`,
  `discount_amount`, `total` all on `Order` — chart "tax burden by state" or
  "shipping share of revenue" without re-aggregating items.
- **Sellers carry `commission_rate` and `seller_type`**: enables platform-
  revenue (`SUM(unit_price * qty * commission_rate)`) and 1P vs 3P
  comparisons.
- **Categories are self-referential**: `parent_id` → drill-downs.
- **Customer `signup_at`** is distinct from `created_at`: the seeder backdates
  signups to produce cohorts; `created_at` is row-insert time.

## Configuration (`config.yml`)

Every knob lives in `seed/config.yml`. Bump `random_seed` to regenerate the
entire dataset.

Categories of knobs:

- **`random_seed`** — RNG seed shared by Faker and Python's `random`. Same
  seed → identical dataset.
- **`counts`** — rows per table: `sellers`, `products`, `customers`, `orders`.
- **`orders`** — `commit_every`, `items_per_order` range, `tax_rate`, free-
  shipping (threshold + probability), cancellation / refund / line-discount /
  order-discount probabilities.
- **`weights`** — relative probability maps for every random pick: countries,
  customer gender / segment / acquisition channel, sales channel, payment
  method (BR vs international), item quantity distribution. Weights are
  *relative* — the RNG normalizes them. Use `0` to suppress a value entirely.

The loader (`seed/config.py`) parses the YAML into frozen dataclasses and
validates: positive counts, probabilities in `[0,1]`, all weight maps non-
empty with non-negative values, etc. Bad config fails loudly at import.

Point at a different file with `SEED_CONFIG_PATH=/path/to/other.yml` for
"small / huge" presets.

State codes per country, the category tree, and brand pools per subcategory
are *lookup tables* (not knobs) and live in `seed/core/factories.py`.

## Validation

`./seed/scripts/run.sh validate` (or `python -m seed.core.validate`) runs a
suite of checks across three categories:

- **Integrity** — FK referential integrity, uniqueness, every order has line
  items, no self-referential categories.
- **Reliability** — money decomposition (`subtotal + shipping + tax - discount = total`,
  with `0.02` rounding tolerance), positive quantities / prices / costs,
  discount caps, timestamp monotonicity (`placed ≤ paid ≤ shipped ≤
  delivered`), status × timestamp consistency for all six order statuses,
  bounds on commission rate / rating / margin.
- **Coverage** — every enum value appears at least once (`Gender`, `OrderStatus`,
  `PaymentMethod`, ...), every configured country appears in customers and
  shipping addresses, no orphan branches in the category tree, every active
  seller has products. Values *outside* an enum's expected set → FAIL.

Exit code: 0 if no FAILs (WARNs are coverage gaps, not bugs), 1 otherwise —
CI-ready.

## Dropping `seed/` into another project

```bash
cp -r path/to/seed ./seed
cp seed/.env.example seed/.env         # fill in MYSQL_* for the target DB
./seed/scripts/run.sh                  # builds image + seeds
```

Customizing the schema:

1. Replace `seed/models/*.py` with the project's SQLAlchemy models (they must
   share a single `Base` and be importable from `seed.models`).
2. Replace / adjust `seed/enums/*.py` to match the new models.
3. Rewrite the per-table seeders in `seed/core/*.py` for the new schema.
4. Update `seed/config.yml` and `seed/core/factories.py`'s reference data
   (category tree, brand pools, geo) for the new domain.

The orchestrator (`seed.core.run`) and the validator (`seed.core.validate`)
are domain-agnostic — they just call into the model registry and don't need
to change. The validator's checks *do* reference specific models / enums, so
you'll need to update its body or trim it.

## Env discovery

`seed/db.py` looks for a `.env` file in this order:

1. `SEED_ENV_FILE` (explicit override path)
2. `seed/.env` (standalone-mode env, sibling to the package)
3. Nearest `.env` walking up from `seed/` to the filesystem root

Process env vars always win — the `.env` file only fills in *missing* keys
(`load_dotenv(..., override=False)`). This lets the package piggy-back on a
parent project's `.env` (as in this repo, where root `.env` holds `MYSQL_*`)
*or* read its own `seed/.env` when dropped into a project without one.

## Connection variables

The seeder builds the DB URL from `MYSQL_USER`, `MYSQL_PASSWORD`,
`MYSQL_DATABASE`, plus host/port (default `127.0.0.1:${MYSQL_PORT}` in host-
Python mode; `host.docker.internal:${MYSQL_PORT}` in container mode).

Overrides, in order of precedence:

- `SEED_DATABASE_URL` — full SQLAlchemy URL, bypasses everything else.
- `SEED_DB_HOST` / `SEED_DB_PORT` — replace just the host or port.
- `MYSQL_*` — the defaults pulled from `.env`.
