from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Date, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..enums.seller import SellerType
from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .address import Address
    from .order import OrderItem
    from .product import Product


class Seller(Base, TimestampMixin):
    """A merchant. Models both first-party (the store itself) and third-party
    marketplace sellers via `seller_type`, so reports can compare 1P vs 3P
    revenue, GMV by seller, commission spend, etc.
    """

    __tablename__ = "sellers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # --- Identity ---
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(180), unique=True, nullable=False)

    # --- Address (origin / warehouse) ---
    country: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    city: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # --- Marketplace economics ---
    # Valid values defined in `enums/seller.py::SellerType`.
    seller_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default=SellerType.MARKETPLACE.value, index=True
    )
    # Fraction of GMV kept by the platform, e.g. 0.1500 = 15%. Useful for
    # computing platform revenue vs seller revenue in reports.
    commission_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, default=Decimal("0.0000")
    )
    # Aggregated review rating, 0.00 – 5.00.
    rating: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2), nullable=True)

    # --- Lifecycle ---
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    onboarded_on: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)

    products: Mapped[List["Product"]] = relationship(back_populates="seller")
    # Historical link via the snapshot on OrderItem.
    sold_items: Mapped[List["OrderItem"]] = relationship(back_populates="seller")
    addresses: Mapped[List["Address"]] = relationship(
        back_populates="seller",
        cascade="all, delete-orphan",
    )
