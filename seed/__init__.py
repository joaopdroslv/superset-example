"""Standalone synthetic-data seeder.

Self-contained Python package: drop the `seed/` directory into any project
that has a target MySQL, point `MYSQL_*` env vars (or `seed/.env`) at it,
adjust the ORM models / `config.yml` to match the target schema, and run
`python -m seed.core.run`. Independent from the parent project's source tree.

Public surface:
    from seed import Base, SessionLocal, engine, get_session

Subpackages:
    seed.models     — SQLAlchemy 2.x ORM models registered on `Base.metadata`
    seed.enums      — controlled vocabularies referenced by the models
    seed.core       — per-table seeders + `run.py` orchestrator
"""

from .db import SessionLocal, engine, get_session
from .models import Base

__all__ = ["Base", "SessionLocal", "engine", "get_session"]
