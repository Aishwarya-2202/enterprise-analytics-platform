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


if __name__ == "__main__":
    engine = get_engine()

    print("\n=== Revenue ===")
    print(calculate_revenue(engine).to_string(index=False))

    print("\n=== Profit (company-wide) ===")
    print(calculate_profit(engine).to_string(index=False))

    print("\n=== Profit by Category ===")
    print(calculate_profit_by_category(engine).to_string(index=False))