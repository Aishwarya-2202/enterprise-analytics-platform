-- =====================================================================
-- File:    01_business_views.sql
-- Purpose: Create permanent, reusable views encapsulating our core
--          business logic. Downstream consumers (Power BI, analysts,
--          Python scripts) query these views instead of re-writing
--          joins and calculations themselves.
-- =====================================================================


-- ---------------------------------------------------------------------
-- VIEW: vw_monthly_revenue
-- One row per month: revenue, transaction count, and running total.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_monthly_revenue AS
SELECT
    d.year,
    d.month,
    d.month_name,
    COUNT(*)                                          AS transaction_count,
    SUM(f.total_amount)                                AS total_revenue,
    SUM(SUM(f.total_amount)) OVER (ORDER BY d.year, d.month) AS running_total_revenue
FROM fact_sales f
JOIN dim_date d ON f.date_id = d.date_id
GROUP BY d.year, d.month, d.month_name;


-- ---------------------------------------------------------------------
-- VIEW: vw_category_performance
-- One row per category: revenue, transaction count, average sale value.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_category_performance AS
SELECT
    p.category,
    COUNT(*)                       AS transaction_count,
    SUM(f.total_amount)            AS total_revenue,
    ROUND(AVG(f.total_amount), 2)  AS avg_sale_value
FROM fact_sales f
JOIN dim_product p ON f.product_id = p.product_id
GROUP BY p.category;


-- ---------------------------------------------------------------------
-- VIEW: vw_store_performance
-- One row per store: revenue, transaction count, and rank vs other stores.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_store_performance AS
SELECT
    s.store_name,
    s.city,
    s.region,
    COUNT(*)             AS transaction_count,
    SUM(f.total_amount)  AS total_revenue,
    RANK() OVER (ORDER BY SUM(f.total_amount) DESC) AS revenue_rank
FROM fact_sales f
JOIN dim_store s ON f.store_id = s.store_id
GROUP BY s.store_name, s.city, s.region;