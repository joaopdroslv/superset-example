-- label: 13 Shipping cost by route (origin → dest state)
-- description: Average shipping cost and lead time between every origin/destination state pair (top 30 by volume).
SELECT
  o_addr.state AS origin_state,
  d_addr.state AS dest_state,
  COUNT(*) AS n_shipments,
  ROUND(AVG(s.shipping_cost), 2) AS avg_cost,
  ROUND(AVG(s.declared_weight_kg), 2) AS avg_weight_kg,
  ROUND(AVG(TIMESTAMPDIFF(HOUR, s.dispatched_at, s.delivered_at)) / 24, 2) AS avg_days
FROM shipments s
JOIN addresses o_addr ON o_addr.id = s.origin_address_id
JOIN addresses d_addr ON d_addr.id = s.dest_address_id
WHERE s.status = 'delivered'
  AND s.dispatched_at IS NOT NULL
  AND s.delivered_at IS NOT NULL
GROUP BY o_addr.state, d_addr.state
ORDER BY n_shipments DESC
LIMIT 30;
