"""Post-seed validation suite.

Runs integrity, reliability, and coverage checks against the seeded DB using
the SQLAlchemy models. Intended as a sanity gate after `seed.core.run`.

Run from the directory that contains the `seed/` package:
    python -m seed.core.validate

After `pip install -e seed/`, the `seed-validate` console script is equivalent.

Exit codes:
    0 — all PASS (WARN allowed; warnings are coverage gaps, not bugs)
    1 — at least one FAIL
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, Iterable, Optional

from sqlalchemy import and_, distinct, func, or_, select
from sqlalchemy.orm import Session

from ..config import CONFIG
from ..db import SessionLocal
from ..enums import (
    AcquisitionChannel,
    Currency,
    CustomerSegment,
    Gender,
    OrderStatus,
    PaymentMethod,
    SalesChannel,
    SellerType,
)
from ..models import Category, Customer, Order, OrderItem, Product, Seller


class Level(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass
class Check:
    section: str
    name: str
    level: Level
    message: str
    sample: Optional[str] = None


class Validator:
    """Accumulates check results and statistics, then prints a report.

    A *check* is a yes/no assertion (`expect_zero`, `expect_coverage`) recorded
    with a level (PASS / WARN / FAIL). A *stat* is informational (totals,
    revenue, date range). Stats are always shown; checks drive the exit code.
    """

    def __init__(self, session: Session) -> None:
        self.session = session
        self.checks: list[Check] = []
        self.stats: list[tuple[str, str]] = []

    # ------------------------------------------------------------------ API

    def expect_zero(self, section: str, name: str, violating_query) -> None:
        """PASS iff `violating_query` returns zero rows."""
        n = self._count(violating_query)
        if n == 0:
            self._record(section, name, Level.PASS, "no violations")
            return
        self._record(
            section, name, Level.FAIL, f"{n} violation(s)", self._sample(violating_query)
        )

    def expect_coverage(
        self,
        section: str,
        name: str,
        column,
        expected: Iterable,
        *,
        allow_null: bool = False,
    ) -> None:
        """All `expected` values must appear at least once in `column`.

        Missing values → WARN (coverage gap, not a bug). Values *outside*
        `expected` present in the column → FAIL (something wrote an invalid
        enum string).
        """
        present = set(self.session.scalars(select(distinct(column))).all())
        if allow_null:
            present.discard(None)
        expected_set = {v.value if hasattr(v, "value") else v for v in expected}
        missing = expected_set - present
        extra = present - expected_set
        if extra:
            self._record(
                section, name, Level.FAIL,
                f"column contains values outside the expected set: {sorted(extra)}",
            )
            return
        if missing:
            self._record(
                section, name, Level.WARN,
                f"{len(present)}/{len(expected_set)} covered — "
                f"missing: {sorted(missing)}",
            )
            return
        self._record(section, name, Level.PASS, f"{len(expected_set)} value(s) covered")

    def stat(self, label: str, value: Any) -> None:
        self.stats.append((label, str(value)))

    # ----------------------------------------------------------- internals

    def _count(self, q) -> int:
        return self.session.scalar(select(func.count()).select_from(q.subquery())) or 0

    def _sample(self, q) -> Optional[str]:
        rows = self.session.execute(q.limit(3)).all()
        return "; ".join(repr(tuple(r)) for r in rows) if rows else None

    def _record(
        self,
        section: str,
        name: str,
        level: Level,
        message: str,
        sample: Optional[str] = None,
    ) -> None:
        self.checks.append(Check(section, name, level, message, sample))

    # ---------------------------------------------------------- suites

    def run(self) -> None:
        self._integrity()
        self._reliability()
        self._coverage()
        self._stats()

    def _integrity(self) -> None:
        s = "Integrity"

        # FK referential integrity. The DB enforces these — we check anyway in
        # case rows were inserted via raw SQL bypassing the constraints.
        self.expect_zero(s, "orders.customer_id → customers.id",
                         select(Order.id).where(~Order.customer_id.in_(select(Customer.id))))
        self.expect_zero(s, "order_items.order_id → orders.id",
                         select(OrderItem.id).where(~OrderItem.order_id.in_(select(Order.id))))
        self.expect_zero(s, "order_items.product_id → products.id",
                         select(OrderItem.id).where(~OrderItem.product_id.in_(select(Product.id))))
        self.expect_zero(s, "order_items.seller_id → sellers.id",
                         select(OrderItem.id).where(~OrderItem.seller_id.in_(select(Seller.id))))
        self.expect_zero(s, "products.category_id → categories.id",
                         select(Product.id).where(~Product.category_id.in_(select(Category.id))))
        self.expect_zero(s, "products.seller_id → sellers.id",
                         select(Product.id).where(~Product.seller_id.in_(select(Seller.id))))

        # Self-referential category cannot be its own parent.
        self.expect_zero(s, "category.parent_id != category.id",
                         select(Category.id).where(Category.parent_id == Category.id))

        # Every order must have at least one line item.
        self.expect_zero(
            s, "every order has >= 1 line item",
            select(Order.id)
            .outerjoin(OrderItem, OrderItem.order_id == Order.id)
            .where(OrderItem.id.is_(None)),
        )

        # Uniqueness — DB-enforced, but verify so we catch any drift.
        self._dup(s, "customer.email unique", Customer.email)
        self._dup(s, "seller.email unique", Seller.email)
        self._dup(s, "product.sku unique", Product.sku)
        self._dup(s, "order.order_number unique", Order.order_number)

    def _dup(self, section: str, name: str, column) -> None:
        q = select(column).group_by(column).having(func.count() > 1)
        self.expect_zero(section, name, q)

    def _reliability(self) -> None:
        s = "Reliability"

        # Money decomposition: subtotal + shipping + tax - discount = total.
        # 0.02 tolerance for half-up rounding artifacts on Numeric(_, 2).
        self.expect_zero(
            s, "order: subtotal + shipping + tax - discount = total",
            select(Order.id).where(
                func.abs(
                    (Order.subtotal + Order.shipping_cost + Order.tax_amount
                     - Order.discount_amount) - Order.total
                ) > Decimal("0.02")
            ),
        )

        # Positive money / quantities.
        self.expect_zero(s, "order.total > 0",
                         select(Order.id).where(Order.total <= 0))
        self.expect_zero(s, "order.subtotal > 0",
                         select(Order.id).where(Order.subtotal <= 0))
        self.expect_zero(s, "order_item.quantity > 0",
                         select(OrderItem.id).where(OrderItem.quantity <= 0))
        self.expect_zero(s, "order_item.unit_price > 0",
                         select(OrderItem.id).where(OrderItem.unit_price <= 0))
        self.expect_zero(s, "order_item.unit_cost > 0",
                         select(OrderItem.id).where(OrderItem.unit_cost <= 0))

        # Discount caps — a discount can't make a line / order negative.
        self.expect_zero(
            s, "line discount <= line subtotal",
            select(OrderItem.id).where(
                OrderItem.discount_amount > OrderItem.unit_price * OrderItem.quantity
            ),
        )
        self.expect_zero(
            s, "order discount <= subtotal",
            select(Order.id).where(Order.discount_amount > Order.subtotal),
        )

        # Lifecycle timestamps must be monotonic when set.
        self.expect_zero(
            s, "placed_at <= paid_at",
            select(Order.id).where(
                and_(Order.paid_at.is_not(None), Order.paid_at < Order.placed_at)
            ),
        )
        self.expect_zero(
            s, "paid_at <= shipped_at",
            select(Order.id).where(
                and_(Order.shipped_at.is_not(None), Order.paid_at.is_not(None),
                     Order.shipped_at < Order.paid_at)
            ),
        )
        self.expect_zero(
            s, "shipped_at <= delivered_at",
            select(Order.id).where(
                and_(Order.delivered_at.is_not(None), Order.shipped_at.is_not(None),
                     Order.delivered_at < Order.shipped_at)
            ),
        )

        # Customer must exist before they place an order.
        self.expect_zero(
            s, "customer.signup_at <= order.placed_at",
            select(Order.id)
            .join(Customer, Customer.id == Order.customer_id)
            .where(Order.placed_at < Customer.signup_at),
        )

        # Status / timestamp consistency — see _status_consistent() for the rules.
        self._status_consistent(s, OrderStatus.PLACED, paid=False, shipped=False, delivered=False)
        self._status_consistent(s, OrderStatus.PAID, paid=True, shipped=False, delivered=False)
        self._status_consistent(s, OrderStatus.SHIPPED, paid=True, shipped=True, delivered=False)
        self._status_consistent(s, OrderStatus.DELIVERED, paid=True, shipped=True, delivered=True)
        self._status_consistent(s, OrderStatus.CANCELLED, paid=False, shipped=False, delivered=False)
        self._status_consistent(s, OrderStatus.REFUNDED, paid=True, shipped=False, delivered=False)

        # Seller-side bounds.
        self.expect_zero(
            s, "seller.commission_rate in [0, 1]",
            select(Seller.id).where(
                or_(Seller.commission_rate < 0, Seller.commission_rate > 1)
            ),
        )
        self.expect_zero(
            s, "seller.rating in [0, 5] or NULL",
            select(Seller.id).where(
                and_(Seller.rating.is_not(None),
                     or_(Seller.rating < 0, Seller.rating > 5))
            ),
        )

        # Product margin can't be negative under our seeder.
        self.expect_zero(
            s, "product.price >= product.cost",
            select(Product.id).where(Product.price < Product.cost),
        )

    def _status_consistent(
        self,
        section: str,
        status: OrderStatus,
        *,
        paid: bool,
        shipped: bool,
        delivered: bool,
    ) -> None:
        """Each boolean flag = the corresponding timestamp must be NOT NULL.

        Violation = the order has this status but the timestamp pattern
        doesn't match (e.g. status=DELIVERED but `paid_at` is NULL).
        """
        violations = [
            Order.paid_at.is_(None) if paid else Order.paid_at.is_not(None),
            Order.shipped_at.is_(None) if shipped else Order.shipped_at.is_not(None),
            Order.delivered_at.is_(None) if delivered else Order.delivered_at.is_not(None),
        ]
        self.expect_zero(
            section,
            f"status={status.value} → timestamps consistent",
            select(Order.id).where(
                and_(Order.status == status.value, or_(*violations))
            ),
        )

    def _coverage(self) -> None:
        s = "Coverage"

        self.expect_coverage(s, "Gender values present", Customer.gender, Gender, allow_null=True)
        self.expect_coverage(s, "CustomerSegment values present", Customer.segment, CustomerSegment)
        self.expect_coverage(s, "AcquisitionChannel values present", Customer.acquisition_channel, AcquisitionChannel)
        self.expect_coverage(s, "SellerType values present", Seller.seller_type, SellerType)
        self.expect_coverage(s, "OrderStatus values present", Order.status, OrderStatus)
        self.expect_coverage(s, "SalesChannel values present", Order.channel, SalesChannel)
        self.expect_coverage(s, "PaymentMethod values present", Order.payment_method, PaymentMethod)
        # Currency: seeder only emits BRL/USD → WARN about the rest is expected.
        self.expect_coverage(s, "Currency values present", Order.currency, Currency)

        # Geographic — every country configured in config.yml shows up.
        countries = list(CONFIG.weights.countries.keys())
        self.expect_coverage(s, "configured countries in customers", Customer.country, countries)
        self.expect_coverage(s, "configured countries in orders.ship_country", Order.ship_country, countries)

        # Catalog topology — no orphan branches in the tree.
        self.expect_zero(
            s, "every leaf category has >= 1 product",
            select(Category.id)
            .where(Category.parent_id.is_not(None))
            .where(~Category.id.in_(select(distinct(Product.category_id)))),
        )
        self.expect_zero(
            s, "every parent category has >= 1 child",
            select(Category.id)
            .where(Category.parent_id.is_(None))
            .where(~Category.id.in_(
                select(distinct(Category.parent_id)).where(Category.parent_id.is_not(None))
            )),
        )
        self.expect_zero(
            s, "every active seller has >= 1 product",
            select(Seller.id)
            .where(Seller.is_active.is_(True))
            .where(~Seller.id.in_(select(distinct(Product.seller_id)))),
        )

    def _stats(self) -> None:
        sess = self.session

        total_customers = sess.scalar(select(func.count()).select_from(Customer)) or 0
        total_products = sess.scalar(select(func.count()).select_from(Product)) or 0
        total_sellers = sess.scalar(select(func.count()).select_from(Seller)) or 0
        total_orders = sess.scalar(select(func.count()).select_from(Order)) or 0
        total_items = sess.scalar(select(func.count()).select_from(OrderItem)) or 0
        total_revenue = sess.scalar(select(func.coalesce(func.sum(Order.total), 0))) or Decimal(0)

        self.stat("customers", total_customers)
        self.stat("products", total_products)
        self.stat("sellers", total_sellers)
        self.stat("orders", total_orders)
        self.stat("order items", total_items)
        self.stat("revenue (sum total)", f"{total_revenue:,.2f}")

        if total_orders:
            self.stat("avg ticket", f"{total_revenue/total_orders:,.2f}")
            self.stat("avg items / order", f"{total_items/total_orders:.2f}")

        date_range = sess.execute(
            select(func.min(Order.placed_at), func.max(Order.placed_at))
        ).one()
        earliest, latest = date_range
        if earliest and latest:
            self.stat("order date range", f"{earliest:%Y-%m-%d} → {latest:%Y-%m-%d}")

        # 1P vs 3P GMV split — useful BI sanity, not a check.
        gmv_q = (
            select(
                Seller.seller_type,
                func.coalesce(func.sum(OrderItem.unit_price * OrderItem.quantity), 0),
            )
            .join(Seller, Seller.id == OrderItem.seller_id)
            .group_by(Seller.seller_type)
        )
        by_type = dict(sess.execute(gmv_q).all())
        total_gmv = sum((Decimal(v) for v in by_type.values()), Decimal(0))
        for st in (SellerType.FIRST_PARTY, SellerType.MARKETPLACE):
            v = Decimal(by_type.get(st.value, 0))
            pct = (v / total_gmv * 100) if total_gmv else Decimal(0)
            self.stat(f"GMV {st.value}", f"{v:,.2f}  ({pct:.1f}%)")

    # --------------------------------------------------------- reporting

    def report(self) -> bool:
        sections: dict[str, list[Check]] = {}
        for c in self.checks:
            sections.setdefault(c.section, []).append(c)

        max_name = max((len(c.name) for c in self.checks), default=20)

        for section, items in sections.items():
            print(f"\n=== {section.upper()} ===")
            for c in items:
                print(f"  [{c.level.value}]  {c.name.ljust(max_name)}  {c.message}")
                if c.sample:
                    print(f"          sample: {c.sample}")

        if self.stats:
            print("\n=== STATS ===")
            max_label = max(len(label) for label, _ in self.stats)
            for label, value in self.stats:
                print(f"  {label.ljust(max_label)}  {value}")

        n_pass = sum(1 for c in self.checks if c.level == Level.PASS)
        n_warn = sum(1 for c in self.checks if c.level == Level.WARN)
        n_fail = sum(1 for c in self.checks if c.level == Level.FAIL)
        print(f"\n{len(self.checks)} check(s) ran — PASS={n_pass}, WARN={n_warn}, FAIL={n_fail}")
        return n_fail == 0


def main() -> None:
    with SessionLocal() as session:
        v = Validator(session)
        v.run()
        ok = v.report()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
