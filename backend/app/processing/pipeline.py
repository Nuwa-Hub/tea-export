"""
Data processing pipeline (the diagram's "Data Processing" box).

    raw national CSV
      -> clean()                 fill gaps, clip impossible values
      -> derive_storage_risk()   humidity/inventory-driven 0-100 risk index
      -> engineer_features()     momentum / volatility / seasonality features

`build_national()` is the single entry point that returns a clean, enriched
dataframe carrying every column in config.NATIONAL_SERIES (including the derived
`storage_risk`). The engineered feature matrix feeds the XGBoost readiness model.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..data import loaders

# Feature columns produced by engineer_features (order matters for SHAP labels).
FEATURE_NAMES = [
    "price_level",
    "price_momentum",
    "volume_momentum",
    "fx_momentum",
    "price_volatility",
    "storage_risk",
    "rainfall_mm",
    "global_index_momentum",
    "competitor_gap",
    "season",
]

FEATURE_LABELS = {
    "price_level": "Auction price level",
    "price_momentum": "Price momentum (3m vs 12m)",
    "volume_momentum": "Volume momentum (3m vs 12m)",
    "fx_momentum": "USD/LKR momentum",
    "price_volatility": "Price volatility (12m CV)",
    "storage_risk": "Storage risk",
    "rainfall_mm": "Rainfall",
    "global_index_momentum": "Global tea-price momentum",
    "competitor_gap": "Price gap vs competitor",
    "season": "Seasonality",
}

_MIN_HISTORY = 12        # months of history required before a row is usable


# --------------------------------------------------------------------------- #
# Clean / integrate / derive
# --------------------------------------------------------------------------- #
def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Sort by date, forward/back-fill gaps and clip impossible values."""
    df = df.sort_values("date").reset_index(drop=True)
    df = df.ffill().bfill()
    if "auction_price_usd" in df:
        df["auction_price_usd"] = df["auction_price_usd"].clip(lower=0.1)
    if "export_volume_kg" in df:
        df["export_volume_kg"] = df["export_volume_kg"].clip(lower=0)
    if "usd_lkr" in df:
        df["usd_lkr"] = df["usd_lkr"].clip(lower=1.0)
    return df


def derive_storage_risk(df: pd.DataFrame) -> pd.Series:
    """
    Tea is hygroscopic: monsoon rainfall raises warehouse humidity and spoilage
    risk; warmth compounds it; holding more inventory than usual adds exposure.
    Returns a 0-100 storage-risk index.
    """
    rainfall = df["rainfall_mm"].to_numpy(dtype="float64")
    temp = df["avg_temp_c"].to_numpy(dtype="float64")
    volume = df["export_volume_kg"].to_numpy(dtype="float64")

    inventory_ratio = volume / max(volume.mean(), 1.0)        # >1 => above-average stock
    risk = (
        18.0
        + 0.16 * (rainfall - 150.0)
        + 4.0 * (temp - 23.0)
        + 8.0 * (inventory_ratio - 1.0)
    )
    return pd.Series(np.clip(np.round(risk, 2), 0.0, 100.0), index=df.index)


def build_national() -> pd.DataFrame:
    """Load + clean the national series and attach the derived storage-risk column."""
    df = clean(loaders.load_national())
    df["storage_risk"] = derive_storage_risk(df)
    return df


# --------------------------------------------------------------------------- #
# Feature engineering (for the XGBoost readiness model)
# --------------------------------------------------------------------------- #
def _momentum(values: np.ndarray, t: int, short: int = 3, long: int = 12) -> float:
    """Short-window mean relative to long-window mean, as a fraction."""
    s = values[max(0, t - short + 1) : t + 1].mean()
    l = values[max(0, t - long + 1) : t + 1].mean()
    return float(s / l - 1.0) if l else 0.0


def _feature_row(df: pd.DataFrame, t: int) -> dict[str, float]:
    price = df["auction_price_usd"].to_numpy(dtype="float64")
    volume = df["export_volume_kg"].to_numpy(dtype="float64")
    fx = df["usd_lkr"].to_numpy(dtype="float64")
    gindex = df["global_tea_price_index"].to_numpy(dtype="float64")
    competitor = df["competitor_price_usd"].to_numpy(dtype="float64")
    window = price[max(0, t - 11) : t + 1]
    month = pd.to_datetime(df["date"].iloc[t]).month

    return {
        "price_level": float(price[t]),
        "price_momentum": _momentum(price, t),
        "volume_momentum": _momentum(volume, t),
        "fx_momentum": _momentum(fx, t),
        "price_volatility": float(window.std() / window.mean()) if window.mean() else 0.0,
        "storage_risk": float(df["storage_risk"].iloc[t]),
        "rainfall_mm": float(df["rainfall_mm"].iloc[t]),
        "global_index_momentum": _momentum(gindex, t),
        "competitor_gap": float((price[t] - competitor[t]) / competitor[t]) if competitor[t] else 0.0,
        "season": float(np.sin(2 * np.pi * (month - 1) / 12)),
    }


def engineer_features(df: pd.DataFrame) -> tuple[pd.DataFrame, list[int]]:
    """
    Build one feature row per month that has >= _MIN_HISTORY months behind it.
    Returns (features_df with FEATURE_NAMES columns, list of source row indices t).
    """
    idxs = list(range(_MIN_HISTORY, len(df)))
    rows = [_feature_row(df, t) for t in idxs]
    return pd.DataFrame(rows, columns=FEATURE_NAMES), idxs


def latest_features(df: pd.DataFrame) -> pd.DataFrame:
    """Single feature row for the most recent month (used at inference)."""
    return pd.DataFrame([_feature_row(df, len(df) - 1)], columns=FEATURE_NAMES)
