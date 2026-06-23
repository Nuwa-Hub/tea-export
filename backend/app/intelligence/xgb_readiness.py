"""
XGBoost Export-Readiness model + Explainable AI (TreeSHAP).

The diagram calls for the Export Readiness Index to be produced by XGBoost and
explained with SHAP. Here we:

  1. Build a supervised dataset: for each historical month, engineer features
     (processing.pipeline) and label it with the *realized* ERI over the next
     H_FORWARD months (computed from actual future values via readiness.py).
  2. Train an XGBRegressor to predict that readiness from current conditions.
  3. Explain any prediction with exact per-feature contributions using XGBoost's
     native TreeSHAP (`pred_contribs=True`) — no separate `shap` dependency.

This complements the closed-form ERI: the index stays the ground truth, while the
XGBoost model gives a learned, explainable estimate of it.
"""
from __future__ import annotations

import numpy as np

from ..config import XGB_PATH
from ..processing import pipeline
from . import explain, readiness

H_FORWARD = 6           # months of look-ahead the readiness label summarises


# --------------------------------------------------------------------------- #
# Build the supervised dataset
# --------------------------------------------------------------------------- #
def _build_training_set(df):
    """Return (X features, y realized-ERI) over months with a full forward window."""
    feats, idxs = pipeline.engineer_features(df)
    price = df["auction_price_usd"].to_numpy(dtype="float64")
    volume = df["export_volume_kg"].to_numpy(dtype="float64")
    fx = df["usd_lkr"].to_numpy(dtype="float64")

    rows, targets = [], []
    for row_pos, t in enumerate(idxs):
        if t + H_FORWARD >= len(df):
            continue                                    # no full future window
        fut = slice(t + 1, t + 1 + H_FORWARD)
        eri = readiness.compute_readiness(
            price_hist=price[: t + 1], price_fc=price[fut],
            volume_hist=volume[: t + 1], volume_fc=volume[fut],
            fx_hist=fx[: t + 1], fx_fc=fx[fut],
        )["eri"]
        rows.append(feats.iloc[row_pos].to_dict())
        targets.append(eri)

    import pandas as pd
    return pd.DataFrame(rows, columns=pipeline.FEATURE_NAMES), np.asarray(targets, dtype="float64")


# --------------------------------------------------------------------------- #
# Train / persist
# --------------------------------------------------------------------------- #
def train(df) -> dict:
    """Fit the XGBoost readiness model and save it. Returns training metadata."""
    from xgboost import XGBRegressor

    X, y = _build_training_set(df)
    model = XGBRegressor(
        n_estimators=200,
        max_depth=3,
        learning_rate=0.08,
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=42,
        objective="reg:squarederror",
    )
    model.fit(X, y)

    XGB_PATH.parent.mkdir(parents=True, exist_ok=True)
    model.save_model(XGB_PATH)

    pred = model.predict(X)
    rmse = float(np.sqrt(np.mean((pred - y) ** 2)))
    return {
        "n_samples": int(len(y)),
        "n_features": len(pipeline.FEATURE_NAMES),
        "train_rmse": round(rmse, 3),
        "look_ahead_months": H_FORWARD,
    }


def model_exists() -> bool:
    return XGB_PATH.exists()


def _load():
    from xgboost import XGBRegressor

    model = XGBRegressor()
    model.load_model(XGB_PATH)
    return model


# --------------------------------------------------------------------------- #
# Predict + explain (TreeSHAP)
# --------------------------------------------------------------------------- #
def predict_with_shap(df) -> dict:
    """
    Predict readiness for the latest month and explain it with TreeSHAP.

    Returns: predicted_eri, base value, and a sorted per-feature contribution
    breakdown (the "why").
    """
    import xgboost as xgb

    model = _load()
    X = pipeline.latest_features(df)

    booster = model.get_booster()
    dmatrix = xgb.DMatrix(X, feature_names=pipeline.FEATURE_NAMES)
    contribs = booster.predict(dmatrix, pred_contribs=True)[0]   # len = n_features + 1
    per_feature = contribs[:-1]
    base = float(contribs[-1])
    predicted = float(base + per_feature.sum())

    items = explain.breakdown(pipeline.FEATURE_NAMES, per_feature, pipeline.FEATURE_LABELS)
    return {
        "predicted_eri": round(max(0.0, min(100.0, predicted)), 1),
        "base_value": round(base, 1),
        "feature_values": {k: round(float(v), 3) for k, v in X.iloc[0].to_dict().items()},
        "contributions": items,
    }
