"""
Sample dataset handling.

Instead of regenerating data on every run, the synthetic series is written
ONCE to disk as CSV (and XLSX) and then loaded from that file:

    backend/data/tea_export.csv
    backend/data/tea_export.xlsx

Columns:
    date              first day of the month (YYYY-MM-DD)
    auction_price_usd Colombo auction FOB price, USD per kg
    export_volume_kg  total monthly export volume, kg
    usd_lkr           USD/LKR exchange rate (month average)

To (re)generate the sample files:

    cd backend && python -m app.data

To plug in REAL data later, just replace tea_export.csv with your own file
(same column names) — nothing else changes.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

# Fixed seed -> identical dataset every time it is generated.
_SEED = 42
START = "2016-01-01"
N_MONTHS = 108

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CSV_PATH = DATA_DIR / "tea_export.csv"
XLSX_PATH = DATA_DIR / "tea_export.xlsx"


def generate_dataset() -> pd.DataFrame:
    """Build the synthetic monthly dataset in memory (trend + season + noise)."""
    rng = np.random.default_rng(_SEED)
    dates = pd.date_range(START, periods=N_MONTHS, freq="MS")
    t = np.arange(N_MONTHS)

    month = dates.month.to_numpy()
    season = np.sin(2 * np.pi * (month - 1) / 12)      # peaks mid-year
    season2 = np.cos(2 * np.pi * (month - 1) / 12)

    # Auction price (USD/kg): slow upward trend + season + noise
    price = (
        4.30
        + 0.012 * t
        + 0.25 * season
        + 0.10 * season2
        + rng.normal(0, 0.08, N_MONTHS)
    )

    # Export volume (kg): higher in peak season, gentle growth
    volume = (
        20_000
        + 35 * t
        + 2_500 * season
        + 900 * season2
        + rng.normal(0, 600, N_MONTHS)
    )
    volume = np.clip(volume, 5_000, None)

    # USD/LKR: long depreciation trend with a sharp 2022-style jump
    usd_lkr = 180 + 0.9 * t + rng.normal(0, 1.5, N_MONTHS)
    usd_lkr[74:] += 120                                 # ~Mar 2022 currency shock
    usd_lkr = np.clip(usd_lkr, 150, None)

    return pd.DataFrame(
        {
            "date": dates,
            "auction_price_usd": np.round(price, 3),
            "export_volume_kg": np.round(volume).astype(int),
            "usd_lkr": np.round(usd_lkr, 2),
        }
    )


def make_sample_files() -> list[Path]:
    """Generate the dataset and write it to CSV (always) and XLSX (if possible)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df = generate_dataset()
    written = []

    df.to_csv(CSV_PATH, index=False)
    written.append(CSV_PATH)

    try:
        df.to_excel(XLSX_PATH, index=False)             # needs openpyxl
        written.append(XLSX_PATH)
    except ModuleNotFoundError:
        print("openpyxl not installed -> skipping .xlsx (CSV written).")

    return written


def load_dataset() -> pd.DataFrame:
    """Load the dataset from CSV, generating the sample file first if missing."""
    if not CSV_PATH.exists():
        make_sample_files()
    df = pd.read_csv(CSV_PATH, parse_dates=["date"])
    return df


def records(df: pd.DataFrame) -> list[dict]:
    """Serialise a dataframe to JSON-friendly records (date as YYYY-MM)."""
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m")
    return out.to_dict(orient="records")


if __name__ == "__main__":
    paths = make_sample_files()
    print("Wrote:")
    for p in paths:
        print(" ", p)
