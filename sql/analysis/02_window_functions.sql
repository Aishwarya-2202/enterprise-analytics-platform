-- =====================================================================
-- File:    02_window_functions.sql
-- Purpose: Window function queries -- rankings, running totals, and
--          period-over-period growth -- that GROUP BY alone cannot
--          express, because they need to keep individual rows visible
--          alongside aggregate context.
-- =====================================================================


-- ---------------------------------------------------------------------
-- Query 1: Rank stores by total revenue (RANK vs DENSE_RANK comparison)
-- Business question: "Which store ranks #1? What happens with ties?"
-- ---------------------------------------------------------------------
SELECT
    s.store_name,
    SUM(f.total_amount)                                           AS total_revenue,
    RANK()       OVER (ORDER BY SUM(f.total_amount) DESC)          AS revenue_rank,
    DENSE_RANK() OVER (ORDER BY SUM(f.total_amount) DESC)          AS revenue_dense_rank
FROM fact_sales f
JOIN dim_store s ON f.store_id = s.store_id
GROUP BY s.store_name
ORDER BY total_revenue DESC;


-- ---------------------------------------------------------------------
-- Query 2: Rank products WITHIN each category by revenue (PARTITION BY)
-- Business question: "What's the top product in EACH category?"
-- ---------------------------------------------------------------------
SELECT
    category,
    product_name,
    product_revenue,
    rank_in_category
FROM (
    SELECT
        p.category,
        p.product_name,
        SUM(f.total_amount) AS product_revenue,
        RANK() OVER (
            PARTITION BY p.category
            ORDER BY SUM(f.total_amount) DESC
        ) AS rank_in_category
    FROM fact_sales f
    JOIN dim_product p ON f.product_id = p.product_id
    GROUP BY p.category, p.product_name
) ranked_products
WHERE rank_in_category = 1
ORDER BY category;


-- ---------------------------------------------------------------------
-- Query 3: Running (cumulative) monthly revenue
-- Business question: "What's our cumulative revenue as the year progresses?"
-- ---------------------------------------------------------------------
SELECT
    d.year,
    d.month,
    d.month_name,
    SUM(f.total_amount) AS monthly_revenue,
    SUM(SUM(f.total_amount)) OVER (
        ORDER BY d.year, d.month
    ) AS running_total_revenue
FROM fact_sales f
JOIN dim_date d ON f.date_id = d.date_id
GROUP BY d.year, d.month, d.month_name
ORDER BY d.year, d.month;


-- ---------------------------------------------------------------------
-- Query 4: Month-over-month revenue growth (LAG)
-- Business question: "Is revenue growing or shrinking, month to month?"
-- ---------------------------------------------------------------------
SELECT
    year,
    month,
    month_name,
    monthly_revenue,
    LAG(monthly_revenue, 1) OVER (ORDER BY year, month)      AS prev_month_revenue,
    ROUND(
        100.0 * (monthly_revenue - LAG(monthly_revenue, 1) OVER (ORDER BY year, month))
        / NULLIF(LAG(monthly_revenue, 1) OVER (ORDER BY year, month), 0)
    , 1) AS pct_change_vs_prev_month
FROM (
    SELECT
        d.year,
        d.month,
        d.month_name,
        SUM(f.total_amount) AS monthly_revenue
    FROM fact_sales f
    JOIN dim_date d ON f.date_id = d.date_id
    GROUP BY d.year, d.month, d.month_name
) monthly
ORDER BY year, month;