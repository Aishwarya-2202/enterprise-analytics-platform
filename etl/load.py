"""
load.py

The "L" in ETL. Takes the clean DataFrame produced by transform.py and
loads it into the PostgreSQL star schema built in Module 3.

The tricky part: our clean data describes each sale using NAMES
(customer name, product name, store name), but fact_sales needs
FOREIGN KEY IDs pointing to dim_customer, dim_product, dim_store, and
dim_date. This module resolves names into IDs using a "get or create"
pattern: look up whether a matching dimension row already exists; if
not, insert it and use the new ID. This makes the pipeline safe to
re-run repeatedly without creating duplicate dimension rows.
"""

import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection

# etl/load.py is run as `python etl/load.py`, which puts only the etl/
# folder on Python's import search path -- not the project root. Since
# config/config.py lives at the project root, we add it explicitly here
# so the import below works no matter which directory this is run from.
sys.path.append(str(Path(__file__).resolve().parent.parent))

from config.config import DATABASE_URL


def get_engine():
    """Create a SQLAlchemy engine using the connection URL from config.py."""
    return create_engine(DATABASE_URL)


def get_or_create_date(conn: Connection, sale_date: pd.Timestamp) -> int:
    """
    Look up date_id for this calendar date in dim_date. Insert a new
    row (with all date parts pre-computed) if it doesn't exist yet.
    """
    existing = conn.execute(
        text("SELECT date_id FROM dim_date WHERE full_date = :d"),
        {"d": sale_date.date()},
    ).fetchone()
    if existing:
        return existing.date_id

    result = conn.execute(
        text("""
            INSERT INTO dim_date (full_date, day, month, month_name,
                                   quarter, year, is_weekend)
            VALUES (:full_date, :day, :month, :month_name,
                    :quarter, :year, :is_weekend)
            RETURNING date_id
        """),
        {
            "full_date": sale_date.date(),
            "day": sale_date.day,
            "month": sale_date.month,
            "month_name": sale_date.month_name(),
            "quarter": sale_date.quarter,
            "year": sale_date.year,
            "is_weekend": sale_date.dayofweek >= 5,  # 5=Saturday, 6=Sunday
        },
    )
    return result.fetchone().date_id


def get_or_create_customer(conn: Connection, name: str, email: str) -> int:
    """Look up customer_id by email (a natural unique key); insert if new."""
    existing = conn.execute(
        text("SELECT customer_id FROM dim_customer WHERE email = :email"),
        {"email": email},
    ).fetchone()
    if existing:
        return existing.customer_id

    result = conn.execute(
        text("""
            INSERT INTO dim_customer (customer_name, email)
            VALUES (:name, :email)
            RETURNING customer_id
        """),
        {"name": name, "email": email},
    )
    return result.fetchone().customer_id


def get_or_create_product(conn: Connection, product_name: str,
                           category: str, unit_price: float) -> int:
    """
    Look up product_id by product_name; insert if new.

    NOTE on unit_cost: our raw sales data only tells us what the
    CUSTOMER paid (unit_price), not what the product actually COSTS
    the company. In a real company, cost would come from a separate
    procurement/supplier data source, not from sales transactions. As
    a placeholder until that source exists, we estimate cost as 60%
    of price. This is a deliberate simplification, not a hidden
    assumption -- flagging it clearly here is the honest approach.
    """
    existing = conn.execute(
        text("SELECT product_id FROM dim_product WHERE product_name = :name"),
        {"name": product_name},
    ).fetchone()
    if existing:
        return existing.product_id

    estimated_cost = round(unit_price * 0.60, 2)
    result = conn.execute(
        text("""
            INSERT INTO dim_product (product_name, category, unit_cost)
            VALUES (:name, :category, :unit_cost)
            RETURNING product_id
        """),
        {"name": product_name, "category": category, "unit_cost": estimated_cost},
    )
    return result.fetchone().product_id


def get_or_create_store(conn: Connection, store_name: str,
                         city: str, region: str) -> int:
    """Look up store_id by store_name; insert if new."""
    existing = conn.execute(
        text("SELECT store_id FROM dim_store WHERE store_name = :name"),
        {"name": store_name},
    ).fetchone()
    if existing:
        return existing.store_id

    result = conn.execute(
        text("""
            INSERT INTO dim_store (store_name, city, region)
            VALUES (:name, :city, :region)
            RETURNING store_id
        """),
        {"name": store_name, "city": city, "region": region},
    )
    return result.fetchone().store_id


def load(df: pd.DataFrame) -> None:
    """
    Load a clean DataFrame into the star schema.

    Runs inside a single transaction: if any row fails partway through,
    the ENTIRE load is rolled back, so we never end up with half the
    day's sales loaded and half missing.
    """
    engine = get_engine()
    rows_loaded = 0

    with engine.begin() as conn:  # begin() = one transaction, auto commit/rollback
        for _, row in df.iterrows():
            date_id = get_or_create_date(conn, row["sale_date"])
            customer_id = get_or_create_customer(
                conn, row["customer_name"], row["customer_email"]
            )
            product_id = get_or_create_product(
                conn, row["product_name"], row["category"], row["unit_price"]
            )
            store_id = get_or_create_store(
                conn, row["store_name"], row["city"], row["region"]
            )

            conn.execute(
                text("""
                    INSERT INTO fact_sales (date_id, customer_id, product_id,
                                             store_id, quantity, unit_price,
                                             total_amount)
                    VALUES (:date_id, :customer_id, :product_id, :store_id,
                            :quantity, :unit_price, :total_amount)
                """),
                {
                    "date_id": date_id,
                    "customer_id": customer_id,
                    "product_id": product_id,
                    "store_id": store_id,
                    "quantity": int(row["quantity"]),
                    "unit_price": float(row["unit_price"]),
                    "total_amount": float(row["total_amount"]),
                },
            )
            rows_loaded += 1

    print(f"[load] Successfully loaded {rows_loaded} row(s) into fact_sales.")


if __name__ == "__main__":
    from extract import extract_csv
    from transform import transform

    raw_sales = extract_csv("data/raw/sample_sales.csv")
    clean_sales = transform(raw_sales)
    load(clean_sales)