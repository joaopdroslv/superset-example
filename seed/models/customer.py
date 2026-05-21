from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Date, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..enums.customer import AcquisitionChannel, CustomerSegment
from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .address import Address
    from .order import Order


class Customer(Base, TimestampMixin):
    """A buyer. Geographic + demographic + acquisition fields are denormalized
    on purpose so Superset can group/filter without extra joins.
    """

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # --- Identity ---
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    email: Mapped[str] = mapped_column(String(180), unique=True, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    # --- Demographics (all nullable: not every customer discloses these) ---
    # Valid values defined in `enums/customer.py::Gender`.
    gender: Mapped[Optional[str]] = mapped_column(String(1), nullable=True, index=True)
    birth_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # --- Primary address (denormalized for BI; ship address lives on Order) ---
    country: Mapped[str] = mapped_column(String(2), nullable=False, index=True)  # ISO 3166-1 alpha-2
    state: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    city: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # --- Segmentation / acquisition (great BI dimensions) ---
    # Valid values defined in `enums/customer.py::{CustomerSegment, AcquisitionChannel}`.
    segment: Mapped[str] = mapped_column(
        String(20), nullable=False, default=CustomerSegment.B2C.value, index=True
    )
    acquisition_channel: Mapped[str] = mapped_column(
        String(20), nullable=False, default=AcquisitionChannel.ORGANIC.value, index=True
    )

    # --- Lifecycle ---
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Distinct from `created_at`: lets the seeder backdate signups for cohort
    # analysis, while `created_at` remains the row-insert timestamp.
    signup_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), index=True
    )

    orders: Mapped[List["Order"]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
    )
    addresses: Mapped[List["Address"]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
    )
