"""Shipment + ShipmentEvent — the shipping fact tables.

A single `Order` can produce multiple `Shipment` rows when items come from
different sellers (marketplace split shipping). Every `Shipment` has a
timeline recorded as `ShipmentEvent` rows (carrier scans).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .address import Address
    from .order import Order, OrderItem
    from .shipping import ShippingCarrier


class Shipment(Base, TimestampMixin):
    """One delivery from one origin to one destination. Snapshots both
    addresses (FK to `addresses` rows that are themselves point-in-time —
    the seeder creates dedicated rows per shipment when sourcing from a
    seller warehouse, so edits later don't drift).
    """

    __tablename__ = "shipments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    carrier_id: Mapped[int] = mapped_column(
        ForeignKey("shipping_carriers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # economy | standard | express | same_day (enums/shipping.py::ServiceLevel)
    service_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default="standard", index=True
    )

    tracking_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)

    # FK snapshots — see class docstring.
    origin_address_id: Mapped[int] = mapped_column(
        ForeignKey("addresses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    dest_address_id: Mapped[int] = mapped_column(
        ForeignKey("addresses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    declared_weight_kg: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False)
    shipping_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Lifecycle timestamps — all nullable; populated as the shipment progresses.
    estimated_delivery_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, index=True
    )
    dispatched_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, index=True
    )

    # pending | dispatched | in_transit | out_for_delivery | delivered | exception | returned
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )

    # --- Relationships ---
    order: Mapped["Order"] = relationship(back_populates="shipments")
    carrier: Mapped["ShippingCarrier"] = relationship(back_populates="shipments")
    origin_address: Mapped["Address"] = relationship(
        foreign_keys=[origin_address_id], back_populates="shipments_as_origin"
    )
    dest_address: Mapped["Address"] = relationship(
        foreign_keys=[dest_address_id], back_populates="shipments_as_dest"
    )
    items: Mapped[List["OrderItem"]] = relationship(back_populates="shipment")
    events: Mapped[List["ShipmentEvent"]] = relationship(
        back_populates="shipment",
        cascade="all, delete-orphan",
        order_by="ShipmentEvent.occurred_at",
    )


class ShipmentEvent(Base, TimestampMixin):
    """A single carrier scan / status change. Ordered by `occurred_at` to
    reconstruct the shipment timeline. Always at least one row per shipment
    ("created"); usually a chain of 3-7.
    """

    __tablename__ = "shipment_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    shipment_id: Mapped[int] = mapped_column(
        ForeignKey("shipments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # created | picked_up | in_transit | out_for_delivery | delivered
    #         | delivery_failed | exception | returned
    event_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    # Where the scan happened (e.g. "Distribution Center São Paulo - SP").
    location: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    shipment: Mapped["Shipment"] = relationship(back_populates="events")
