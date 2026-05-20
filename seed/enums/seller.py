"""Enums backing the string columns on `models.seller.Seller`."""

from __future__ import annotations

from enum import Enum


class SellerType(str, Enum):
    """`Seller.seller_type` — whether the seller is the store itself or a
    third-party marketplace vendor. Drives 1P vs 3P share reports.
    """

    FIRST_PARTY = "first_party"   # 1P — the platform owns inventory & fulfilment
    MARKETPLACE = "marketplace"   # 3P — independent merchant on the platform
