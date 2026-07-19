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


def weekend_vs_weekday_test(df: pd.DataFrame, alpha: float = 0.05) -> None:
    """
    Independent-samples t-test (Welch's, not assuming equal variance):
    is average sale value different on weekends vs weekdays?

    H0 (null): mean total_amount is the same on weekends and weekdays.
    H1 (alt):  mean total_amount is different between the two groups.

    alpha is decided BEFORE looking at the result -- 0.05 here, a
    conventional but not universal choice.
    """
    weekday_sales = df.loc[df["is_weekend"] == False, "total_amount"]
    weekend_sales = df.loc[df["is_weekend"] == True, "total_amount"]

    t_stat, p_value = stats.ttest_ind(weekday_sales, weekend_sales, equal_var=False)

    print("\nHypothesis test: weekday vs weekend average sale value")
    print(f"  H0: no difference in mean sale value")
    print(f"  H1: mean sale value differs between weekday and weekend")
    print(f"  Weekday: n={len(weekday_sales)}, mean=${weekday_sales.mean():.2f}")
    print(f"  Weekend: n={len(weekend_sales)}, mean=${weekend_sales.mean():.2f}")
    print(f"  t-statistic = {t_stat:.3f}")
    print(f"  p-value = {p_value:.4f}  (alpha = {alpha})")

    if p_value < alpha:
        print(f"  -> p < alpha: reject H0. The difference is statistically "
              f"significant at the {alpha} level.")
    else:
        print(f"  -> p >= alpha: fail to reject H0. Not enough evidence "
              f"of a real difference -- could plausibly be due to chance.")

    print("  Note: 'fail to reject H0' is NOT the same as 'proving H0 true' "
          "-- it just means this data didn't provide strong enough evidence "
          "against it.")


if __name__ == "__main__":
    engine = get_engine()
    sales = get_sales_detail(engine)
    print(f"Loaded {len(sales)} row-level sales for analysis.")

    quantity_price_correlation(sales)

    print("\nFull correlation matrix:")
    print(full_correlation_matrix(sales))

    weekend_vs_weekday_test(sales)