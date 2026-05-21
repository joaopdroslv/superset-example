-- label: 16 Split-shipping rate (monthly)
-- description: Share of orders that ended up with more than one shipment, by month.
WITH per_order AS (
  SELECT
    o.id AS order_id,
    DATE_FORMAT(o.placed_at, '%Y-%m') AS month,
    COUNT(s.id) AS n_shipments
  FROM orders o
  LEFT JOIN shipments s ON s.order_id = o.id
  WHERE o.status <> 'cancelled'
  GROUP BY o.id, DATE_FORMAT(o.placed_at, '%Y-%m')
)
SELECT
  month,
  COUNT(*) AS n_orders,
  SUM(CASE WHEN n_shipments > 1 THEN 1 ELSE 0 END) AS n_split,
  ROUND(100.0 * SUM(CASE WHEN n_shipments > 1 THEN 1 ELSE 0 END) / COUNT(*), 1) AS split_pct,
  ROUND(AVG(n_shipments), 2) AS avg_shipments_per_order
FROM per_order
GROUP BY month
ORDER BY month;
