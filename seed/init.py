"""Create every table declared in `seed.models` on the target database.

Idempotent: SQLAlchemy's `create_all` skips tables that already exist. To
start from a clean slate, drop the schema first (or wipe the underlying
volume).

Run from the directory that contains the `seed/` package, e.g. the repo root:
    python -m seed.init
After `pip install -e seed/` the `seed-init` console script is also available.
"""

from __future__ import annotations

import logging

from .db import engine
from .models import Base

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    url = engine.url.render_as_string(hide_password=True)
    logger.info("Creating tables on %s", url)
    Base.metadata.create_all(engine)
    created = ", ".join(sorted(Base.metadata.tables.keys()))
    logger.info("Done. Tables present: %s", created)


if __name__ == "__main__":
    main()
