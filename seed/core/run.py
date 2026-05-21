"""Master orchestrator — runs every seeder in FK-safe order.

Usage (from the directory that contains the `seed/` package, e.g. the repo
root):
    python -m seed.core.run            # additive: skips tables that already have rows
    python -m seed.core.run --reset    # drops and recreates the schema first

After `pip install -e seed/` the `seed-run` console script is equivalent.

Each step commits independently. If anything fails midway, rows committed
before the failure remain — fix the issue, rerun, the populated tables are
skipped.
"""

from __future__ import annotations

import argparse
import logging
import time

from sqlalchemy.orm import Session

from ..db import SessionLocal, engine
from ..models import Base
from . import (
    addresses,
    categories,
    customers,
    orders,
    products,
    sellers,
    shipments,
    shipping,
)

logger = logging.getLogger(__name__)

# Order matters — each entry's FKs reference tables earlier in the list.
SEEDERS = [
    ("categories", categories.seed),
    ("shipping (carriers + zones)", shipping.seed),
    ("sellers", sellers.seed),
    ("products", products.seed),
    ("customers", customers.seed),
    ("addresses", addresses.seed),
    ("orders", orders.seed),
    ("shipments + events", shipments.seed),
]


def run(session: Session) -> None:
    for name, fn in SEEDERS:
        t0 = time.perf_counter()
        logger.info("[%s] starting", name)
        inserted = fn(session)
        logger.info("[%s] done: %d rows in %.2fs", name, inserted, time.perf_counter() - t0)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate every table before seeding (DESTRUCTIVE).",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.reset:
        logger.warning("Dropping all tables...")
        Base.metadata.drop_all(engine)

    logger.info("Ensuring schema exists on %s", engine.url.render_as_string(hide_password=True))
    Base.metadata.create_all(engine)

    with SessionLocal() as session:
        run(session)

    logger.info("All seeders completed.")


if __name__ == "__main__":
    main()
