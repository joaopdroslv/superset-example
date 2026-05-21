-- label: 04 Daily revenue trend
-- description: Daily order count + revenue + 7-day moving average. Last 90 days.
SELECT
  DATE(placed_at) AS day,
  COUNT(*) AS n_orders,
  ROUND(SUM(total), 2) AS revenue,
  ROUND(AVG(SUM(total)) OVER (ORDER BY DATE(placed_at) ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 2) AS revenue_7d_ma
FROM orders
WHERE placed_at >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
GROUP BY DATE(placed_at)
ORDER BY day;
