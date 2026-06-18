"""
Synthetic ("dummy") monthly Sri Lankan tea-export dataset.

This stands in for the real series you will later download from the
Sri Lanka Tea Board / Tea Exporters Association / Central Bank:

    - auction_price_usd : Colombo auction FOB price, USD per kg
    - export_volume_kg  : total monthly export volume, kg
    - usd_lkr           : USD/LKR exchange rate (month average)

The numbers are generated with a fixed seed so every run is reproducible.
Each series is trend + seasonality + mild noise, which gives the LSTM
something realistic to learn (an upward drift plus a yearly cycle).

Replace `generate_dataset()` with a CSV loader when you have real data:

    df = pd.read_csv("tea_export.csv", parse_dates=["date"])
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Fixed seed -> identical dataset on every run (important for a demo / paper).
_SEED = 42

# Series span: Jan 2016 .. Dec 2024 (108 monthly observations).
START = "2016-01-01"
N_MONTHS = 108


def generate_dataset() -> pd.DataFrame:
    """Return a monthly DataFrame indexed 0..N-1 with a `date` column."""
    rng = np.random.default_rng(_SEED)
    dates = pd.date_range(START, periods=N_MONTHS, freq="MS")
    t = np.arange(N_MONTHS)

    # Month-of-year (0..11) drives the seasonal component.
    month = dates.month.to_numpy()
    season = np.sin(2 * np.pi * (month - 1) / 12)      # peaks mid-year
    season2 = np.cos(2 * np.pi * (month - 1) / 12)

    # --- Auction price (USD/kg): slow upward trend + season + noise ---
    price = (
        4.30
        + 0.012 * t                       # ~ +1.2 cents/month long-run drift
        + 0.25 * season
        + 0.10 * season2
        + rng.normal(0, 0.08, N_MONTHS)
    )

    # --- Export volume (kg): higher in peak season, gentle growth ---
    volume = (
        20_000
        + 35 * t                          # gentle growth
        + 2_500 * season
        + 900 * season2
        + rng.normal(0, 600, N_MONTHS)
    )
    volume = np.clip(volume, 5_000, None)

    # --- USD/LKR: long depreciation trend with a sharp 2022-style jump ---
    usd_lkr = (
        180
        + 0.9 * t
        + rng.normal(0, 1.5, N_MONTHS)
    )
    # Simulate the 2022 currency shock (around month index 74 = Mar 2022).
    usd_lkr[74:] += 120
    usd_lkr = np.clip(usd_lkr, 150, None)

    df = pd.DataFrame(
        {
            "date": dates,
            "auction_price_usd": np.round(price, 3),
            "export_volume_kg": np.round(volume).astype(int),
            "usd_lkr": np.round(usd_lkr, 2),
        }
    )
    return df


def records(df: pd.DataFrame) -> list[dict]:
    """Serialise a dataframe to JSON-friendly records (date as YYYY-MM)."""
    out = df.copy()
    out["date"] = out["date"].dt.strftime("%Y-%m")
    return out.to_dict(orient="records")
