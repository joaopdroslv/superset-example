-- label: 10 Top categories by units sold
-- description: Best-selling categories by unit volume, with their gross margin.
SELECT
  cat_parent.name AS parent_category,
  cat.name        AS category,
  SUM(oi.quantity) AS units_sold,
  ROUND(SUM(oi.unit_price * oi.quantity - oi.discount_amount), 2) AS revenue,
  ROUND(SUM((oi.unit_price - oi.unit_cost) * oi.quantity - oi.discount_amount), 2) AS gross_margin
FROM order_items oi
JOIN products p   ON p.id = oi.product_id
JOIN categories cat ON cat.id = p.category_id
LEFT JOIN categories cat_parent ON cat_parent.id = cat.parent_id
GROUP BY cat_parent.name, cat.name
ORDER BY units_sold DESC
LIMIT 20;
