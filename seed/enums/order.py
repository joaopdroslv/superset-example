"""Enums backing the string columns on `models.order.Order`."""

from __future__ import annotations

from enum import Enum


class SalesChannel(str, Enum):
    """`Order.channel` — where the order originated."""

    WEB = "web"                       # browser checkout
    MOBILE_APP = "mobile_app"         # native iOS / Android app
    MARKETPLACE_API = "marketplace_api"  # external marketplace (ML, Amazon, ...) via API
    IN_STORE = "in_store"             # physical PoS
    PHONE = "phone"                   # call-center order


class OrderStatus(str, Enum):
    """`Order.status` — fulfilment lifecycle. Forward-only in practice except
    for `CANCELLED` / `REFUNDED`, which can interrupt at any point.
    """

    PLACED = "placed"          # created, awaiting payment
    PAID = "paid"              # payment confirmed
    SHIPPED = "shipped"        # handed to carrier
    DELIVERED = "delivered"    # received by customer
    CANCELLED = "cancelled"    # cancelled before fulfilment
    REFUNDED = "refunded"      # money returned post-payment


class PaymentMethod(str, Enum):
    """`Order.payment_method` — how the order was paid. Includes Brazil-specific
    rails (Pix, Boleto) because the test data is Brazil-shaped.
    """

    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    PIX = "pix"                       # BR instant transfer
    BOLETO = "boleto"                 # BR bank slip
    WIRE_TRANSFER = "wire_transfer"
    CASH = "cash"
    PAYPAL = "paypal"


class Currency(str, Enum):
    """`Order.currency` — ISO 4217 alpha codes. Extend as needed; not exhaustive
    on purpose (only the currencies the seeder will produce).
    """

    BRL = "BRL"   # Brazilian Real
    USD = "USD"   # US Dollar
    EUR = "EUR"   # Euro
    GBP = "GBP"   # British Pound
    ARS = "ARS"   # Argentine Peso
    MXN = "MXN"   # Mexican Peso
