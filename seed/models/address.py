from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Numeric, String
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .customer import Customer
    from .seller import Seller
    from .shipment import Shipment
    from .shipping import ShippingZone


class Address(Base, TimestampMixin):
    """Postal address book entry. Owned by EITHER a customer or a seller
    (XOR enforced at the DB via CheckConstraint).

    Customers use these as shipping destinations; sellers use them as
    warehouse origins. The same model is reused for both so the shipment FKs
    can target a single table.
    """

    __tablename__ = "addresses"
    __table_args__ = (
        CheckConstraint(
            "(customer_id IS NULL) != (seller_id IS NULL)",
            name="address_owner_xor",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # --- Ownership (exactly one of these is set) ---
    customer_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), nullable=True, index=True
    )
    seller_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sellers.id", ondelete="CASCADE"), nullable=True, index=True
    )

    # --- Label / metadata ---
    label: Mapped[str] = mapped_column(String(60), nullable=False)  # "Home", "Warehouse SP", ...
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # --- Address fields ---
    line1: Mapped[str] = mapped_column(String(160), nullable=False)
    line2: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    neighborhood: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    city: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    country: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    postal_code: Mapped[str] = mapped_column(String(20), nullable=False)

    # --- Geo (for map-based charts in Superset) ---
    latitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 6), nullable=True)

    # --- Shipping zone (region grouping for tariff analytics) ---
    zone_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("shipping_zones.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # --- Relationships ---
    customer: Mapped[Optional["Customer"]] = relationship(back_populates="addresses")
    seller: Mapped[Optional["Seller"]] = relationship(back_populates="addresses")
    zone: Mapped[Optional["ShippingZone"]] = relationship(back_populates="addresses")
    shipments_as_origin: Mapped[List["Shipment"]] = relationship(
        back_populates="origin_address",
        foreign_keys="Shipment.origin_address_id",
    )
    shipments_as_dest: Mapped[List["Shipment"]] = relationship(
        back_populates="dest_address",
        foreign_keys="Shipment.dest_address_id",
    )
