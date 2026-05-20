from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..enums.order import Currency, OrderStatus, SalesChannel
from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .customer import Customer
    from .product import Product
    from .seller import Seller


class Order(Base, TimestampMixin):
    """A purchase. Carries denormalized shipping address, payment, and totals
    decomposition (subtotal / shipping / tax / discount / total) so reports can
    answer questions like "tax burden by state" or "shipping share of revenue"
    without joining through line items.
    """

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # --- Sales channel & lifecycle ---
    # Valid values defined in `enums/order.py::{SalesChannel, OrderStatus}`.
    channel: Mapped[str] = mapped_column(
        String(20), nullable=False, default=SalesChannel.WEB.value, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=OrderStatus.PLACED.value, index=True
    )
    placed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    shipped_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # --- Payment ---
    # Valid values defined in `enums/order.py::PaymentMethod`.
    payment_method: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    # Brazil-style installment count; defaults to 1 (à vista / single payment).
    payment_installments: Mapped[int] = mapped_column(nullable=False, default=1)
    # Valid values defined in `enums/order.py::Currency`.
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default=Currency.BRL.value, index=True
    )

    # --- Money breakdown (all in `currency`) ---
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    shipping_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    # --- Shipping address snapshot (may differ from the customer's primary) ---
    ship_country: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    ship_state: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    ship_city: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    ship_postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    customer: Mapped["Customer"] = relationship(back_populates="orders")
    items: Mapped[List["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
    )


class OrderItem(Base, TimestampMixin):
    """One product line on an order. Carries seller, price and cost snapshots
    so reports about historical margin and seller share remain truthful when
    the catalog later changes.
    """

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Historical attribution — the seller credited for THIS sale, even if the
    # product is later moved to a different seller.
    seller_id: Mapped[int] = mapped_column(
        ForeignKey("sellers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    quantity: Mapped[int] = mapped_column(nullable=False, default=1)
    # Snapshots — see class docstring.
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    # Line-level discount (the order-level discount lives on Order).
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)

    order: Mapped["Order"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship(back_populates="items")
    seller: Mapped["Seller"] = relationship(back_populates="sold_items")
