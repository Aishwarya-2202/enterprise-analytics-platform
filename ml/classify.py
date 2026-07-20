"""
classify.py

Classification task: predict product CATEGORY from unit_price,
quantity, region, and is_weekend. Compares RandomForestClassifier
(bagging) against XGBoost (boosting).

HONEST CAVEAT, stated upfront: our catalog only has 9 unique products,
each with a FIXED price and category. Because price so strongly
distinguishes category by product design (Furniture is expensive,
Stationery is cheap), this task is close to a lookup table given so
few distinct products -- expect very high accuracy, but recognize
it reflects our small, fixed product catalog more than a deeply
generalizable real-world pattern that would hold for new, unseen
products.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
sys.path.append(str(Path(__file__).resolve().parent.parent / "etl"))

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix
)
from xgboost import XGBClassifier

from load import get_engine


def get_classification_data(engine) -> pd.DataFrame:
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


def build_classification_features(engine):
    raw = get_classification_data(engine)
    y = raw["category"]
    X = raw.drop(columns=["category"])
    X["is_weekend"] = X["is_weekend"].astype(int)
    X = pd.get_dummies(X, columns=["region"], drop_first=True)
    return X, y


def train_and_compare(X, y):
    # stratify=y preserves each category's proportion in both splits --
    # important with a small, imbalanced dataset like ours.
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"Train size: {len(X_train)}  Test size: {len(X_test)}")
    print(f"Class distribution (full data):\n{y.value_counts()}\n")

    results = {}

    # --- Random Forest ---
    rf = RandomForestClassifier(n_estimators=100, random_state=42)
    rf.fit(X_train, y_train)
    rf_pred = rf.predict(X_test)

    print("=== Random Forest ===")
    print(f"Accuracy: {accuracy_score(y_test, rf_pred):.3f}")
    print(classification_report(y_test, rf_pred, zero_division=0))
    print("Confusion matrix (rows=actual, cols=predicted):")
    labels = sorted(y.unique())
    print(pd.DataFrame(confusion_matrix(y_test, rf_pred, labels=labels),
                        index=labels, columns=labels))
    results["random_forest"] = rf

    # --- XGBoost ---
    # XGBoost's classifier needs numeric-encoded labels, not raw strings.
    le = LabelEncoder()
    y_train_enc = le.fit_transform(y_train)
    y_test_enc = le.transform(y_test)

    xgb = XGBClassifier(n_estimators=100, random_state=42,
                         eval_metric="mlogloss")
    xgb.fit(X_train, y_train_enc)
    xgb_pred_enc = xgb.predict(X_test)
    xgb_pred = le.inverse_transform(xgb_pred_enc)

    print("\n=== XGBoost ===")
    print(f"Accuracy: {accuracy_score(y_test, xgb_pred):.3f}")
    print(classification_report(y_test, xgb_pred, zero_division=0))
    results["xgboost"] = xgb

    # --- Feature importance comparison ---
    print("\nFeature importance comparison:")
    importance_df = pd.DataFrame({
        "feature": X.columns,
        "random_forest": rf.feature_importances_,
        "xgboost": xgb.feature_importances_,
    }).sort_values("random_forest", ascending=False)
    print(importance_df.to_string(index=False))

    return results


if __name__ == "__main__":
    engine = get_engine()
    X, y = build_classification_features(engine)
    train_and_compare(X, y)