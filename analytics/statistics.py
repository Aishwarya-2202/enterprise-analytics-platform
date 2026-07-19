"""
statistics.py

Statistical analysis functions: correlation, hypothesis testing, trend
analysis, and (in later parts) regression and time series decomposition.

Every result here reports BOTH the statistic and, where applicable,
its significance -- a coefficient without a significance check can be
noise dressed up as a finding.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
sys.path.append(str(Path(__file__).resolve().parent.parent / "etl"))

import pandas as pd
from scipy import stats

from load import get_engine


def get_sales_detail(engine) -> pd.DataFrame:
    """
    Pull row-level sales data (not aggregated) -- correlation and
    hypothesis testing need individual observations, not summaries.
    """
    query = """
        SELECT
            f.sale_id,
            f.quantity,
            f.unit_price,
            f.total_amount,
            d.full_date,
            d.is_weekend,
            p.category,
            s.region
        FROM fact_sales f
        JOIN dim_date d ON f.date_id = d.date_id
        JOIN dim_product p ON f.product_id = p.product_id
        JOIN dim_store s ON f.store_id = s.store_id
    """
    return pd.read_sql(query, engine)


def quantity_price_correlation(df: pd.DataFrame) -> None:
    """
    Test whether quantity purchased and unit price are correlated --
    a common retail question: do customers buy MORE of cheaper items,
    and LESS of expensive ones, in a single transaction?
    """
    r, p_value = stats.pearsonr(df["unit_price"], df["quantity"])

    print(f"\nCorrelation: unit_price vs quantity")
    print(f"  r = {r:.3f}")
    print(f"  p-value = {p_value:.4f}")

    if p_value < 0.05:
        direction = "negative" if r < 0 else "positive"
        print(f"  -> Statistically significant {direction} relationship.")
    else:
        print(f"  -> Not statistically significant at the 0.05 level; "
              f"could plausibly be due to chance.")

    print("  IMPORTANT: correlation does not imply causation. This does "
          "not prove price CAUSES quantity changes -- only that they "
          "move together (or don't) in this data.")


def full_correlation_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """
    Correlation matrix across all numeric sale-level columns at once --
    a fast way to scan for any relationships worth investigating further.
    """
    numeric_cols = df[["quantity", "unit_price", "total_amount"]]
    return numeric_cols.corr(method="pearson").round(3)


if __name__ == "__main__":
    engine = get_engine()
    sales = get_sales_detail(engine)
    print(f"Loaded {len(sales)} row-level sales for analysis.")

    quantity_price_correlation(sales)

    print("\nFull correlation matrix:")
    print(full_correlation_matrix(sales))