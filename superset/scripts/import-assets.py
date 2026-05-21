"""Import the curated asset bundle into Superset.

Two steps:
  1. Read every YAML under /app/assets/, substitute env vars (e.g.
     $MYSQL_PASSWORD) with `os.path.expandvars`, normalize datasets so every
     column / metric has the canonical null defaults Superset's Marshmallow
     schema requires, then call ImportDatabasesCommand + ImportDatasetsCommand
     directly so we surface field-level validation errors.
  2. Read every `.sql` file under /app/assets/queries/, parse its `-- label:`
     and `-- description:` headers, and upsert a SavedQuery row via Superset's
     Python SDK.

Idempotent: imports run with overwrite=True; saved queries upsert by
(database, label). Meant to be called from `superset-init`.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

ASSETS_DIR = Path("/app/assets")
QUERIES_DIR = ASSETS_DIR / "queries"


# ---------------------------------------------------------------------------
# YAML normalization
# ---------------------------------------------------------------------------
# Superset's import schema requires every key on a Column / Metric entry, even
# if null. Authoring datasets with all those nulls inline is noisy, so the
# user-authored YAMLs stay compact and we fill in the canonical defaults here.

_COLUMN_DEFAULTS: dict = {
    "verbose_name": None,
    "is_dttm": False,
    "is_active": True,
    "type": None,
    "advanced_data_type": None,
    "groupby": True,
    "filterable": True,
    "expression": None,
    "description": None,
    "python_date_format": None,
    "extra": None,
}

_METRIC_DEFAULTS: dict = {
    "verbose_name": None,
    "metric_type": None,
    "description": None,
    "d3format": None,
    "currency": None,
    "extra": None,
    "warning_text": None,
}


def _normalize_dataset(data: dict) -> dict:
    for col in data.get("columns") or []:
        for k, v in _COLUMN_DEFAULTS.items():
            col.setdefault(k, v)
    for m in data.get("metrics") or []:
        for k, v in _METRIC_DEFAULTS.items():
            m.setdefault(k, v)
    return data


def load_bundle_contents() -> dict[str, str]:
    """Return `{relative_path: yaml_text}` for every asset, post-substitution
    and post-normalization.

    metadata.yaml is INTENTIONALLY excluded — its `type:` field is per-command
    (Database / SqlaTable / ...) and we inject it dynamically in each call to
    the matching dispatcher.
    """
    contents: dict[str, str] = {}
    for path in sorted(ASSETS_DIR.rglob("*.yaml")):
        rel = path.relative_to(ASSETS_DIR).as_posix()
        if rel == "metadata.yaml":
            continue
        text = os.path.expandvars(path.read_text(encoding="utf-8"))
        if rel.startswith("datasets/"):
            data = yaml.safe_load(text)
            data = _normalize_dataset(data)
            text = yaml.safe_dump(data, default_flow_style=False, sort_keys=False)
        contents[rel] = text
    return contents


def _metadata(asset_type: str) -> str:
    """Per-command metadata.yaml. `type` gates which dispatcher accepts the bundle."""
    return f"version: 1.0.0\ntype: {asset_type}\n"


# ---------------------------------------------------------------------------
# Step 1 — database + datasets via Superset's internal SDK
# ---------------------------------------------------------------------------


def _run_with_error_detail(label: str, command) -> None:
    """Run an ImporterCommand and, on validation failure, log every per-field
    sub-exception so we know exactly which YAML key is wrong.
    """
    from superset.commands.exceptions import CommandInvalidError

    try:
        command.run()
        logger.info("  %s: imported", label)
    except CommandInvalidError as e:
        sub_exceptions = getattr(e, "_exceptions", None) or []
        logger.error("  %s: validation failed (%d sub-exception(s)):", label, len(sub_exceptions))
        for sub in sub_exceptions:
            logger.error("    - %s", sub)
        raise


def import_database_and_datasets() -> None:
    from flask import g
    from superset import security_manager
    from superset.commands.database.importers.dispatcher import (
        ImportDatabasesCommand,
    )
    from superset.commands.dataset.importers.dispatcher import (
        ImportDatasetsCommand,
    )

    # Superset's import commands do permission checks via `g.user`, which is
    # only auto-populated by the HTTP middleware. Since we're outside a
    # request, push the admin user into Flask's request-context globals.
    admin_username = os.environ.get("ADMIN_USERNAME", "admin")
    admin = security_manager.find_user(admin_username)
    if admin is None:
        raise RuntimeError(f"admin user {admin_username!r} not found in metadata DB")
    g.user = admin

    contents = load_bundle_contents()
    logger.info("loaded %d asset YAML file(s) (as user %s)", len(contents), admin.username)

    db_contents = {"metadata.yaml": _metadata("Database"), **contents}
    _run_with_error_detail("databases", ImportDatabasesCommand(db_contents, overwrite=True))

    ds_contents = {"metadata.yaml": _metadata("SqlaTable"), **contents}
    _run_with_error_detail("datasets", ImportDatasetsCommand(ds_contents, overwrite=True))


# ---------------------------------------------------------------------------
# Step 2 — saved queries via Superset's Python SDK
# ---------------------------------------------------------------------------


def _parse_sql_header(text: str) -> tuple[str, Optional[str], str]:
    label: Optional[str] = None
    description: Optional[str] = None
    body_lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("-- label:"):
            label = stripped[len("-- label:") :].strip()
        elif stripped.startswith("-- description:"):
            description = stripped[len("-- description:") :].strip()
        else:
            body_lines.append(line)
    if label is None:
        raise ValueError("missing `-- label:` header")
    return label, description, "\n".join(body_lines).strip() + "\n"


def import_saved_queries() -> None:
    from superset import db
    from superset.models.core import Database
    from superset.models.sql_lab import SavedQuery

    if not QUERIES_DIR.exists():
        logger.info("no queries/ directory at %s; skipping", QUERIES_DIR)
        return

    target_db_name = "Test MySQL"
    database = (
        db.session.query(Database).filter_by(database_name=target_db_name).first()
    )
    if database is None:
        logger.error(
            "database %r not found — skipping queries", target_db_name,
        )
        return

    schema = os.environ.get("MYSQL_DATABASE", "testdb")
    sql_files = sorted(QUERIES_DIR.glob("*.sql"))
    if not sql_files:
        logger.info("no .sql files under %s; skipping", QUERIES_DIR)
        return

    n_created = 0
    n_updated = 0
    for sql_file in sql_files:
        label, description, body = _parse_sql_header(
            sql_file.read_text(encoding="utf-8")
        )
        existing = (
            db.session.query(SavedQuery)
            .filter_by(db_id=database.id, label=label)
            .first()
        )
        if existing is None:
            db.session.add(
                SavedQuery(
                    db_id=database.id,
                    schema=schema,
                    label=label,
                    description=description,
                    sql=body,
                )
            )
            n_created += 1
        else:
            existing.sql = body
            existing.description = description
            existing.schema = schema
            n_updated += 1

    db.session.commit()
    logger.info(
        "saved queries: %d created, %d updated (total %d)",
        n_created,
        n_updated,
        len(sql_files),
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    from superset.app import create_app

    app = create_app()
    with app.app_context():
        logger.info("[1/2] importing database + datasets")
        import_database_and_datasets()
        logger.info("[2/2] importing saved queries")
        import_saved_queries()

    logger.info("all assets imported.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("asset import failed")
        sys.exit(1)
