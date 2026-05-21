-- label: 06 AOV by acquisition channel
-- description: Average order value and customer count, sliced by how the customer was acquired.
SELECT
  c.acquisition_channel,
  COUNT(DISTINCT c.id) AS n_customers,
  COUNT(o.id) AS n_orders,
  ROUND(AVG(o.total), 2) AS aov,
  ROUND(SUM(o.total), 2) AS revenue
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.id AND o.status NOT IN ('cancelled', 'refunded')
GROUP BY c.acquisition_channel
ORDER BY revenue DESC;
