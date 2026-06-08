# Repository Layout

```
.
├── CLAUDE.md                         # index / entry point for Claude Code sessions
├── docs/                             # split documentation (this directory)
│   ├── reference/                    # what the project is & how it's structured
│   └── standards/                    # conventions & rules to follow when editing
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
├── seed/                             # standalone seeder package (see reference/seeder.md)
│   ├── pyproject.toml                # makes `pip install -e seed/` work
│   ├── requirements.txt              # equivalent dep list for non-install workflows
│   ├── .env.example                  # optional standalone-mode env template
│   ├── config.yml                    # tunable knobs (counts, weights, probabilities)
│   ├── config.py                     # YAML loader → typed `CONFIG` dataclass
│   ├── __init__.py
│   ├── db.py                         # engine + SessionLocal factory, env auto-discovery
│   ├── init.py                       # `python -m seed.init` — table creation only
│   ├── enums/                        # controlled vocabularies (one .py per model cluster)
│   │   ├── __init__.py
│   │   ├── customer.py               # Gender, CustomerSegment, AcquisitionChannel
│   │   ├── seller.py                 # SellerType
│   │   ├── order.py                  # SalesChannel, OrderStatus, PaymentMethod, Currency
│   │   └── shipping.py               # ShippingStatus, ServiceLevel, ShipmentEventType
│   ├── core/                         # per-table seeders + master orchestrator
│   │   ├── __init__.py
│   │   ├── factories.py              # shared Faker, RNG, geo + catalog + carrier ref data
│   │   ├── categories.py
│   │   ├── shipping.py               # shipping_carriers + shipping_zones (dims)
│   │   ├── sellers.py
│   │   ├── products.py
│   │   ├── customers.py
│   │   ├── addresses.py              # one default per customer/seller + extras
│   │   ├── orders.py                 # also seeds order_items + computes order totals
│   │   ├── shipments.py              # shipments + events; reconciles order.shipping_cost
│   │   ├── validate.py               # `python -m seed.core.validate` — integrity / coverage / reliability
│   │   └── run.py                    # `python -m seed.core.run` — orchestrator
│   ├── models/                       # SQLAlchemy 2.x ORM models
│   │   ├── __init__.py
│   │   ├── base.py                   # DeclarativeBase + TimestampMixin
│   │   ├── customer.py
│   │   ├── seller.py
│   │   ├── category.py
│   │   ├── product.py
│   │   ├── order.py                  # Order + OrderItem
│   │   ├── address.py                # XOR-owned by customer or seller (DB CheckConstraint)
│   │   ├── shipping.py               # ShippingCarrier + ShippingZone (dim tables)
│   │   └── shipment.py               # Shipment + ShipmentEvent (fact tables)
│   ├── docker/                       # containerized seeder runtime
│   │   ├── Dockerfile                # python:3.11-slim + requirements.txt
│   │   └── docker-compose.yml        # one-off `seed` service, reaches MySQL via host.docker.internal
│   └── scripts/
│       └── run.sh                    # entry point for the seeder (Docker-based)
```
