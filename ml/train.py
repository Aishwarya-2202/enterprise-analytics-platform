"""
train.py

Trains and evaluates a baseline regression model predicting quantity
purchased. Every real model's error is compared against a naive
baseline (always predict the average) -- a model that can't beat this
baseline hasn't actually learned anything useful from the features.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
sys.path.append(str(Path(__file__).resolve().parent.parent / "etl"))

import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.dummy import DummyRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from load import get_engine
from features import build_feature_matrix


def evaluate(y_true, y_pred, label: str) -> dict:
    """Compute and print MAE, RMSE, R-squared for a set of predictions."""
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)

    print(f"  {label}: MAE={mae:.3f}  RMSE={rmse:.3f}  R2={r2:.3f}")
    return {"mae": mae, "rmse": rmse, "r2": r2}


def train_and_evaluate(X, y, test_size: float = 0.2, random_state: int = 42):
    """
    Split data, train a Linear Regression model AND a naive baseline,
    and report both -- so the real model's performance can be judged
    honestly against "just guessing the average" rather than in isolation.
    """
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )
    print(f"Train size: {len(X_train)}  Test size: {len(X_test)}")

    # --- Naive baseline: always predict the training mean ---
    baseline = DummyRegressor(strategy="mean")
    baseline.fit(X_train, y_train)
    baseline_pred = baseline.predict(X_test)

    print("\nNaive baseline (always predicts the average quantity):")
    baseline_metrics = evaluate(y_test, baseline_pred, "Baseline")

    # --- Real model: Linear Regression ---
    model = LinearRegression()
    model.fit(X_train, y_train)

    train_pred = model.predict(X_train)
    test_pred = model.predict(X_test)

    print("\nLinear Regression:")
    train_metrics = evaluate(y_train, train_pred, "Train")
    test_metrics = evaluate(y_test, test_pred, "Test ")

    # --- Honest comparison ---
    improvement = baseline_metrics["mae"] - test_metrics["mae"]
    print(f"\nMAE improvement over naive baseline: {improvement:.3f}")
    if improvement <= 0:
        print("  -> The model did NOT beat simply guessing the average. "
              "It has not learned a useful pattern from these features.")
    elif improvement < 0.1:
        print("  -> The model barely beat the naive baseline. Treat any "
              "apparent pattern with real skepticism at this data size.")
    else:
        print("  -> The model meaningfully outperformed the naive baseline.")

    gap = test_metrics["mae"] - train_metrics["mae"]
    print(f"\nTrain vs test MAE gap: {gap:.3f} "
          f"(a large positive gap would suggest overfitting)")

    print("\nModel coefficients (Linear Regression):")
    for name, coef in zip(X.columns, model.coef_):
        print(f"  {name}: {coef:+.4f}")

    return model, test_metrics


if __name__ == "__main__":
    engine = get_engine()
    X, y = build_feature_matrix(engine)
    train_and_evaluate(X, y)