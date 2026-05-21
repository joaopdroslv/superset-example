-- label: 05 Order status distribution
-- description: How orders are spread across the lifecycle (placed → paid → shipped → delivered, plus cancelled / refunded).
SELECT
  status,
  COUNT(*) AS n_orders,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct,
  ROUND(SUM(total), 2) AS revenue
FROM orders
GROUP BY status
ORDER BY n_orders DESC;
