"""Enums backing the string columns on shipping models."""

from __future__ import annotations

from enum import Enum


class ShippingStatus(str, Enum):
    """`Shipment.status` — fulfillment lifecycle of a single shipment."""

    PENDING = "pending"            # created but not picked up
    DISPATCHED = "dispatched"      # picked up by the carrier
    IN_TRANSIT = "in_transit"      # moving through the carrier network
    OUT_FOR_DELIVERY = "out_for_delivery"  # last mile in progress
    DELIVERED = "delivered"        # received by the customer
    EXCEPTION = "exception"        # damaged / lost / address issue
    RETURNED = "returned"          # back at the seller / depot


class ServiceLevel(str, Enum):
    """`Shipment.service_level` — speed/price tier picked at checkout."""

    ECONOMY = "economy"            # slowest, cheapest
    STANDARD = "standard"          # default
    EXPRESS = "express"            # fast (usually 1-2 day)
    SAME_DAY = "same_day"          # metropolitan same-day


class ShipmentEventType(str, Enum):
    """`ShipmentEvent.event_type` — carrier scan / status event.

    Every successful shipment produces a chain like:
    CREATED → PICKED_UP → IN_TRANSIT → OUT_FOR_DELIVERY → DELIVERED.
    Exceptions and returns interrupt the chain.
    """

    CREATED = "created"            # shipment record opened
    PICKED_UP = "picked_up"        # carrier collected from origin
    IN_TRANSIT = "in_transit"      # scan at a distribution center
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    DELIVERY_FAILED = "delivery_failed"   # nobody home / refused
    EXCEPTION = "exception"        # damage, loss, address invalid
    RETURNED = "returned"
