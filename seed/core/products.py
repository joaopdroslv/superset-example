"""Seed `products` — distributed across leaf categories and active sellers.

Queries the previously-seeded `categories` and `sellers` tables for valid FKs
instead of receiving objects from another seeder.
"""

from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import CONFIG
from ..models import Category, Product, Seller
from .factories import BRANDS_BY_SUBCATEGORY, fake, money, rng

logger = logging.getLogger(__name__)


def seed(session: Session) -> int:
    if session.scalar(select(Product).limit(1)) is not None:
        logger.info("products: table already populated, skipping")
        return 0

    # Attach products only to leaf (sub)categories — parents are organizational.
    leaf_cats: list[Category] = list(
        session.scalars(
            select(Category).where(Category.parent_id.is_not(None))
        )
    )
    if not leaf_cats:
        raise RuntimeError("No leaf categories found — seed categories first.")

    seller_ids: list[int] = list(
        session.scalars(select(Seller.id).where(Seller.is_active.is_(True)))
    )
    if not seller_ids:
        raise RuntimeError("No active sellers found — seed sellers first.")

    products: list[Product] = []
    for i in range(CONFIG.counts.products):
        category = rng.choice(leaf_cats)
        seller_id = rng.choice(seller_ids)
        brand_pool = BRANDS_BY_SUBCATEGORY.get(category.name, ["Generic"])
        brand = rng.choice(brand_pool)

        price = money(rng.uniform(20, 5000))
        # Cost is 40–70% of price — gives a realistic gross margin band.
        cost = money(price * Decimal(str(round(rng.uniform(0.40, 0.70), 4))))

        products.append(
            Product(
                sku=f"SKU-{i + 1:06d}",
                name=f"{brand} {fake.word().title()} {rng.randint(100, 9999)}",
                description=fake.sentence(nb_words=12),
                brand=brand,
                price=price,
                cost=cost,
                weight_kg=Decimal(str(round(rng.uniform(0.05, 15.0), 3))),
                category_id=category.id,
                seller_id=seller_id,
                is_active=rng.random() > 0.05,
                launched_on=fake.date_between(start_date="-2y", end_date="today"),
            )
        )

    session.add_all(products)
    session.commit()
    return len(products)
