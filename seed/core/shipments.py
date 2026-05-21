"""Seed `shipments` and `shipment_events`, then reconcile `orders.shipping_cost`.

For each non-cancelled order:
  1. Group items by seller. If multi-seller, split into N shipments (rolled
     against `shipments.split_shipping_probability`); otherwise consolidate
     into one shipment from the primary seller's warehouse.
  2. Each shipment picks a carrier, service level, origin (seller default
     address), destination (customer default address) and computes
     cost = base + weight*factor + cross-zone-penalty.
  3. Status / timestamps derive from the parent order:
        order PLACED / PAID         → shipment PENDING (no dispatch yet)
        order SHIPPED               → shipment IN_TRANSIT or OUT_FOR_DELIVERY
        order DELIVERED             → shipment DELIVERED
        order CANCELLED             → no shipment created
        order REFUNDED              → shipment RETURNED (was delivered)
  4. Event chain matches the lifecycle, ending at delivered_at / occurred_at.
  5. Back-fill `OrderItem.shipment_id` so individual lines know their carrier.
  6. Update `Order.shipping_cost = SUM(shipments.shipping_cost)` and recompute
     `Order.total = subtotal + shipping_cost + tax - discount`.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..config import CONFIG
from ..enums.order import OrderStatus
from ..enums.shipping import ServiceLevel, ShipmentEventType, ShippingStatus
from ..models import (
    Address,
    Order,
    OrderItem,
    Product,
    Shipment,
    ShipmentEvent,
    ShippingCarrier,
)
from .factories import (
    compute_shipping_cost,
    fake,
    from_weights,
    money,
    rng,
    state_to_zone_code,
    tracking_location,
)

logger = logging.getLogger(__name__)

COMMIT_EVERY = 100


def seed(session: Session) -> int:
    if session.scalar(select(Shipment).limit(1)) is not None:
        logger.info("shipments: already populated, skipping")
        return 0

    carriers = list(session.scalars(select(ShippingCarrier).where(ShippingCarrier.is_active.is_(True))))
    if not carriers:
        raise RuntimeError("no active shipping_carriers found — seed shipping first")

    # Default-address index by owner — avoids N+1 lookups during the main loop.
    default_addr_by_customer: dict[int, int] = dict(
        session.execute(
            select(Address.customer_id, Address.id)
            .where(Address.customer_id.is_not(None), Address.is_default.is_(True))
        ).all()
    )
    default_addr_by_seller: dict[int, int] = dict(
        session.execute(
            select(Address.seller_id, Address.id)
            .where(Address.seller_id.is_not(None), Address.is_default.is_(True))
        ).all()
    )
    addresses_by_id: dict[int, Address] = {
        a.id: a for a in session.scalars(select(Address))
    }

    # Product weights — used to compute shipment declared_weight_kg.
    weight_by_product: dict[int, Decimal] = {
        pid: (w or Decimal("0.5"))  # 500g fallback for products with NULL weight
        for pid, w in session.execute(select(Product.id, Product.weight_kg))
    }

    orders = list(
        session.scalars(
            select(Order).options(selectinload(Order.items))
        )
    )

    inserted_shipments = 0
    inserted_events = 0

    for i, order in enumerate(orders):
        new_shipments, new_events = _process_order(
            session,
            order,
            carriers=carriers,
            default_addr_by_customer=default_addr_by_customer,
            default_addr_by_seller=default_addr_by_seller,
            addresses_by_id=addresses_by_id,
            weight_by_product=weight_by_product,
        )
        inserted_shipments += new_shipments
        inserted_events += new_events

        if (i + 1) % COMMIT_EVERY == 0:
            session.commit()
            logger.info(
                "shipments: order %d / %d (shipments=%d, events=%d so far)",
                i + 1, len(orders), inserted_shipments, inserted_events,
            )

    session.commit()
    logger.info(
        "shipments: total inserted — shipments=%d, events=%d",
        inserted_shipments, inserted_events,
    )
    return inserted_shipments


def _process_order(
    session: Session,
    order: Order,
    *,
    carriers: list[ShippingCarrier],
    default_addr_by_customer: dict[int, int],
    default_addr_by_seller: dict[int, int],
    addresses_by_id: dict[int, Address],
    weight_by_product: dict[int, Decimal],
) -> tuple[int, int]:
    # Cancelled orders: no shipment, zero shipping cost.
    if order.status == OrderStatus.CANCELLED.value:
        order.shipping_cost = Decimal("0.00")
        order.total = money(order.subtotal + order.tax_amount - order.discount_amount)
        return 0, 0

    dest_addr_id = default_addr_by_customer.get(order.customer_id)
    if dest_addr_id is None:
        raise RuntimeError(f"customer {order.customer_id} has no default address")
    dest_addr = addresses_by_id[dest_addr_id]

    # Group items by seller for split-shipping decision.
    items_by_seller: dict[int, list[OrderItem]] = {}
    for item in order.items:
        items_by_seller.setdefault(item.seller_id, []).append(item)

    multi_seller = len(items_by_seller) > 1
    do_split = multi_seller and rng.random() < CONFIG.shipments.split_shipping_probability

    shipments_to_make: list[tuple[int, list[OrderItem]]]  # (seller_id, items)
    if do_split:
        shipments_to_make = list(items_by_seller.items())
    else:
        # Consolidate at the seller with the largest line count (proxy for "primary").
        primary_seller_id = max(items_by_seller, key=lambda sid: len(items_by_seller[sid]))
        shipments_to_make = [(primary_seller_id, list(order.items))]

    created: list[Shipment] = []
    n_events = 0
    for shipment_idx, (seller_id, items) in enumerate(shipments_to_make):
        origin_addr_id = default_addr_by_seller.get(seller_id)
        if origin_addr_id is None:
            raise RuntimeError(f"seller {seller_id} has no default address")
        origin_addr = addresses_by_id[origin_addr_id]

        weight = sum(
            (weight_by_product.get(it.product_id, Decimal("0.5")) * it.quantity for it in items),
            start=Decimal("0"),
        )
        # Clamp to non-zero so the cost formula doesn't degenerate.
        if weight <= 0:
            weight = Decimal("0.10")

        same_zone = state_to_zone_code(origin_addr.country, origin_addr.state) == state_to_zone_code(
            dest_addr.country, dest_addr.state
        )
        cost = compute_shipping_cost(weight, same_zone=same_zone)

        carrier = rng.choice(carriers)
        service_level = _pick_service_level(carrier)

        ship_status, dispatched_at, delivered_at = _shipment_lifecycle(order)
        on_time = rng.random() < CONFIG.shipments.on_time_delivery_rate
        estimated_at = _estimate_delivery(
            order.placed_at,
            carrier.typical_lead_time_hours,
            delivered_at,
            on_time=on_time,
        )

        shipment = Shipment(
            order_id=order.id,
            carrier_id=carrier.id,
            service_level=service_level,
            tracking_number=_tracking_number(carrier.code, shipment_idx),
            origin_address_id=origin_addr_id,
            dest_address_id=dest_addr_id,
            declared_weight_kg=money(weight),
            shipping_cost=cost,
            estimated_delivery_at=estimated_at,
            dispatched_at=dispatched_at,
            delivered_at=delivered_at,
            status=ship_status,
        )
        session.add(shipment)
        session.flush()  # need shipment.id for items + events

        for item in items:
            item.shipment_id = shipment.id

        events = _build_events(shipment, order, origin_addr, dest_addr)
        session.add_all(events)
        n_events += len(events)

        created.append(shipment)

    # Reconcile order totals with the actual shipments.
    total_ship = sum((s.shipping_cost for s in created), start=Decimal("0.00"))
    order.shipping_cost = money(total_ship)
    order.total = money(order.subtotal + order.shipping_cost + order.tax_amount - order.discount_amount)

    return len(created), n_events


# ---------------------------------------------------------------------------
# Lifecycle helpers
# ---------------------------------------------------------------------------


def _shipment_lifecycle(
    order: Order,
) -> tuple[str, Optional[datetime], Optional[datetime]]:
    """Map (Order.status, Order.{paid,shipped,delivered}_at) → shipment state."""
    status = order.status
    if status in (OrderStatus.PLACED.value, OrderStatus.PAID.value):
        return ShippingStatus.PENDING.value, None, None
    if status == OrderStatus.SHIPPED.value:
        # Either in transit or out for delivery — both are "dispatched, not delivered".
        ship_status = rng.choices(
            [ShippingStatus.IN_TRANSIT.value, ShippingStatus.OUT_FOR_DELIVERY.value],
            weights=[80, 20],
            k=1,
        )[0]
        return ship_status, order.shipped_at, None
    if status == OrderStatus.DELIVERED.value:
        return ShippingStatus.DELIVERED.value, order.shipped_at, order.delivered_at
    if status == OrderStatus.REFUNDED.value:
        # Modeled as "delivered then returned" — return timestamp is after delivery.
        delivered_at = order.delivered_at or (order.shipped_at + timedelta(days=2)) if order.shipped_at else order.paid_at
        return ShippingStatus.RETURNED.value, order.shipped_at or order.paid_at, delivered_at
    return ShippingStatus.PENDING.value, None, None


def _estimate_delivery(
    placed_at: datetime,
    lead_hours: int,
    delivered_at: Optional[datetime],
    *,
    on_time: bool,
) -> datetime:
    """Carrier-promised delivery date.

    For shipments that don't have a delivered_at yet (PENDING / IN_TRANSIT /
    OUT_FOR_DELIVERY), emit a forward-looking estimate from placed_at + the
    carrier's typical lead time, plus jitter.

    For delivered/returned shipments we anchor the estimate around the actual
    `delivered_at` and the desired on-time outcome: on-time → estimate is on
    or after delivery, late → estimate is before delivery. This makes the
    `delivered_at <= estimated_delivery_at` BI check honor
    `config.shipments.on_time_delivery_rate`.
    """
    if delivered_at is None:
        jitter = rng.uniform(-0.2, 0.4)  # -20% to +40%
        return placed_at + timedelta(hours=int(lead_hours * (1 + jitter)))
    if on_time:
        # Promised same day or up to 36h after actual delivery → counts as on-time.
        return delivered_at + timedelta(hours=rng.randint(0, 36))
    # Promised before actual delivery → counts as late.
    return delivered_at - timedelta(hours=rng.randint(12, 96))


def _pick_service_level(carrier: ShippingCarrier) -> str:
    """Weighted pick restricted to the levels this carrier supports."""
    supported = {s.strip() for s in carrier.service_levels.split(",") if s.strip()}
    weights = {
        level: w for level, w in CONFIG.weights.service_level.items() if level in supported
    }
    if not weights:
        return ServiceLevel.STANDARD.value
    return from_weights(weights)


def _tracking_number(carrier_code: str, idx: int) -> str:
    # carrier_code-XXXXXXXX where X is alphanumeric — fake.bothify keeps Faker seeded.
    return f"{carrier_code}-{fake.bothify('????????').upper()}-{idx}"


# ---------------------------------------------------------------------------
# Event timeline
# ---------------------------------------------------------------------------


def _build_events(
    shipment: Shipment,
    order: Order,
    origin: Address,
    dest: Address,
) -> list[ShipmentEvent]:
    """Reconstruct a plausible carrier-scan timeline for the shipment."""
    created_at = order.paid_at or order.placed_at
    events: list[ShipmentEvent] = [
        ShipmentEvent(
            shipment_id=shipment.id,
            event_type=ShipmentEventType.CREATED.value,
            occurred_at=created_at,
            location=tracking_location(origin.city, origin.state),
            notes="Etiqueta de envio gerada.",
        )
    ]

    if shipment.dispatched_at is None:
        return events  # PENDING shipments stop at "created"

    events.append(
        ShipmentEvent(
            shipment_id=shipment.id,
            event_type=ShipmentEventType.PICKED_UP.value,
            occurred_at=shipment.dispatched_at,
            location=tracking_location(origin.city, origin.state),
            notes="Coletado pelo transportador.",
        )
    )

    # IN_TRANSIT scans between dispatched_at and (delivered_at or estimated_at).
    n_total = rng.randint(
        CONFIG.shipments.events_per_shipment.min,
        CONFIG.shipments.events_per_shipment.max,
    )
    n_transit = max(0, n_total - len(events) - 2)  # reserve room for OUT_FOR_DELIVERY + DELIVERED
    end_at = shipment.delivered_at or shipment.estimated_delivery_at or (
        shipment.dispatched_at + timedelta(days=3)
    )
    total_seconds = max(int((end_at - shipment.dispatched_at).total_seconds()), 60)
    for k in range(n_transit):
        # Evenly distribute scans, with a small jitter.
        frac = (k + 1) / (n_transit + 2)
        ts = shipment.dispatched_at + timedelta(
            seconds=int(total_seconds * frac * rng.uniform(0.9, 1.1))
        )
        events.append(
            ShipmentEvent(
                shipment_id=shipment.id,
                event_type=ShipmentEventType.IN_TRANSIT.value,
                occurred_at=ts,
                location=tracking_location(fake.city(), dest.state),
                notes=None,
            )
        )

    if shipment.status == ShippingStatus.OUT_FOR_DELIVERY.value:
        events.append(
            ShipmentEvent(
                shipment_id=shipment.id,
                event_type=ShipmentEventType.OUT_FOR_DELIVERY.value,
                occurred_at=end_at,
                location=tracking_location(dest.city, dest.state),
            )
        )
    elif shipment.status == ShippingStatus.DELIVERED.value:
        events.append(
            ShipmentEvent(
                shipment_id=shipment.id,
                event_type=ShipmentEventType.OUT_FOR_DELIVERY.value,
                occurred_at=end_at - timedelta(hours=rng.randint(1, 8)),
                location=tracking_location(dest.city, dest.state),
            )
        )
        events.append(
            ShipmentEvent(
                shipment_id=shipment.id,
                event_type=ShipmentEventType.DELIVERED.value,
                occurred_at=end_at,
                location=f"{dest.city} - {dest.state}",
                notes="Entregue ao destinatário.",
            )
        )
    elif shipment.status == ShippingStatus.RETURNED.value:
        # Delivered first, then returned.
        deliv_at = end_at - timedelta(days=rng.randint(1, 5))
        events.append(
            ShipmentEvent(
                shipment_id=shipment.id,
                event_type=ShipmentEventType.DELIVERED.value,
                occurred_at=deliv_at,
                location=f"{dest.city} - {dest.state}",
            )
        )
        events.append(
            ShipmentEvent(
                shipment_id=shipment.id,
                event_type=ShipmentEventType.RETURNED.value,
                occurred_at=end_at,
                location=tracking_location(origin.city, origin.state),
                notes="Devolvido ao remetente.",
            )
        )

    return events
