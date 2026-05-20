"""Seed `orders` and `order_items` with realistic snapshots and lifecycles.

Every count, weight and probability comes from `config.yml::orders` and
`config.yml::weights` — edit the YAML, not this file.

For each order we:
- pick an active customer (FK lookup via SELECT, no in-memory hand-off),
- pick 1-N active products and snapshot their price, cost and seller onto
  the line items,
- compute money (subtotal → +shipping +tax −discount = total),
- pick a lifecycle (status + timestamps) consistent with `placed_at` age,
- ship to the customer's address most of the time, a different address
  sometimes (adds geographic variance for BI).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import CONFIG
from ..enums.order import Currency, OrderStatus
from ..models import Customer, Order, OrderItem, Product
from .factories import fake_location, from_weights, money, rng

logger = logging.getLogger(__name__)


def seed(session: Session) -> int:
    if session.scalar(select(Order).limit(1)) is not None:
        logger.info("orders: table already populated, skipping")
        return 0

    customers = list(
        session.scalars(select(Customer).where(Customer.is_active.is_(True)))
    )
    if not customers:
        raise RuntimeError("No active customers found — seed customers first.")

    products = list(
        session.scalars(select(Product).where(Product.is_active.is_(True)))
    )
    if not products:
        raise RuntimeError("No active products found — seed products first.")

    cfg = CONFIG.orders
    now = datetime.now()
    inserted = 0

    for i in range(CONFIG.counts.orders):
        customer = rng.choice(customers)
        # Orders happen after signup and no later than "now".
        placed_at = _datetime_between(customer.signup_at, now)

        # Pick distinct products for the cart — never duplicate a product
        # within the same order.
        n_items = rng.randint(cfg.items_per_order.min, cfg.items_per_order.max)
        n_items = min(n_items, len(products))
        chosen = rng.sample(products, k=n_items)

        items: list[OrderItem] = []
        subtotal = Decimal("0")
        for product in chosen:
            quantity = from_weights(CONFIG.weights.item_quantity)
            unit_price = product.price
            unit_cost = product.cost
            line_discount = (
                money(unit_price * Decimal(str(round(rng.uniform(0.02, 0.15), 4))))
                if rng.random() < cfg.line_discount_probability
                else Decimal("0.00")
            )
            subtotal += unit_price * quantity - line_discount
            items.append(
                OrderItem(
                    product_id=product.id,
                    seller_id=product.seller_id,  # snapshot at sale time
                    quantity=quantity,
                    unit_price=unit_price,
                    unit_cost=unit_cost,
                    discount_amount=line_discount,
                )
            )

        subtotal = money(subtotal)
        shipping_cost = _shipping_for(subtotal)
        tax_amount = money(subtotal * cfg.tax_rate)
        order_discount = (
            money(subtotal * Decimal(str(round(rng.uniform(0.05, 0.20), 4))))
            if rng.random() < cfg.order_discount_probability
            else Decimal("0.00")
        )
        total = money(subtotal + shipping_cost + tax_amount - order_discount)

        # Most orders ship to the customer's address; a minority go elsewhere
        # (gift, alternate office) — adds geographic variance for BI.
        if rng.random() < 0.80:
            ship_country = customer.country
            ship_state = customer.state
            ship_city = customer.city
            ship_postal_code = customer.postal_code
        else:
            ship_country, ship_state, ship_city, ship_postal_code = fake_location()

        status, paid_at, shipped_at, delivered_at = _lifecycle(placed_at, now)

        order = Order(
            order_number=f"ORD-{placed_at.year}-{i + 1:06d}",
            customer_id=customer.id,
            channel=from_weights(CONFIG.weights.sales_channel),
            status=status,
            placed_at=placed_at,
            paid_at=paid_at,
            shipped_at=shipped_at,
            delivered_at=delivered_at,
            payment_method=_payment_method_for(ship_country),
            payment_installments=_installments_for_amount(total),
            currency=Currency.BRL.value if ship_country == "BR" else Currency.USD.value,
            subtotal=subtotal,
            shipping_cost=shipping_cost,
            tax_amount=tax_amount,
            discount_amount=order_discount,
            total=total,
            ship_country=ship_country,
            ship_state=ship_state,
            ship_city=ship_city,
            ship_postal_code=ship_postal_code,
        )
        session.add(order)
        session.flush()  # generates order.id so items can reference it

        for item in items:
            item.order_id = order.id
            session.add(item)

        inserted += 1
        if inserted % cfg.commit_every == 0:
            session.commit()
            logger.info("orders: %d / %d committed", inserted, CONFIG.counts.orders)

    session.commit()
    return inserted


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _datetime_between(start: datetime, end: datetime) -> datetime:
    """Pick a random datetime in [start, end). Uses the seeded RNG (Faker's
    built-in randomness would not respect our seed otherwise).
    """
    if end <= start:
        return start
    delta_seconds = int((end - start).total_seconds())
    return start + timedelta(seconds=rng.randint(0, delta_seconds))


def _shipping_for(subtotal: Decimal) -> Decimal:
    base = money(rng.uniform(10, 80))
    fs = CONFIG.orders.free_shipping
    if subtotal > fs.threshold and rng.random() < fs.probability:
        return Decimal("0.00")
    return base


def _payment_method_for(country: str) -> str:
    """Brazilian orders skew toward Pix/Boleto; others toward cards."""
    weights = (
        CONFIG.weights.payment_method_br
        if country == "BR"
        else CONFIG.weights.payment_method_intl
    )
    return from_weights(weights)


def _installments_for_amount(total: Decimal) -> int:
    """Brazilian-style installment behaviour: low-value orders à vista, big
    tickets split into more parcelas. Bands hard-coded — they're a behavioral
    decision, not a knob worth YAML-izing.
    """
    if total < Decimal("100"):
        return 1
    if total < Decimal("500"):
        return from_weights({1: 70, 2: 20, 3: 10})
    if total < Decimal("2000"):
        return from_weights({1: 40, 2: 20, 3: 20, 6: 15, 10: 5})
    return from_weights({1: 20, 3: 20, 6: 25, 10: 25, 12: 10})


def _lifecycle(
    placed_at: datetime, now: datetime
) -> tuple[str, Optional[datetime], Optional[datetime], Optional[datetime]]:
    """Pick (status, paid_at, shipped_at, delivered_at) consistent with the
    order's age. Older orders are more likely to be delivered; brand-new
    orders may still be sitting in `placed`.
    """
    age_days = (now - placed_at).days
    cfg = CONFIG.orders
    roll = rng.random()

    # Always-possible exits.
    if roll < cfg.cancellation_rate:
        return OrderStatus.CANCELLED.value, None, None, None
    if roll < cfg.cancellation_rate + cfg.refund_rate:
        paid_at = placed_at + timedelta(hours=rng.randint(0, 24))
        return OrderStatus.REFUNDED.value, paid_at, None, None

    # Happy path.
    paid_at = placed_at + timedelta(hours=rng.randint(0, 24))
    if age_days < 1:
        # Brand-new — half are still unpaid.
        if rng.random() < 0.5:
            return OrderStatus.PLACED.value, None, None, None
        return OrderStatus.PAID.value, paid_at, None, None

    shipped_at = paid_at + timedelta(days=rng.randint(0, 3))
    if age_days < 5:
        return OrderStatus.SHIPPED.value, paid_at, shipped_at, None

    delivered_at = shipped_at + timedelta(days=rng.randint(1, 7))
    return OrderStatus.DELIVERED.value, paid_at, shipped_at, delivered_at
