"""Loads `config.yml` into a typed `Config` dataclass tree.

The default file path is `src/seed/config.yml`. Override with the
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
class ItemsPerOrder:
    min: int
    max: int


@dataclass(frozen=True)
class FreeShipping:
    threshold: Decimal
    probability: float


@dataclass(frozen=True)
class OrdersConfig:
    commit_every: int
    items_per_order: ItemsPerOrder
    tax_rate: Decimal
    free_shipping: FreeShipping
    cancellation_rate: float
    refund_rate: float
    line_discount_probability: float
    order_discount_probability: float


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


@dataclass(frozen=True)
class Config:
    random_seed: int
    counts: Counts
    orders: OrdersConfig
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
    weights_raw = raw["weights"]
    return Config(
        random_seed=int(raw["random_seed"]),
        counts=Counts(**raw["counts"]),
        orders=OrdersConfig(
            commit_every=int(orders_raw["commit_every"]),
            items_per_order=ItemsPerOrder(**orders_raw["items_per_order"]),
            tax_rate=Decimal(str(orders_raw["tax_rate"])),
            free_shipping=FreeShipping(
                threshold=Decimal(str(orders_raw["free_shipping"]["threshold"])),
                probability=float(orders_raw["free_shipping"]["probability"]),
            ),
            cancellation_rate=float(orders_raw["cancellation_rate"]),
            refund_rate=float(orders_raw["refund_rate"]),
            line_discount_probability=float(orders_raw["line_discount_probability"]),
            order_discount_probability=float(orders_raw["order_discount_probability"]),
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
        ),
    )


def _validate(cfg: Config) -> None:
    if cfg.counts.sellers < 1:
        raise ValueError("counts.sellers must be >= 1 (the first-party seller is mandatory)")
    for field in ("products", "customers", "orders"):
        if getattr(cfg.counts, field) < 0:
            raise ValueError(f"counts.{field} must be non-negative")

    ipo = cfg.orders.items_per_order
    if ipo.min < 1 or ipo.max < ipo.min:
        raise ValueError(f"orders.items_per_order: invalid range min={ipo.min} max={ipo.max}")

    for name, value in [
        ("cancellation_rate", cfg.orders.cancellation_rate),
        ("refund_rate", cfg.orders.refund_rate),
        ("free_shipping.probability", cfg.orders.free_shipping.probability),
        ("line_discount_probability", cfg.orders.line_discount_probability),
        ("order_discount_probability", cfg.orders.order_discount_probability),
    ]:
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"orders.{name} must be in [0, 1], got {value}")

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
