-- label: 08 Avg lead time paid→delivered (by state)
-- description: How long it takes from payment confirmation to delivery, grouped by shipping state. Only delivered orders.
SELECT
  ship_country AS country,
  ship_state   AS state,
  COUNT(*)     AS n_orders,
  ROUND(AVG(TIMESTAMPDIFF(HOUR, paid_at, delivered_at)) / 24.0, 2) AS avg_days_paid_to_delivered,
  ROUND(AVG(TIMESTAMPDIFF(HOUR, shipped_at, delivered_at)) / 24.0, 2) AS avg_days_shipped_to_delivered
FROM orders
WHERE status = 'delivered'
  AND paid_at IS NOT NULL
  AND shipped_at IS NOT NULL
  AND delivered_at IS NOT NULL
GROUP BY ship_country, ship_state
ORDER BY n_orders DESC;
