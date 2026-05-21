-- label: 07 First-party vs marketplace share
-- description: GMV split between 1P (the store itself) and 3P (marketplace vendors), with platform-revenue from commissions.
SELECT
  s.seller_type,
  COUNT(DISTINCT oi.order_id) AS n_orders,
  COUNT(*) AS n_lines,
  ROUND(SUM(oi.unit_price * oi.quantity), 2) AS gmv,
  ROUND(SUM(oi.unit_price * oi.quantity * s.commission_rate), 2) AS platform_revenue,
  ROUND(100.0 * SUM(oi.unit_price * oi.quantity) / SUM(SUM(oi.unit_price * oi.quantity)) OVER (), 2) AS pct_of_gmv
FROM order_items oi
JOIN sellers s ON s.id = oi.seller_id
GROUP BY s.seller_type;
