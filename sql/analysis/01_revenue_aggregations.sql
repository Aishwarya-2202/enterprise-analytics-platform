
-- ---------------------------------------------------------------------
-- Query 1: Total revenue and transaction count by product category
-- Business question: "Which category drives the most revenue?"

SELECT
    p.category,
    COUNT(*)                       AS transaction_count,
    SUM(f.total_amount)            AS total_revenue,
    ROUND(AVG(f.total_amount), 2)  AS avg_sale_value
FROM fact_sales f
JOIN dim_product p ON f.product_id = p.product_id
GROUP BY p.category
ORDER BY total_revenue DESC;


-- ---------------------------------------------------------------------
-- Query 2: Total revenue by store, region, and city
-- Business question: "Which physical stores are performing best?"
-- ---------------------------------------------------------------------
SELECT
    s.store_name,
    s.city,
    s.region,
    COUNT(*)             AS transaction_count,
    SUM(f.total_amount)  AS total_revenue
FROM fact_sales f
JOIN dim_store s ON f.store_id = s.store_id
GROUP BY s.store_name, s.city, s.region
ORDER BY total_revenue DESC;


-- ---------------------------------------------------------------------
-- Query 3: Monthly revenue trend
-- Business question: "Is revenue growing or shrinking month over month?"
-- ---------------------------------------------------------------------
SELECT
    d.year,
    d.month,
    d.month_name,
    SUM(f.total_amount) AS total_revenue
FROM fact_sales f
JOIN dim_date d ON f.date_id = d.date_id
GROUP BY d.year, d.month, d.month_name
ORDER BY d.year, d.month;


-- ---------------------------------------------------------------------
-- Query 4: High-value categories only (WHERE vs HAVING demonstration)
-- Business question: "Which categories generated over $3,000 in revenue,
-- looking only at non-weekend sales?"
-- ---------------------------------------------------------------------
SELECT
    p.category,
    SUM(f.total_amount) AS total_revenue
FROM fact_sales f
JOIN dim_product p ON f.product_id = p.product_id
JOIN dim_date d ON f.date_id = d.date_id
WHERE d.is_weekend = FALSE                 -- filters ROWS, before grouping
GROUP BY p.category
HAVING SUM(f.total_amount) > 3000           -- filters GROUPS, after aggregation
ORDER BY total_revenue DESC;