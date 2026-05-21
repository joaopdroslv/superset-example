"""Seed `shipping_carriers` and `shipping_zones`.

Small dim tables — both populated from hard-coded reference data in
`factories.py` (carrier roster, BR macro-regions). One-shot, idempotent.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ShippingCarrier, ShippingZone
from .factories import SHIPPING_CARRIERS, SHIPPING_ZONE_INTL, SHIPPING_ZONES_BR

logger = logging.getLogger(__name__)


def seed(session: Session) -> int:
    inserted = 0
    inserted += _seed_zones(session)
    inserted += _seed_carriers(session)
    return inserted


def _seed_zones(session: Session) -> int:
    if session.scalar(select(ShippingZone).limit(1)) is not None:
        logger.info("shipping_zones: already populated, skipping")
        return 0

    zones = [ShippingZone(**z) for z in SHIPPING_ZONES_BR]
    zones.append(ShippingZone(**SHIPPING_ZONE_INTL))
    session.add_all(zones)
    session.commit()
    return len(zones)


def _seed_carriers(session: Session) -> int:
    if session.scalar(select(ShippingCarrier).limit(1)) is not None:
        logger.info("shipping_carriers: already populated, skipping")
        return 0

    carriers = [ShippingCarrier(is_active=True, **c) for c in SHIPPING_CARRIERS]
    session.add_all(carriers)
    session.commit()
    return len(carriers)
