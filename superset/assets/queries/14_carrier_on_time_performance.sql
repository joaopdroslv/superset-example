-- label: 14 Carrier on-time performance
-- description: On-time delivery rate and average lead time per carrier. Only delivered shipments.
SELECT
  c.name AS carrier,
  c.code,
  COUNT(*) AS n_delivered,
  ROUND(100.0 * SUM(CASE WHEN s.delivered_at <= s.estimated_delivery_at THEN 1 ELSE 0 END) / COUNT(*), 1) AS on_time_pct,
  ROUND(AVG(TIMESTAMPDIFF(HOUR, s.dispatched_at, s.delivered_at)) / 24, 2) AS avg_days,
  ROUND(AVG(s.shipping_cost), 2) AS avg_cost,
  ROUND(SUM(s.shipping_cost), 2) AS revenue
FROM shipments s
JOIN shipping_carriers c ON c.id = s.carrier_id
WHERE s.status = 'delivered'
  AND s.dispatched_at IS NOT NULL
  AND s.delivered_at IS NOT NULL
GROUP BY c.id, c.name, c.code
ORDER BY n_delivered DESC;
