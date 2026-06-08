# Seeder (`seed/`)

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

## Schema

Schema (`seed/models/`) — an e-commerce / marketplace shape designed to
unlock a wide range of BI questions: geographic (country/state/city on both
customers and per-order shipping address), payment mix (method, installments,
currency), channel attribution (sales channel + customer acquisition channel),
demographics (gender, age via birth_date), and seller economics (1P vs 3P,
commission, rating).

Entity map:
```
                       ┌──> shipping_zones <──┐
                       │                       │
customers ──< addresses ──┐               ┌── addresses >── sellers
    │                     │               │                  │
    └─< orders ──< order_items >── products >── categories (self-referential)
            │           │                          │
            │           └─────> sellers <──────────┘
            │
            └─< shipments ──> shipping_carriers
                    │
                    ├──> origin addresses
                    ├──> dest   addresses
                    └─< shipment_events
```

### Key design choices that affect query patterns

> These shape how reports should be written. The snapshot rule in particular
> is a hard constraint — see [standards/gotchas.md](../standards/gotchas.md).

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
- **Addresses are normalized** (own table, XOR-owned by customer or seller via
  DB CheckConstraint) — but the `Order.ship_{country,state,city}` snapshot
  stays so existing geo reports keep working without joins.
- **Shipments + tracking events** sit between orders and addresses.
  `Shipment.{origin,dest}_address_id` reference real address rows; events
  trail the lifecycle (`created → picked_up → in_transit → out_for_delivery →
  delivered`). After the shipments seeder runs, `Order.shipping_cost` is
  reconciled to `SUM(shipments.shipping_cost)` (and `Order.total`
  recomputed). One order can have multiple shipments — `split-shipping rate`
  is a config knob (default 80%).
- **Shipping zones** (BR macro-regions Sudeste/Sul/Nordeste/Norte/Centro-Oeste
  + INTL) group states for tariff analytics. Same-zone shipments are cheaper;
  cross-zone shipments pay a penalty per the `factories.compute_shipping_cost`
  formula (base + weight×factor + cross-zone penalty).
- **`Shipment.estimated_delivery_at`** is set so the on-time rate
  (`delivered_at <= estimated_delivery_at`) matches
  `config.shipments.on_time_delivery_rate` — late shipments get an estimate
  before their actual delivery, on-time shipments get one after.
- `Base` and `TimestampMixin` live in `models/base.py`; the mixin adds
  `created_at` / `updated_at` managed by MySQL `NOW()` / `ON UPDATE`.
- **Controlled vocabularies live in `seed/enums/`**, not on the columns. The DB
  columns are plain `String(...)` (no MySQL ENUM constraint) for flexibility,
  but the enum classes (`Gender`, `OrderStatus`, `PaymentMethod`, ...) are the
  source of truth. Model `default=` values reference enum members, and the
  seeder should pick random values from the enums — never hard-code the
  strings inline.

## Execution modes

### Containerized (default — no host Python required)

```bash
# bring up MySQL via the Superset stack first:
./superset/scripts/run.sh

# populate everything (creates tables if missing, then seeds):
./seed/scripts/run.sh              # additive; skips populated tables
./seed/scripts/run.sh --reset      # wipe schema + reseed (DESTRUCTIVE)
./seed/scripts/run.sh init         # only create the tables
```

### Host Python (alternative — useful for editing & debugging in your IDE)

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

## Configuration

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
above). Override the host/port with `SEED_DB_HOST` / `SEED_DB_PORT`, or
replace the URL entirely with `SEED_DATABASE_URL`, when running from inside a
container on the same network as the DB.

## Dropping `seed/` into another project

Copy the directory, replace `seed/models/` and `seed/enums/` to match the
target schema, rewrite the `*_TREE` / `BRANDS_BY_SUBCATEGORY` reference data in
`seed/core/factories.py`, edit `seed/config.yml`. The orchestrator in
`seed/core/run.py` stays the same — only the per-table seeders need rewriting
to match the new schema.
