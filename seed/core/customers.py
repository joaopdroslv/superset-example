"""Seed `customers` with weighted demographics, segments, and channels.

All distributions come from `config.yml::weights.{customer_gender,
customer_segment, acquisition_channel}` — edit the YAML, not this file.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import CONFIG
from ..models import Customer
from .factories import fake, fake_location, from_weights, rng

logger = logging.getLogger(__name__)


def seed(session: Session) -> int:
    if session.scalar(select(Customer).limit(1)) is not None:
        logger.info("customers: table already populated, skipping")
        return 0

    customers: list[Customer] = []
    for _ in range(CONFIG.counts.customers):
        country, state, city, postal_code = fake_location()

        customers.append(
            Customer(
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                email=fake.unique.email(),
                phone=fake.phone_number(),
                gender=from_weights(CONFIG.weights.customer_gender),
                birth_date=fake.date_of_birth(minimum_age=18, maximum_age=80),
                country=country,
                state=state,
                city=city,
                postal_code=postal_code,
                segment=from_weights(CONFIG.weights.customer_segment),
                acquisition_channel=from_weights(CONFIG.weights.acquisition_channel),
                is_active=rng.random() > 0.05,
                signup_at=fake.date_time_between(start_date="-3y", end_date="-1d"),
            )
        )

    session.add_all(customers)
    session.commit()
    return len(customers)
