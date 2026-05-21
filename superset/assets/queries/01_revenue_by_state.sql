-- label: 01 Revenue by state
-- description: Total order value grouped by shipping-address state. Top 20.
SELECT
  ship_country  AS country,
  ship_state    AS state,
  COUNT(*)      AS n_orders,
  ROUND(SUM(total), 2)  AS revenue
FROM orders
WHERE status NOT IN ('cancelled', 'refunded')
GROUP BY ship_country, ship_state
ORDER BY revenue DESC
LIMIT 20;
