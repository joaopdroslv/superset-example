"""ORM model registry.

Importing this package registers every model with `Base.metadata` so a single
`Base.metadata.create_all(engine)` call materializes the full schema.
"""

from .address import Address
from .base import Base, TimestampMixin
from .category import Category
from .customer import Customer
from .order import Order, OrderItem
from .product import Product
from .seller import Seller
from .shipment import Shipment, ShipmentEvent
from .shipping import ShippingCarrier, ShippingZone

__all__ = [
    "Base",
    "TimestampMixin",
    "Address",
    "Category",
    "Customer",
    "Order",
    "OrderItem",
    "Product",
    "Seller",
    "Shipment",
    "ShipmentEvent",
    "ShippingCarrier",
    "ShippingZone",
]
