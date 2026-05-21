"""Seed `addresses`.

Every customer and every active seller gets at least one address marked as
`is_default`. Extra addresses (per config knobs) are scattered: customers can
have alt destinations (work, gift), sellers can have additional warehouses.

The address's geo (country/state/city) reuses the *owner's* primary location
for the default address — keeps the foundation realistic — and uses random
locations for the extras. Each address gets a `zone_id` resolved via
`factories.state_to_zone_code`.
"""

from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import CONFIG
from ..models import Address, Customer, Seller, ShippingZone
from .factories import fake, fake_location, rng, state_to_zone_code

logger = logging.getLogger(__name__)


def seed(session: Session) -> int:
    if session.scalar(select(Address).limit(1)) is not None:
        logger.info("addresses: already populated, skipping")
        return 0

    zone_by_code: dict[str, int] = dict(
        session.execute(select(ShippingZone.code, ShippingZone.id)).all()
    )
    if not zone_by_code:
        raise RuntimeError("no shipping_zones found — seed shipping first")

    inserted = 0
    inserted += _seed_for_customers(session, zone_by_code)
    inserted += _seed_for_sellers(session, zone_by_code)
    session.commit()
    return inserted


def _build_address(
    *,
    owner_id_field: str,
    owner_id: int,
    label: str,
    country: str,
    state: str,
    city: str,
    postal_code: str | None,
    is_default: bool,
    zone_by_code: dict[str, int],
) -> Address:
    return Address(
        **{owner_id_field: owner_id},
        label=label,
        is_default=is_default,
        line1=fake.street_address(),
        line2=None if rng.random() > 0.25 else f"Apt {rng.randint(1, 999)}",
        neighborhood=fake.neighborhood() if rng.random() > 0.30 else None,
        city=city,
        state=state,
        country=country,
        postal_code=postal_code or fake.postcode(),
        latitude=Decimal(str(round(rng.uniform(-33.0, 5.0), 6))) if country == "BR" else None,
        longitude=Decimal(str(round(rng.uniform(-74.0, -34.0), 6))) if country == "BR" else None,
        zone_id=zone_by_code.get(state_to_zone_code(country, state)),
    )


def _seed_for_customers(session: Session, zone_by_code: dict[str, int]) -> int:
    customers = list(session.scalars(select(Customer)))
    n = 0
    rng_min = CONFIG.addresses.per_customer.min
    rng_max = CONFIG.addresses.per_customer.max
    for c in customers:
        # Default address mirrors the customer's primary location.
        session.add(
            _build_address(
                owner_id_field="customer_id",
                owner_id=c.id,
                label="Casa",
                country=c.country,
                state=c.state,
                city=c.city,
                postal_code=c.postal_code,
                is_default=True,
                zone_by_code=zone_by_code,
            )
        )
        n += 1
        for _ in range(rng.randint(rng_min, rng_max)):
            country, state, city, postal = fake_location()
            session.add(
                _build_address(
                    owner_id_field="customer_id",
                    owner_id=c.id,
                    label=rng.choice(["Trabalho", "Recado", "Casa de Familiar", "Outro"]),
                    country=country,
                    state=state,
                    city=city,
                    postal_code=postal,
                    is_default=False,
                    zone_by_code=zone_by_code,
                )
            )
            n += 1
    return n


def _seed_for_sellers(session: Session, zone_by_code: dict[str, int]) -> int:
    sellers = list(session.scalars(select(Seller).where(Seller.is_active.is_(True))))
    n = 0
    rng_min = CONFIG.addresses.per_seller.min
    rng_max = CONFIG.addresses.per_seller.max
    for s in sellers:
        session.add(
            _build_address(
                owner_id_field="seller_id",
                owner_id=s.id,
                label="Galpão Principal",
                country=s.country,
                state=s.state,
                city=s.city,
                postal_code=s.postal_code,
                is_default=True,
                zone_by_code=zone_by_code,
            )
        )
        n += 1
        for i in range(rng.randint(rng_min, rng_max)):
            country, state, city, postal = fake_location()
            session.add(
                _build_address(
                    owner_id_field="seller_id",
                    owner_id=s.id,
                    label=f"Galpão Regional {i + 2}",
                    country=country,
                    state=state,
                    city=city,
                    postal_code=postal,
                    is_default=False,
                    zone_by_code=zone_by_code,
                )
            )
            n += 1
    return n
