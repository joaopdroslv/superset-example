"""Loads `config.yml` into a typed `Config` dataclass tree.

The default file path is `seed/config.yml`. Override with the
`SEED_CONFIG_PATH` environment variable to point at a different YAML (handy
for running a "small" or "huge" preset side by side).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional, TypeVar

import yaml

T = TypeVar("T")


@dataclass(frozen=True)
class Counts:
    sellers: int
    products: int
    customers: int
    orders: int


@dataclass(frozen=True)
class IntRange:
    min: int
    max: int


@dataclass(frozen=True)
class AddressesConfig:
    per_customer: IntRange
    per_seller: IntRange


@dataclass(frozen=True)
class FreeShipping:
    threshold: Decimal
    probability: float


@dataclass(frozen=True)
class OrdersConfig:
    commit_every: int
    items_per_order: IntRange
    tax_rate: Decimal
    free_shipping: FreeShipping
    cancellation_rate: float
    refund_rate: float
    line_discount_probability: float
    order_discount_probability: float
    alt_ship_address_probability: float


@dataclass(frozen=True)
class ShipmentCost:
    base_min: Decimal
    base_max: Decimal
    weight_factor_min: Decimal
    weight_factor_max: Decimal
    cross_zone_penalty_min: Decimal
    cross_zone_penalty_max: Decimal


@dataclass(frozen=True)
class ShipmentsConfig:
    split_shipping_probability: float
    on_time_delivery_rate: float
    events_per_shipment: IntRange
    cost: ShipmentCost


@dataclass(frozen=True)
class Weights:
    # All weight dicts preserve insertion order (Python 3.7+), so the seeder
    # output is reproducible across runs.
    countries: dict[str, int]
    customer_gender: dict[Optional[str], int]
    customer_segment: dict[str, int]
    acquisition_channel: dict[str, int]
    sales_channel: dict[str, int]
    payment_method_br: dict[str, int]
    payment_method_intl: dict[str, int]
    item_quantity: dict[int, int]
    service_level: dict[str, int]
    shipment_status: dict[str, int]


@dataclass(frozen=True)
class Config:
    random_seed: int
    counts: Counts
    addresses: AddressesConfig
    orders: OrdersConfig
    shipments: ShipmentsConfig
    weights: Weights


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def _default_path() -> Path:
    override = os.environ.get("SEED_CONFIG_PATH")
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parent / "config.yml"


def load(path: Optional[Path] = None) -> Config:
    """Parse and validate the YAML file at `path` (or the default location)."""
    cfg_path = path or _default_path()
    with open(cfg_path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    cfg = _build(raw)
    _validate(cfg)
    return cfg


def _build(raw: dict[str, Any]) -> Config:
    orders_raw = raw["orders"]
    addresses_raw = raw["addresses"]
    shipments_raw = raw["shipments"]
    weights_raw = raw["weights"]
    cost_raw = shipments_raw["cost"]
    return Config(
        random_seed=int(raw["random_seed"]),
        counts=Counts(**raw["counts"]),
        addresses=AddressesConfig(
            per_customer=IntRange(**addresses_raw["per_customer"]),
            per_seller=IntRange(**addresses_raw["per_seller"]),
        ),
        orders=OrdersConfig(
            commit_every=int(orders_raw["commit_every"]),
            items_per_order=IntRange(**orders_raw["items_per_order"]),
            tax_rate=Decimal(str(orders_raw["tax_rate"])),
            free_shipping=FreeShipping(
                threshold=Decimal(str(orders_raw["free_shipping"]["threshold"])),
                probability=float(orders_raw["free_shipping"]["probability"]),
            ),
            cancellation_rate=float(orders_raw["cancellation_rate"]),
            refund_rate=float(orders_raw["refund_rate"]),
            line_discount_probability=float(orders_raw["line_discount_probability"]),
            order_discount_probability=float(orders_raw["order_discount_probability"]),
            alt_ship_address_probability=float(orders_raw["alt_ship_address_probability"]),
        ),
        shipments=ShipmentsConfig(
            split_shipping_probability=float(shipments_raw["split_shipping_probability"]),
            on_time_delivery_rate=float(shipments_raw["on_time_delivery_rate"]),
            events_per_shipment=IntRange(**shipments_raw["events_per_shipment"]),
            cost=ShipmentCost(
                base_min=Decimal(str(cost_raw["base_min"])),
                base_max=Decimal(str(cost_raw["base_max"])),
                weight_factor_min=Decimal(str(cost_raw["weight_factor_min"])),
                weight_factor_max=Decimal(str(cost_raw["weight_factor_max"])),
                cross_zone_penalty_min=Decimal(str(cost_raw["cross_zone_penalty_min"])),
                cross_zone_penalty_max=Decimal(str(cost_raw["cross_zone_penalty_max"])),
            ),
        ),
        weights=Weights(
            countries=dict(weights_raw["countries"]),
            customer_gender=dict(weights_raw["customer_gender"]),
            customer_segment=dict(weights_raw["customer_segment"]),
            acquisition_channel=dict(weights_raw["acquisition_channel"]),
            sales_channel=dict(weights_raw["sales_channel"]),
            payment_method_br=dict(weights_raw["payment_method_br"]),
            payment_method_intl=dict(weights_raw["payment_method_intl"]),
            item_quantity={int(k): int(v) for k, v in weights_raw["item_quantity"].items()},
            service_level=dict(weights_raw["service_level"]),
            shipment_status=dict(weights_raw["shipment_status"]),
        ),
    )


def _validate(cfg: Config) -> None:
    if cfg.counts.sellers < 1:
        raise ValueError("counts.sellers must be >= 1 (the first-party seller is mandatory)")
    for field in ("products", "customers", "orders"):
        if getattr(cfg.counts, field) < 0:
            raise ValueError(f"counts.{field} must be non-negative")

    for label, rng in (
        ("orders.items_per_order", cfg.orders.items_per_order),
        ("shipments.events_per_shipment", cfg.shipments.events_per_shipment),
    ):
        if rng.min < 1 or rng.max < rng.min:
            raise ValueError(f"{label}: invalid range min={rng.min} max={rng.max}")
    for label, rng in (
        ("addresses.per_customer", cfg.addresses.per_customer),
        ("addresses.per_seller", cfg.addresses.per_seller),
    ):
        if rng.min < 0 or rng.max < rng.min:
            raise ValueError(f"{label}: invalid range min={rng.min} max={rng.max}")

    probs = [
        ("orders.cancellation_rate", cfg.orders.cancellation_rate),
        ("orders.refund_rate", cfg.orders.refund_rate),
        ("orders.free_shipping.probability", cfg.orders.free_shipping.probability),
        ("orders.line_discount_probability", cfg.orders.line_discount_probability),
        ("orders.order_discount_probability", cfg.orders.order_discount_probability),
        ("orders.alt_ship_address_probability", cfg.orders.alt_ship_address_probability),
        ("shipments.split_shipping_probability", cfg.shipments.split_shipping_probability),
        ("shipments.on_time_delivery_rate", cfg.shipments.on_time_delivery_rate),
    ]
    for name, value in probs:
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{name} must be in [0, 1], got {value}")

    if cfg.orders.cancellation_rate + cfg.orders.refund_rate > 1.0:
        raise ValueError("orders.cancellation_rate + orders.refund_rate must be <= 1")

    for label, weights in (
        ("countries", cfg.weights.countries),
        ("customer_gender", cfg.weights.customer_gender),
        ("customer_segment", cfg.weights.customer_segment),
        ("acquisition_channel", cfg.weights.acquisition_channel),
        ("sales_channel", cfg.weights.sales_channel),
        ("payment_method_br", cfg.weights.payment_method_br),
        ("payment_method_intl", cfg.weights.payment_method_intl),
        ("item_quantity", cfg.weights.item_quantity),
        ("service_level", cfg.weights.service_level),
        ("shipment_status", cfg.weights.shipment_status),
    ):
        if not weights:
            raise ValueError(f"weights.{label} must contain at least one entry")
        if any(w < 0 for w in weights.values()):
            raise ValueError(f"weights.{label}: weights must be non-negative")
        if sum(weights.values()) == 0:
            raise ValueError(f"weights.{label}: at least one weight must be > 0")


# Eager-loaded singleton. If `config.yml` is missing or malformed, every
# seeder import fails loudly — which is the behavior we want.
CONFIG: Config = load()
