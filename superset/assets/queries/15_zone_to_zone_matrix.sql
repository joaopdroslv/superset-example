-- label: 15 Zone-to-zone shipment matrix
-- description: Counts + average cost between every pair of shipping zones. Same-zone is much cheaper than cross-zone.
SELECT
  o_zone.code AS origin_zone,
  d_zone.code AS dest_zone,
  COUNT(*) AS n_shipments,
  ROUND(AVG(s.shipping_cost), 2) AS avg_cost,
  ROUND(SUM(s.shipping_cost), 2) AS total_revenue,
  ROUND(AVG(s.declared_weight_kg), 2) AS avg_weight_kg
FROM shipments s
JOIN addresses o_addr ON o_addr.id = s.origin_address_id
JOIN addresses d_addr ON d_addr.id = s.dest_address_id
LEFT JOIN shipping_zones o_zone ON o_zone.id = o_addr.zone_id
LEFT JOIN shipping_zones d_zone ON d_zone.id = d_addr.zone_id
GROUP BY o_zone.code, d_zone.code
ORDER BY n_shipments DESC;
