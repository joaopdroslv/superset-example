-- label: 12 Top 20 customers by lifetime value
-- description: Highest-spending customers, their order count, and average ticket.
SELECT
  c.id,
  CONCAT(c.first_name, ' ', c.last_name) AS customer,
  c.country,
  c.state,
  c.segment,
  COUNT(o.id) AS n_orders,
  ROUND(SUM(o.total), 2) AS lifetime_value,
  ROUND(AVG(o.total), 2) AS avg_ticket
FROM customers c
JOIN orders o ON o.customer_id = c.id
WHERE o.status NOT IN ('cancelled', 'refunded')
GROUP BY c.id, c.first_name, c.last_name, c.country, c.state, c.segment
ORDER BY lifetime_value DESC
LIMIT 20;
