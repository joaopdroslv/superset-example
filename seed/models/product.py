from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .category import Category
    from .order import OrderItem
    from .seller import Seller


class Product(Base, TimestampMixin):
    """A catalog SKU. `price` and `cost` here are the *current* values — the
    historical snapshots travel on `OrderItem` so margin reports stay correct
    when these change.
    """

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sku: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    brand: Mapped[Optional[str]] = mapped_column(String(80), nullable=True, index=True)

    # --- Pricing ---
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # --- Physical attributes (useful for shipping reports) ---
    weight_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 3), nullable=True)

    # --- Relationships ---
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Current owner of the listing. Order items also snapshot the seller at
    # sale time (see OrderItem.seller_id) so historic attribution survives a
    # listing transfer.
    seller_id: Mapped[int] = mapped_column(
        ForeignKey("sellers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # --- Lifecycle ---
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    launched_on: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)

    category: Mapped["Category"] = relationship(back_populates="products")
    seller: Mapped["Seller"] = relationship(back_populates="products")
    items: Mapped[List["OrderItem"]] = relationship(back_populates="product")
