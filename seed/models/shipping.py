"""Shipping dimension models — carriers and zones.

Both are small lookup tables referenced by the higher-cardinality `shipments`
fact table. Kept in a single file because they're tightly related and small.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .address import Address
    from .shipment import Shipment


class ShippingCarrier(Base, TimestampMixin):
    """A logistics provider (Correios, Loggi, Total Express, ...).

    `service_levels` is a comma-separated string of supported levels (e.g.
    "standard,express"); the seeder picks from this list when creating
    shipments. Kept denormalized — modeling per-level capability as a separate
    join table adds complexity without enabling new BI questions.
    """

    __tablename__ = "shipping_carriers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False, index=True)

    # CSV of ServiceLevel enum values supported by this carrier.
    service_levels: Mapped[str] = mapped_column(String(120), nullable=False, default="standard")

    # Used by the seeder to compute estimated_delivery_at.
    typical_lead_time_hours: Mapped[int] = mapped_column(nullable=False, default=72)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    shipments: Mapped[List["Shipment"]] = relationship(back_populates="carrier")


class ShippingZone(Base, TimestampMixin):
    """A geographic region grouping multiple states (e.g. "Sudeste").

    Used as a coarser-grained dim than `state` for cost reports — same-zone
    shipments are cheaper, cross-zone shipments pay a penalty. State→zone
    mapping is held in `factories.STATE_TO_ZONE` and applied at address-seed
    time.
    """

    __tablename__ = "shipping_zones"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    addresses: Mapped[List["Address"]] = relationship(back_populates="zone")
