-- =====================================================================
-- File:    03_ctes.sql
-- Purpose: Demonstrate Common Table Expressions (WITH clauses) as a
--          more readable alternative to nested subqueries, and show
--          how a single CTE can be referenced multiple times.
-- =====================================================================


-- ---------------------------------------------------------------------
-- Query 1: Top product per category, rewritten with a CTE
-- Compare this structure to Part 2's Query 2 (same result, clearer steps).
-- ---------------------------------------------------------------------
WITH product_revenue AS (
    -- Step 1: compute revenue and rank per product, within each category
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
)
-- Step 2: keep only the #1 ranked product per category
SELECT category, product_name, product_revenue
FROM product_revenue
WHERE rank_in_category = 1
ORDER BY category;


-- ---------------------------------------------------------------------
-- Query 2: Monthly revenue used TWICE from a single CTE
-- Business question: show each month's revenue, its running total, AND
-- its share of the full quarter -- three different uses of the same
-- underlying monthly_revenue calculation, computed only once.
-- ---------------------------------------------------------------------
WITH monthly_revenue AS (
    SELECT
        d.year,
        d.month,
        d.month_name,
        SUM(f.total_amount) AS revenue
    FROM fact_sales f
    JOIN dim_date d ON f.date_id = d.date_id
    GROUP BY d.year, d.month, d.month_name
),
quarter_total AS (
    -- A second CTE, built on top of the first -- CTEs can chain.
    SELECT SUM(revenue) AS total FROM monthly_revenue
)
SELECT
    m.month_name,
    m.revenue,
    SUM(m.revenue) OVER (ORDER BY m.year, m.month) AS running_total,
    ROUND(100.0 * m.revenue / q.total, 1) AS pct_of_quarter
FROM monthly_revenue m
CROSS JOIN quarter_total q       -- q.total is one row, joined onto every month
ORDER BY m.year, m.month;