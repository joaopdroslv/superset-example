-- label: 02 Payment method mix
-- description: Order count and revenue per payment method (excludes cancelled / refunded).
SELECT
  payment_method,
  COUNT(*) AS n_orders,
  ROUND(SUM(total), 2) AS revenue,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_orders
FROM orders
WHERE status NOT IN ('cancelled', 'refunded')
GROUP BY payment_method
ORDER BY revenue DESC;
