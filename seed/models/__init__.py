"""ORM model registry.

Importing this package registers every model with `Base.metadata` so a single
`Base.metadata.create_all(engine)` call materializes the full schema.
"""

from .base import Base, TimestampMixin
from .category import Category
from .customer import Customer
from .order import Order, OrderItem
from .product import Product
from .seller import Seller

__all__ = [
    "Base",
    "TimestampMixin",
    "Category",
    "Customer",
    "Order",
    "OrderItem",
    "Product",
    "Seller",
]
