-- label: 11 Gross margin by brand
-- description: Brand-level gross margin and margin percentage. Uses unit_price / unit_cost snapshots from order_items.
SELECT
  p.brand,
  COUNT(DISTINCT oi.order_id) AS n_orders,
  SUM(oi.quantity) AS units_sold,
  ROUND(SUM(oi.unit_price * oi.quantity - oi.discount_amount), 2) AS revenue,
  ROUND(SUM((oi.unit_price - oi.unit_cost) * oi.quantity - oi.discount_amount), 2) AS gross_margin,
  ROUND(100.0 * SUM((oi.unit_price - oi.unit_cost) * oi.quantity - oi.discount_amount)
              / NULLIF(SUM(oi.unit_price * oi.quantity - oi.discount_amount), 0), 2) AS margin_pct
FROM order_items oi
JOIN products p ON p.id = oi.product_id
WHERE p.brand IS NOT NULL
GROUP BY p.brand
ORDER BY gross_margin DESC
LIMIT 20;
