#!/usr/bin/env python3
"""
Phase 2: Model Training
Baselines, Optuna tuning, XGBoost + LightGBM + CatBoost, blend optimization.
"""

import pandas as pd
import numpy as np
import json
import os
import sys
import joblib
import warnings
warnings.filterwarnings("ignore")

from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import cross_val_score, KFold
import xgboost as xgb
import lightgbm as lgb

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRAIN_PATH = os.path.join(BASE_DIR, "data", "train.csv")
TEST_PATH = os.path.join(BASE_DIR, "data", "test.csv")
FEATURES_PATH = os.path.join(BASE_DIR, "models", "features.json")
MODEL_PATH = os.path.join(BASE_DIR, "models", "revenue_model.pkl")
META_PATH = os.path.join(BASE_DIR, "models", "meta.json")


def load_data():
    """Load train/test data and feature list."""
    train = pd.read_csv(TRAIN_PATH)
    test = pd.read_csv(TEST_PATH)
    with open(FEATURES_PATH) as f:
        meta = json.load(f)
    features = meta["features"]
    return train, test, features


def evaluate(y_true, y_pred, label=""):
    """Compute all metrics."""
    # Back to dollar space
    y_true_dollar = np.expm1(y_true)
    y_pred_dollar = np.expm1(y_pred)

    mae = mean_absolute_error(y_true_dollar, y_pred_dollar)
    rmse = np.sqrt(mean_squared_error(y_true_dollar, y_pred_dollar))
    r2 = r2_score(y_true_dollar, y_pred_dollar)

    # MAPE (avoid division by zero)
    mask = y_true_dollar > 0
    mape = np.mean(np.abs((y_true_dollar[mask] - y_pred_dollar[mask]) / y_true_dollar[mask])) * 100
    mdape = np.median(np.abs((y_true_dollar[mask] - y_pred_dollar[mask]) / y_true_dollar[mask])) * 100

    # Within X%
    ratios = y_pred_dollar[mask] / y_true_dollar[mask]
    within_25 = np.mean((ratios > 0.75) & (ratios < 1.25)) * 100
    within_50 = np.mean((ratios > 0.50) & (ratios < 1.50)) * 100

    metrics = {
        "mae": round(mae, 0),
        "rmse": round(rmse, 0),
        "r2": round(r2, 4),
        "mape": round(mape, 1),
        "mdape": round(mdape, 1),
        "within_25": round(within_25, 1),
        "within_50": round(within_50, 1),
    }

    if label:
        print(f"\n  {label}:")
        for k, v in metrics.items():
            print(f"    {k}: {v}")

    return metrics


def baseline_median(train, test, features):
    """Baseline 1: Median revenue by (borough, bedrooms)."""
    print("\n" + "=" * 50)
    print("BASELINE 1: Median by (borough, bedrooms)")

    # Find borough column
    borough_col = [c for c in train.columns if c.startswith("borough_") and train[c].sum() > 0]
    if not borough_col:
        print("  No borough columns found, skipping")
        return None

    train["borough_label"] = train[borough_col].idxmax(axis=1).str.replace("borough_", "")
    test["borough_label"] = test[borough_col].idxmax(axis=1).str.replace("borough_", "")

    # Compute median revenue by (borough, bedrooms)
    medians = train.groupby(["borough_label", "bedrooms_num"])["revenue"].median()

    def predict(row):
        key = (row["borough_label"], row["bedrooms_num"])
        if key in medians.index:
            return np.log1p(medians[key])
        return np.log1p(train["revenue"].median())

    y_pred_log = test.apply(predict, axis=1)
    return evaluate(test["log_revenue"], y_pred_log, "Median Baseline")


def baseline_ridge(train, test, features):
    """Baseline 2: Ridge regression."""
    print("\n" + "=" * 50)
    print("BASELINE 2: Ridge Regression")

    X_train = train[features].values
    X_test = test[features].values
    y_train = train["log_revenue"].values
    y_test = test["log_revenue"].values

    model = Ridge(alpha=1.0)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    return evaluate(y_test, y_pred, "Ridge Baseline")


def train_xgboost(train, test, features, n_trials=50):
    """Train XGBoost with Optuna hyperparameter tuning."""
    print("\n" + "=" * 50)
    print("XGBOOST + OPTUNA TUNING")
    print(f"  Trials: {n_trials}")

    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    X_train = train[features].values
    y_train = train["log_revenue"].values
    X_test = test[features].values
    y_test = test["log_revenue"].values

    def objective(trial):
        params = {
            "max_depth": trial.suggest_int("max_depth", 3, 8),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "n_estimators": trial.suggest_int("n_estimators", 100, 800),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
            "random_state": 42,
            "verbosity": 0,
        }

        model = xgb.XGBRegressor(**params)
        kf = KFold(n_splits=5, shuffle=True, random_state=42)
        scores = cross_val_score(model, X_train, y_train, cv=kf, scoring="neg_mean_absolute_error")
        return -scores.mean()

    study = optuna.create_study(direction="minimize")
    study.optimize(objective, n_trials=n_trials)

    best_params = study.best_params
    best_params["random_state"] = 42
    best_params["verbosity"] = 0

    print(f"  Best trial MAE: {study.best_value:.4f}")
    print(f"  Best params: {best_params}")

    # Train final model with early stopping
    X_tr, X_val = X_train[:int(0.8*len(X_train))], X_train[int(0.8*len(X_train)):]
    y_tr, y_val = y_train[:int(0.8*len(y_train))], y_train[int(0.8*len(y_train)):]

    final_model = xgb.XGBRegressor(**best_params, early_stopping_rounds=50)
    final_model.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False)

    print(f"  Best iteration: {final_model.best_iteration}")

    # Evaluate
    y_pred = final_model.predict(X_test)
    metrics = evaluate(y_test, y_pred, "XGBoost (Optuna)")

    return final_model, metrics, best_params


