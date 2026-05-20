"""SQLAlchemy engine and session factory for the seeder.

Reads connection settings from environment variables. By default it targets a
MySQL exposed at 127.0.0.1:${MYSQL_PORT}, so the seeder can run from the host
against a Dockerized DB. To run from inside a container on the same network,
set `SEED_DB_HOST=<service-name>` and `SEED_DB_PORT=3306`.

A fully-formed `SEED_DATABASE_URL` overrides everything else.

The `.env` file is loaded from the first match, in order:
  1. `SEED_ENV_FILE` env var (explicit path)
  2. `<this-package>/.env`                  — standalone-mode env, next to the code
  3. nearest `.env` walking up from `<this-package>` to the filesystem root
Existing process environment variables always win (they're set before the
.env load is even considered).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def _locate_env_file() -> Optional[Path]:
    explicit = os.environ.get("SEED_ENV_FILE")
    if explicit:
        path = Path(explicit).expanduser()
        return path if path.is_file() else None

    pkg_dir = Path(__file__).resolve().parent
    local = pkg_dir / ".env"
    if local.is_file():
        return local

    for parent in pkg_dir.parents:
        candidate = parent / ".env"
        if candidate.is_file():
            return candidate
    return None


_env_file = _locate_env_file()
if _env_file is not None:
    # `override=False` → existing process env vars beat values from the file.
    load_dotenv(_env_file, override=False)


def _build_database_url() -> str:
    override = os.environ.get("SEED_DATABASE_URL")
    if override:
        return override

    user = os.environ["MYSQL_USER"]
    password = os.environ["MYSQL_PASSWORD"]
    database = os.environ["MYSQL_DATABASE"]
    host = os.environ.get("SEED_DB_HOST", "127.0.0.1")
    port = os.environ.get("SEED_DB_PORT", os.environ.get("MYSQL_PORT", "3307"))
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"


DATABASE_URL: str = _build_database_url()

engine: Engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
    expire_on_commit=False,
)


def get_session() -> Session:
    """Return a fresh ORM session. Caller is responsible for closing it.

    Prefer `with SessionLocal() as session:` in new code.
    """
    return SessionLocal()
