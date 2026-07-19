"""
kpis.py

Business KPI calculation functions. Each function answers one named,
standardized business question a retail executive would recognize by
name -- Revenue, Profit, Customer Lifetime Value, and (in later parts)
Growth Metrics.

This module reuses get_engine() from etl/load.py rather than
duplicating database connection logic -- a direct application of the
DRY (Don't Repeat Yourself) principle.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
sys.path.append(str(Path(__file__).resolve().parent.parent / "etl"))

import pandas as pd

from load import get_engine  # reused, not duplicated


def calculate_revenue(engine) -> pd.DataFrame:
    """
    Total revenue, transaction count, and average sale value,
    company-wide.
    """
    query = """
        SELECT
            COUNT(*)                       AS transaction_count,
            SUM(total_amount)              AS total_revenue,
            ROUND(AVG(total_amount), 2)    AS avg_sale_value
        FROM fact_sales
    """
    return pd.read_sql(query, engine)


def calculate_profit(engine) -> pd.DataFrame:
    """
    Gross profit and gross profit margin, company-wide.

    COGS (Cost of Goods Sold) is computed per sale as
    dim_product.unit_cost * fact_sales.quantity, then summed.
    Gross profit = revenue - COGS.
    Margin = gross profit / revenue, as a percentage.
    """
    query = """
        SELECT
            SUM(f.total_amount)                        AS total_revenue,
            SUM(p.unit_cost * f.quantity)               AS total_cogs,
            SUM(f.total_amount) - SUM(p.unit_cost * f.quantity)
                                                          AS gross_profit,
            ROUND(
                100.0 * (SUM(f.total_amount) - SUM(p.unit_cost * f.quantity))
                / NULLIF(SUM(f.total_amount), 0)
            , 1)                                         AS gross_margin_pct
        FROM fact_sales f
        JOIN dim_product p ON f.product_id = p.product_id
    """
    return pd.read_sql(query, engine)


def calculate_profit_by_category(engine) -> pd.DataFrame:
    """
    Gross profit and margin broken down by product category --
    reveals that high-revenue categories aren't always the most
    profitable ones.
    """
    query = """
        SELECT
            p.category,
            SUM(f.total_amount)                          AS total_revenue,
            SUM(p.unit_cost * f.quantity)                 AS total_cogs,
            SUM(f.total_amount) - SUM(p.unit_cost * f.quantity)
                                                            AS gross_profit,
            ROUND(
                100.0 * (SUM(f.total_amount) - SUM(p.unit_cost * f.quantity))
                / NULLIF(SUM(f.total_amount), 0)
            , 1)                                           AS gross_margin_pct
        FROM fact_sales f
        JOIN dim_product p ON f.product_id = p.product_id
        GROUP BY p.category
        ORDER BY gross_profit DESC
    """
    return pd.read_sql(query, engine)


def calculate_clv(engine) -> pd.DataFrame:
    """
    Historical (observed) Customer Lifetime Value per customer.

    lifespan_days is the gap between a customer's first and most
    recent purchase IN OUR OBSERVED DATA -- not necessarily their
    true full relationship with the company, since our dataset only
    covers a 3-month window. A customer who bought once in January
    and once in February has a short observed lifespan simply because
    we haven't watched them long enough yet, not because they churned.
    """
    query = """
        SELECT
            c.customer_id,
            c.customer_name,
            c.email,
            COUNT(*)                                   AS total_orders,
            SUM(f.total_amount)                         AS total_revenue,
            ROUND(AVG(f.total_amount), 2)                AS avg_order_value,
            MIN(d.full_date)                            AS first_purchase_date,
            MAX(d.full_date)                            AS last_purchase_date,
            (MAX(d.full_date) - MIN(d.full_date))       AS observed_lifespan_days
        FROM fact_sales f
        JOIN dim_customer c ON f.customer_id = c.customer_id
        JOIN dim_date d ON f.date_id = d.date_id
        GROUP BY c.customer_id, c.customer_name, c.email
        ORDER BY total_revenue DESC
    """
    return pd.read_sql(query, engine)


def calculate_customer_tiers(engine) -> pd.DataFrame:
    """
    Segment customers into four equal-sized tiers by total revenue,
    using NTILE(4) -- the same technique real loyalty programs use to
    define Platinum/Gold/Silver/Bronze groups from ranked data, rather
    than arbitrary fixed dollar thresholds.
    """
    query = """
        WITH customer_revenue AS (
            SELECT
                c.customer_id,
                c.customer_name,
                SUM(f.total_amount) AS total_revenue
            FROM fact_sales f
            JOIN dim_customer c ON f.customer_id = c.customer_id
            GROUP BY c.customer_id, c.customer_name
        )
        SELECT
            customer_name,
            total_revenue,
            NTILE(4) OVER (ORDER BY total_revenue DESC) AS revenue_tile,
            CASE NTILE(4) OVER (ORDER BY total_revenue DESC)
                WHEN 1 THEN 'Platinum'
                WHEN 2 THEN 'Gold'
                WHEN 3 THEN 'Silver'
                ELSE 'Bronze'
            END AS tier
        FROM customer_revenue
        ORDER BY total_revenue DESC
    """
    return pd.read_sql(query, engine)


def calculate_growth_metrics(engine) -> pd.DataFrame:
    """
    Month-over-month revenue growth and new customer acquisition,
    combined into a single growth view.

    "New customer" = a customer whose EARLIEST purchase across the
    entire dataset falls in that month -- derived from the data itself,
    since "new vs returning" isn't a stored fact anywhere in our schema.
    """
    query = """
        WITH monthly_revenue AS (
            SELECT
                d.year, d.month, d.month_name,
                SUM(f.total_amount) AS revenue
            FROM fact_sales f
            JOIN dim_date d ON f.date_id = d.date_id
            GROUP BY d.year, d.month, d.month_name
        ),
        first_purchase AS (
            SELECT
                c.customer_id,
                MIN(d.full_date) AS first_purchase_date
            FROM fact_sales f
            JOIN dim_customer c ON f.customer_id = c.customer_id
            JOIN dim_date d ON f.date_id = d.date_id
            GROUP BY c.customer_id
        ),
        new_customers_monthly AS (
            SELECT
                EXTRACT(YEAR FROM first_purchase_date)::int  AS year,
                EXTRACT(MONTH FROM first_purchase_date)::int AS month,
                COUNT(*) AS new_customers
            FROM first_purchase
            GROUP BY 1, 2
        )
        SELECT
            m.year,
            m.month,
            m.month_name,
            m.revenue,
            LAG(m.revenue) OVER (ORDER BY m.year, m.month) AS prev_month_revenue,
            ROUND(
                100.0 * (m.revenue - LAG(m.revenue) OVER (ORDER BY m.year, m.month))
                / NULLIF(LAG(m.revenue) OVER (ORDER BY m.year, m.month), 0)
            , 1) AS revenue_growth_pct,
            COALESCE(n.new_customers, 0) AS new_customers
        FROM monthly_revenue m
        LEFT JOIN new_customers_monthly n
            ON m.year = n.year AND m.month = n.month
        ORDER BY m.year, m.month
    """
    return pd.read_sql(query, engine)


if __name__ == "__main__":
    engine = get_engine()

    print("\n=== Revenue ===")
    print(calculate_revenue(engine).to_string(index=False))

    print("\n=== Profit (company-wide) ===")
    print(calculate_profit(engine).to_string(index=False))

    print("\n=== Profit by Category ===")
    print(calculate_profit_by_category(engine).to_string(index=False))

    print("\n=== Customer Lifetime Value (top 5) ===")
    print(calculate_clv(engine).head(5).to_string(index=False))

    print("\n=== Customer Tiers ===")
    print(calculate_customer_tiers(engine).to_string(index=False))

    print("\n=== Growth Metrics ===")
    print(calculate_growth_metrics(engine).to_string(index=False))