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
import statsmodels.api as sm
from scipy import stats
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.arima.model import ARIMA

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


def get_daily_revenue(engine) -> pd.DataFrame:
    """One row per calendar day with that day's total revenue."""
    query = """
        SELECT d.full_date, SUM(f.total_amount) AS daily_revenue
        FROM fact_sales f
        JOIN dim_date d ON f.date_id = d.date_id
        GROUP BY d.full_date
        ORDER BY d.full_date
    """
    return pd.read_sql(query, engine)


def trend_regression(daily_df: pd.DataFrame):
    """
    Fit revenue = intercept + slope * day_index using OLS, to quantify
    whether revenue is trending up, down, or flat -- using ALL days at
    once, not just comparing two endpoints.
    """
    daily_df = daily_df.copy()
    daily_df["day_index"] = range(len(daily_df))  # 0, 1, 2, ... one per day

    X = sm.add_constant(daily_df["day_index"])  # adds the intercept term
    y = daily_df["daily_revenue"]
    model = sm.OLS(y, X).fit()

    slope = model.params["day_index"]
    p_value = model.pvalues["day_index"]
    r_squared = model.rsquared

    print("\nTrend regression: daily_revenue ~ day_index")
    print(f"  Slope = ${slope:.2f} per day")
    print(f"  p-value on slope = {p_value:.4f}")
    print(f"  R-squared = {r_squared:.3f}")

    if p_value < 0.05:
        direction = "upward" if slope > 0 else "downward"
        print(f"  -> Statistically significant {direction} trend.")
    else:
        print(f"  -> No statistically significant trend detected; "
              f"day-to-day revenue could plausibly be flat, with the "
              f"apparent slope just being noise.")

    print(f"  R-squared of {r_squared:.3f} means the trend line explains "
          f"about {r_squared*100:.0f}% of day-to-day revenue variation -- "
          f"the rest is other factors (daily randomness, specific sales mix).")

    return model


def day_of_week_pattern(daily_df: pd.DataFrame) -> pd.DataFrame:
    """
    Average revenue by day of week. With ~90 days of data, each weekday
    has roughly 12-13 observations -- enough for a reasonable initial
    look at WEEKLY patterns.

    IMPORTANT LIMITATION: this says nothing reliable about QUARTERLY or
    YEARLY seasonality (e.g. holiday spikes) -- detecting a yearly cycle
    requires observing multiple actual years, which we don't have. We
    are deliberately NOT claiming anything about that longer cycle here.
    """
    daily_df = daily_df.copy()
    daily_df["day_of_week"] = pd.to_datetime(daily_df["full_date"]).dt.day_name()

    pattern = (
        daily_df.groupby("day_of_week")["daily_revenue"]
        .agg(["mean", "count"])
        .round(2)
        .rename(columns={"mean": "avg_daily_revenue", "count": "num_days_observed"})
    )
    # Order Monday -> Sunday instead of alphabetical
    weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday",
                      "Friday", "Saturday", "Sunday"]
    return pattern.reindex(weekday_order)


def fill_date_gaps(daily_df: pd.DataFrame) -> pd.DataFrame:
    """
    Reindex to include EVERY calendar day in the observed range,
    filling days with no sales as $0 revenue.

    Time series methods like ARIMA assume evenly-spaced observations.
    Silently dropping zero-revenue days (as a plain SQL GROUP BY does,
    since it only returns days that actually appear in fact_sales)
    would corrupt the time ordering the model depends on.
    """
    daily_df = daily_df.copy()
    daily_df["full_date"] = pd.to_datetime(daily_df["full_date"])
    daily_df = daily_df.set_index("full_date")

    full_range = pd.date_range(daily_df.index.min(), daily_df.index.max(), freq="D")
    missing_days = len(full_range) - len(daily_df)
    if missing_days > 0:
        print(f"[fill_date_gaps] Filling {missing_days} zero-sales day(s) "
              f"into the series.")

    daily_df = daily_df.reindex(full_range, fill_value=0)
    return daily_df.rename_axis("full_date").reset_index()


def check_stationarity(daily_df: pd.DataFrame) -> None:
    """
    Augmented Dickey-Fuller test: is the daily revenue series stationary?
    H0: the series is NON-stationary (has a unit root / trend).
    A small p-value lets us reject H0 and treat the series as stationary.
    """
    result = adfuller(daily_df["daily_revenue"])
    adf_stat, p_value = result[0], result[1]

    print("\nAugmented Dickey-Fuller stationarity test")
    print(f"  ADF statistic = {adf_stat:.3f}")
    print(f"  p-value = {p_value:.4f}")
    if p_value < 0.05:
        print("  -> Reject H0: series looks stationary. Consistent with "
              "Part 3's finding of no significant trend.")
    else:
        print("  -> Fail to reject H0: series may be non-stationary; "
              "differencing (the 'I' in ARIMA) would help.")


def forecast_revenue(daily_df: pd.DataFrame, steps: int = 14, order=(1, 1, 1)):
    """
    Fit ARIMA(p,d,q) on daily revenue and forecast `steps` days ahead,
    with 95% confidence intervals.

    order=(1,1,1) is a simple, defensible starting choice given our
    short series -- d=1 differences the data once (handles any mild
    trend), p=1 and q=1 keep the model simple, appropriate for only
    ~90 observations. A longer series would justify a more careful,
    data-driven order selection (ACF/PACF analysis), flagged here as
    a natural next step rather than something worth over-engineering
    on this little data.
    """
    series = daily_df.set_index(pd.to_datetime(daily_df["full_date"]))["daily_revenue"]
    series = series.asfreq("D")  # explicit daily frequency -- removes ambiguity

    model = ARIMA(series, order=order)
    fitted = model.fit()

    forecast_result = fitted.get_forecast(steps=steps)
    forecast_mean = forecast_result.predicted_mean
    conf_int = forecast_result.conf_int(alpha=0.05)  # 95% CI

    print(f"\nARIMA{order} forecast, {steps} days ahead")
    print(f"  Historical daily average: ${series.mean():.2f}")
    print(f"  Forecasted average over next {steps} days: "
          f"${forecast_mean.mean():.2f}")
    print(f"  95% CI width on first forecast day: "
          f"${conf_int.iloc[0, 1] - conf_int.iloc[0, 0]:.2f}")
    print("  A wide confidence interval here is EXPECTED and CORRECT, "
          "given only ~90 days of noisy, trend-less history -- it "
          "reflects genuine uncertainty, not a modeling mistake.")

    return series, forecast_mean, conf_int


if __name__ == "__main__":
    engine = get_engine()
    sales = get_sales_detail(engine)
    print(f"Loaded {len(sales)} row-level sales for analysis.")

    quantity_price_correlation(sales)

    print("\nFull correlation matrix:")
    print(full_correlation_matrix(sales))

    weekend_vs_weekday_test(sales)

    daily_revenue = get_daily_revenue(engine)
    daily_revenue = fill_date_gaps(daily_revenue)
    trend_regression(daily_revenue)

    print("\nAverage revenue by day of week:")
    print(day_of_week_pattern(daily_revenue))

    check_stationarity(daily_revenue)
    series, forecast_mean, conf_int = forecast_revenue(daily_revenue)