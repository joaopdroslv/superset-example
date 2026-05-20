"""Seed `categories` from the hard-coded `CATEGORY_TREE`.

Parents are inserted first and flushed so their IDs are available before the
child rows reference them via `parent_id`.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Category
from .factories import CATEGORY_TREE, slugify

logger = logging.getLogger(__name__)


def seed(session: Session) -> int:
    if session.scalar(select(Category).limit(1)) is not None:
        logger.info("categories: table already populated, skipping")
        return 0

    inserted = 0
    for parent_name, sub_names in CATEGORY_TREE.items():
        parent = Category(
            name=parent_name,
            slug=slugify(parent_name),
            is_active=True,
        )
        session.add(parent)
        session.flush()  # generates parent.id so children can reference it
        inserted += 1

        for sub_name in sub_names:
            session.add(
                Category(
                    name=sub_name,
                    slug=slugify(sub_name),
                    parent_id=parent.id,
                    is_active=True,
                )
            )
            inserted += 1

    session.commit()
    return inserted
