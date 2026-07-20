"""
features.py

Builds the feature matrix (X) and target (y) used by every model in
Module 8. Prediction target: quantity purchased in a transaction.

DATA LEAKAGE RULE: total_amount is EXCLUDED from features, because
total_amount = quantity * unit_price -- using it to predict quantity
would let the model "cheat" via algebra instead of learning a real
pattern. Any feature must be something genuinely knowable BEFORE the
outcome (quantity) is decided.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
sys.path.append(str(Path(__file__).resolve().parent.parent / "etl"))

import pandas as pd

from load import get_engine


def get_raw_features(engine) -> pd.DataFrame:
    """
    Pull transaction-level data with only features that are genuinely
    knowable in advance -- explicitly NOT including total_amount.
    """
    query = """
        SELECT
            f.quantity,
            f.unit_price,
            p.category,
            s.region,
            d.is_weekend
        FROM fact_sales f
        JOIN dim_product p ON f.product_id = p.product_id
        JOIN dim_store s ON f.store_id = s.store_id
        JOIN dim_date d ON f.date_id = d.date_id
    """
    return pd.read_sql(query, engine)


def build_feature_matrix(engine):
    """
    Returns (X, y):
      X - one-hot encoded, model-ready feature DataFrame
      y - the target Series (quantity)
    """
    raw = get_raw_features(engine)

    y = raw["quantity"]
    X = raw.drop(columns=["quantity"])

    # is_weekend is already boolean; convert to 0/1 for the model.
    X["is_weekend"] = X["is_weekend"].astype(int)

    # One-hot encode the categorical columns. drop_first=True drops one
    # category per column to avoid redundant, perfectly-correlated
    # columns (e.g. if you know category is NOT Electronics and NOT
    # Furniture, you already know it must be Stationery -- keeping all
    # three would be redundant information, a problem called the
    # "dummy variable trap").
    X = pd.get_dummies(X, columns=["category", "region"], drop_first=True)

    return X, y


if __name__ == "__main__":
    engine = get_engine()
    X, y = build_feature_matrix(engine)

    print(f"Feature matrix shape: {X.shape}")
    print(f"Target shape: {y.shape}")
    print("\nFeature columns:")
    print(list(X.columns))
    print("\nFirst 5 rows of X:")
    print(X.head())
    print("\nFirst 5 values of y:")
    print(y.head().tolist())