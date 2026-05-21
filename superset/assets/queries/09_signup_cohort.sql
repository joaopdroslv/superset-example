-- label: 09 Signup cohort (monthly)
-- description: Customers and their revenue grouped by signup month. Useful as a base for retention / cohort views.
SELECT
  DATE_FORMAT(c.signup_at, '%Y-%m') AS signup_month,
  COUNT(DISTINCT c.id) AS n_customers,
  COUNT(o.id) AS n_orders,
  ROUND(SUM(o.total), 2) AS lifetime_revenue,
  ROUND(SUM(o.total) / NULLIF(COUNT(DISTINCT c.id), 0), 2) AS avg_revenue_per_customer
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.id AND o.status NOT IN ('cancelled', 'refunded')
GROUP BY DATE_FORMAT(c.signup_at, '%Y-%m')
ORDER BY signup_month;
