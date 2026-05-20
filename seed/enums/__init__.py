"""Controlled vocabularies used by the ORM models.

Every enum here mirrors a `String(...)` column on a model. The DB column itself
stays free-form (no MySQL ENUM constraint) for flexibility, but these classes
are the canonical list of valid values — the seeder pulls choices from them
and any code that compares against a known value should reference an enum
member rather than a magic string.

All enums inherit from `(str, Enum)` so members can be passed to SQLAlchemy
columns directly and compared with `==` against plain strings.
"""

from .customer import AcquisitionChannel, CustomerSegment, Gender
from .order import Currency, OrderStatus, PaymentMethod, SalesChannel
from .seller import SellerType

__all__ = [
    "AcquisitionChannel",
    "CustomerSegment",
    "Currency",
    "Gender",
    "OrderStatus",
    "PaymentMethod",
    "SalesChannel",
    "SellerType",
]
