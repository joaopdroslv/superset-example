-- label: 03 Top sellers by GMV
-- description: Top 10 sellers ranked by gross merchandise value, with platform-revenue (commission).
SELECT
  s.id,
  s.name,
  s.seller_type,
  COUNT(DISTINCT oi.order_id) AS n_orders,
  ROUND(SUM(oi.unit_price * oi.quantity), 2) AS gmv,
  ROUND(SUM(oi.unit_price * oi.quantity * s.commission_rate), 2) AS platform_revenue
FROM order_items oi
JOIN sellers s ON s.id = oi.seller_id
GROUP BY s.id, s.name, s.seller_type
ORDER BY gmv DESC
LIMIT 10;
