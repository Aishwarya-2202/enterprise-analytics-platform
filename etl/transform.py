"""
transform.py

The "T" in ETL. Takes a raw DataFrame (as produced by extract.py) and
returns a clean, validated, feature-engineered DataFrame ready to be
loaded into PostgreSQL.

Every row dropped and every value fixed is counted and printed, so
the scale of any data quality issue is always visible — never silent.
"""

import pandas as pd


def clean_text_columns(df: pd.DataFrame, columns: list) -> pd.DataFrame:
    """
    Strip leading/trailing whitespace and standardize casing on the
    given text columns.

    customer_name: whitespace-stripped only (names keep their given casing).
    category: whitespace-stripped AND title-cased, so "electronics" and
    "Electronics" are treated as the same category.
    """
    df = df.copy()
    for col in columns:
        df[col] = df[col].str.strip()
    return df


def standardize_category(df: pd.DataFrame) -> pd.DataFrame:
    """
    Title-case the category column so inconsistent source casing
    (e.g. 'electronics' vs 'Electronics') doesn't create duplicate
    categories downstream.
    """
    df = df.copy()
    before = df["category"].nunique()
    df["category"] = df["category"].str.title()
    after = df["category"].nunique()
    print(f"[standardize_category] Unique categories: {before} -> {after}")
    return df


def drop_missing_price(df: pd.DataFrame) -> pd.DataFrame:
    """
    Drop rows with a missing unit_price. Price is a financial fact we
    cannot safely guess, so rather than inventing a number, we remove
    the row and report exactly how many were removed.
    """
    df = df.copy()
    missing_mask = df["unit_price"].isna()
    dropped_count = missing_mask.sum()
    if dropped_count > 0:
        print(f"[drop_missing_price] Dropping {dropped_count} row(s) "
              f"with missing unit_price.")
    return df.loc[~missing_mask].copy()


def drop_invalid_quantity(df: pd.DataFrame) -> pd.DataFrame:
    """
    Drop rows where quantity is not a positive number. This mirrors
    the CHECK (quantity > 0) constraint on fact_sales in the database
    (Module 3) — we enforce the same rule here, before the data ever
    reaches PostgreSQL, so bad rows fail clearly in the pipeline log
    instead of as a rejected INSERT later.
    """
    df = df.copy()
    invalid_mask = df["quantity"] <= 0
    dropped_count = invalid_mask.sum()
    if dropped_count > 0:
        print(f"[drop_invalid_quantity] Dropping {dropped_count} row(s) "
              f"with quantity <= 0.")
    return df.loc[~invalid_mask].copy()


def convert_date_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert sale_date from plain text to a real pandas datetime type,
    so downstream code can extract year/month/quarter and compare
    dates correctly.
    """
    df = df.copy()
    df["sale_date"] = pd.to_datetime(df["sale_date"])
    return df


def engineer_total_amount(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add a total_amount column, computed once here so every downstream
    consumer (SQL views, KPIs, dashboards) uses the same calculation.
    """
    df = df.copy()
    df["total_amount"] = df["quantity"] * df["unit_price"]
    return df


def transform(df: pd.DataFrame) -> pd.DataFrame:
    """
    Run the full transformation sequence, in order, on a raw DataFrame.
    This is the single function pipeline.py (a later lesson) will call.
    """
    starting_rows = len(df)
    print(f"[transform] Starting with {starting_rows} raw row(s).")

    df = clean_text_columns(df, columns=["customer_name", "category"])
    df = standardize_category(df)
    df = drop_missing_price(df)
    df = drop_invalid_quantity(df)
    df = convert_date_column(df)
    df = engineer_total_amount(df)

    ending_rows = len(df)
    print(f"[transform] Finished with {ending_rows} clean row(s) "
          f"({starting_rows - ending_rows} dropped total).")
    return df


if __name__ == "__main__":
    from extract import extract_csv, inspect

    raw_sales = extract_csv("data/raw/sample_sales.csv")
    clean_sales = transform(raw_sales)
    inspect(clean_sales, label="clean_sales")