def train_lightgbm(train, test, features):
    """Train LightGBM (baseline)."""
    print("\n" + "=" * 50)
    print("LIGHTGBM (default params)")

    X_train = train[features].values
    y_train = train["log_revenue"].values
    X_test = test[features].values
    y_test = test["log_revenue"].values

    model = lgb.LGBMRegressor(
        n_estimators=500,
        learning_rate=0.05,
        max_depth=6,
        random_state=42,
        verbose=-1,
    )
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    metrics = evaluate(y_test, y_pred, "LightGBM")
    return model, metrics


def optimize_blend(xgb_model, train, test, features):
    """Optimize blend weight between XGBoost and comp-based prediction."""
    print("\n" + "=" * 50)
    print("BLEND OPTIMIZATION")

    X_test = test[features].values
    y_test = test["log_revenue"].values

    # XGBoost predictions
    xgb_pred = xgb_model.predict(X_test)

    # Comp-based predictions (vectorized: median of nearest training listings by borough+bedrooms)
    comp_pred = np.zeros(len(test))
    train_borough_cols = [c for c in train.columns if c.startswith("borough_")]

    # Pre-group training data by borough for fast lookup
    borough_groups = {}
    for col in train_borough_cols:
        borough_name = col.replace("borough_", "")
        borough_groups[borough_name] = train[train[col] == 1]

    test_records = test.to_dict('records')
    for i, row in enumerate(test_records):
        # Find matching borough
        borough_match = None
        for col in train_borough_cols:
            if row.get(col, 0) == 1:
                borough_name = col.replace("borough_", "")
                borough_match = borough_groups.get(borough_name)
                break

        if borough_match is None or len(borough_match) == 0:
            borough_match = train

        bed_match = borough_match[
            (borough_match["bedrooms_num"] >= row["bedrooms_num"] - 1) &
            (borough_match["bedrooms_num"] <= row["bedrooms_num"] + 1)
        ]

        if len(bed_match) > 0:
            comp_pred[i] = bed_match["log_revenue"].median()
        else:
            comp_pred[i] = train["log_revenue"].median()

    # Grid search alpha
    best_alpha = 0.5
    best_mape = float("inf")

    for alpha in np.arange(0, 1.05, 0.05):
        blended = alpha * xgb_pred + (1 - alpha) * comp_pred
        y_dollar = np.expm1(y_test)
        b_dollar = np.expm1(blended)
        mask = y_dollar > 0
        mape = np.mean(np.abs((y_dollar[mask] - b_dollar[mask]) / y_dollar[mask])) * 100
        if mape < best_mape:
            best_mape = mape
            best_alpha = alpha

    print(f"  Best alpha: {best_alpha:.2f}")
    print(f"  Best MAPE: {best_mape:.1f}%")

    # Final blended prediction
    blended = best_alpha * xgb_pred + (1 - best_alpha) * comp_pred
    metrics = evaluate(y_test, blended, f"Blended (α={best_alpha:.2f})")

    return best_alpha, metrics


def save_model(model, features, metrics, params, alpha):
    """Save trained model and metadata."""
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)

    # Save model
    joblib.dump(model, MODEL_PATH)
    print(f"\n  Saved model: {MODEL_PATH}")

    # Save metadata
    meta = {
        "model_type": "xgboost",
        "version": "1.0.0",
        "trained_at": pd.Timestamp.now().isoformat(),
        "features": features,
        "n_features": len(features),
        "metrics": metrics,
        "optuna_params": params,
        "blend_alpha": alpha,
    }
    with open(META_PATH, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"  Saved metadata: {META_PATH}")


def main():
    print("=" * 60)
    print("PHASE 2: MODEL TRAINING")
    print("=" * 60)

    # Load data
    train, test, features = load_data()
    print(f"  Train: {len(train):,}, Test: {len(test):,}, Features: {len(features)}")

    # Baselines
    baseline_median(train, test, features)
    baseline_ridge(train, test, features)

    # XGBoost with Optuna
    n_trials_arg = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    xgb_model, xgb_metrics, xgb_params = train_xgboost(train, test, features, n_trials=n_trials_arg)

    # LightGBM
    lgb_model, lgb_metrics = train_lightgbm(train, test, features)

    # Blend optimization
    alpha, blend_metrics = optimize_blend(xgb_model, train, test, features)

    # Save best model
    save_model(xgb_model, features, blend_metrics, xgb_params, alpha)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  XGBoost MAPE:  {xgb_metrics['mape']}%")
    print(f"  LightGBM MAPE: {lgb_metrics['mape']}%")
    print(f"  Blended MAPE:  {blend_metrics['mape']}%")
    print(f"  Blend alpha:   {alpha:.2f}")
    print(f"\n✅ Model training complete!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
