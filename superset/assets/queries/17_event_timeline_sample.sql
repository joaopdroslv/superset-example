-- label: 17 Tracking event timeline (sample)
-- description: All events for the 5 most recent delivered shipments — gives a feel for the tracking trail (created → picked_up → in_transit → out_for_delivery → delivered).
WITH recent AS (
  SELECT id FROM shipments
  WHERE status = 'delivered'
  ORDER BY delivered_at DESC
  LIMIT 5
)
SELECT
  e.shipment_id,
  e.event_type,
  e.occurred_at,
  e.location,
  e.notes
FROM shipment_events e
JOIN recent r ON r.id = e.shipment_id
ORDER BY e.shipment_id, e.occurred_at;
