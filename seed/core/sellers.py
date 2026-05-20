"""Seed `sellers` — one first-party store + N marketplace vendors."""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import CONFIG
from ..enums.seller import SellerType
from ..models import Seller
from .factories import fake, fake_location, rng, slugify

logger = logging.getLogger(__name__)


def seed(session: Session) -> int:
    if session.scalar(select(Seller).limit(1)) is not None:
        logger.info("sellers: table already populated, skipping")
        return 0

    sellers: list[Seller] = []

    # The first-party "store itself" — zero commission, oldest, always active.
    sellers.append(
        Seller(
            name="Loja Principal",
            slug="loja-principal",
            email="contact@lojaprincipal.example.com",
            country="BR",
            state="SP",
            city="São Paulo",
            postal_code="01310-100",
            seller_type=SellerType.FIRST_PARTY.value,
            commission_rate=Decimal("0.0000"),
            rating=None,
            is_active=True,
            onboarded_on=date(2020, 1, 1),
        )
    )

    seen_slugs: set[str] = {"loja-principal"}
    for _ in range(CONFIG.counts.sellers - 1):
        company = fake.company()
        slug = slugify(company)
        # Disambiguate in the rare case Faker hands us a name we've seen.
        suffix = 1
        unique_slug = slug
        while unique_slug in seen_slugs or not unique_slug:
            suffix += 1
            unique_slug = f"{slug}-{suffix}"
        seen_slugs.add(unique_slug)

        country, state, city, postal_code = fake_location()
        sellers.append(
            Seller(
                name=company,
                slug=unique_slug,
                email=fake.unique.company_email(),
                country=country,
                state=state,
                city=city,
                postal_code=postal_code,
                seller_type=SellerType.MARKETPLACE.value,
                # 8% – 25% take rate, four-decimal precision.
                commission_rate=Decimal(str(round(rng.uniform(0.08, 0.25), 4))),
                # Ratings cluster between 3.5 and 5.0 (realistic marketplace).
                rating=Decimal(str(round(rng.uniform(3.5, 5.0), 2))),
                is_active=rng.random() > 0.05,  # ~5% deactivated sellers
                onboarded_on=fake.date_between(start_date="-3y", end_date="-1m"),
            )
        )

    session.add_all(sellers)
    session.commit()
    return len(sellers)
