"""Enums backing the string columns on `models.customer.Customer`."""

from __future__ import annotations

from enum import Enum


class Gender(str, Enum):
    """`Customer.gender` — single-character code.

    `NOT_INFORMED` is distinct from NULL: NULL = "field never asked";
    NOT_INFORMED = "user was asked and declined to answer".
    """

    FEMALE = "F"
    MALE = "M"
    OTHER = "O"
    NOT_INFORMED = "N"


class CustomerSegment(str, Enum):
    """`Customer.segment` — commercial tier the buyer belongs to."""

    B2C = "B2C"           # individual consumer
    B2B = "B2B"           # business buyer
    VIP = "VIP"           # high-value individual, special perks


class AcquisitionChannel(str, Enum):
    """`Customer.acquisition_channel` — how the buyer first reached the store.
    Drives attribution and CAC reports.
    """

    ORGANIC = "organic"           # SEO, direct, word-of-mouth
    PAID_ADS = "paid_ads"         # Google/Meta/etc. ad spend
    REFERRAL = "referral"         # referral program / partner link
    SOCIAL = "social"             # unpaid social (Instagram, TikTok, ...)
    EMAIL = "email"               # newsletter / lifecycle email
    AFFILIATE = "affiliate"       # affiliate marketing
    OTHER = "other"
