"""
Synthetic dataset generation.

Everything the platform consumes is generated here ONCE and written to disk, so
the app runs fully offline and deterministically (numpy seed = 42). Swap any of
these files for real Sri Lanka Tea Board / Central Bank data later — the column
names are the contract; nothing downstream changes.

Artifacts written to backend/data/:
    tea_export.csv          national monthly series (price, volume, FX, weather, market)
    tea_export.xlsx         same, as Excel (if openpyxl is available)
    country_exports.csv     long-format per-destination volume + price
    buyer_requirements.json per-country compliance specs + tariffs + demand outlook
    knowledge_base/*.txt    short market/compliance notes for the RAG advisor

Regenerate with:   cd backend && python -m app.data.generate
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import (
    BUYER_REQ_PATH,
    COUNTRIES,
    COUNTRY_CSV_PATH,
    CSV_PATH,
    DATA_DIR,
    KB_DIR,
    XLSX_PATH,
)

_SEED = 42
START = "2016-01-01"
N_MONTHS = 108


# --------------------------------------------------------------------------- #
# National monthly series  (INPUT: volumes, prices, FX, weather, market)
# --------------------------------------------------------------------------- #
def generate_national() -> pd.DataFrame:
    """Monthly national series: price, volume, FX + weather + market context."""
    rng = np.random.default_rng(_SEED)
    dates = pd.date_range(START, periods=N_MONTHS, freq="MS")
    t = np.arange(N_MONTHS)
    month = dates.month.to_numpy()
    season = np.sin(2 * np.pi * (month - 1) / 12)       # peaks mid-year
    season2 = np.cos(2 * np.pi * (month - 1) / 12)

    # Auction price (USD/kg): slow upward trend + season + noise
    price = 4.30 + 0.012 * t + 0.25 * season + 0.10 * season2 + rng.normal(0, 0.08, N_MONTHS)

    # Export volume (kg): higher in peak season, gentle growth
    volume = 20_000 + 35 * t + 2_500 * season + 900 * season2 + rng.normal(0, 600, N_MONTHS)
    volume = np.clip(volume, 5_000, None)

    # USD/LKR: long depreciation trend with a sharp 2022-style currency shock
    usd_lkr = 180 + 0.9 * t + rng.normal(0, 1.5, N_MONTHS)
    usd_lkr[74:] += 120
    usd_lkr = np.clip(usd_lkr, 150, None)

    # Weather (tea-growing regions): monsoon-driven rainfall + mild temperature
    rainfall = 180 + 120 * np.clip(season, 0, None) + 60 * season2 + rng.normal(0, 25, N_MONTHS)
    rainfall = np.clip(rainfall, 20, None)
    temp = 24.0 - 1.5 * season + rng.normal(0, 0.6, N_MONTHS)

    # Market context: global tea price index + a competitor (Kenya/India) price
    global_index = 100 + 0.18 * t + 6 * season + rng.normal(0, 2.5, N_MONTHS)
    competitor = 3.90 + 0.010 * t + 0.18 * season + rng.normal(0, 0.10, N_MONTHS)

    return pd.DataFrame(
        {
            "date": dates,
            "auction_price_usd": np.round(price, 3),
            "export_volume_kg": np.round(volume).astype(int),
            "usd_lkr": np.round(usd_lkr, 2),
            "rainfall_mm": np.round(rainfall, 1),
            "avg_temp_c": np.round(temp, 2),
            "global_tea_price_index": np.round(global_index, 2),
            "competitor_price_usd": np.round(competitor, 3),
        }
    )


# --------------------------------------------------------------------------- #
# Country-wise exports  (OUTPUT module 1: country demand)
# --------------------------------------------------------------------------- #
# Each destination gets a base share of national volume, its own multi-year
# trend (e.g. Russia softening, China/Japan growing), seasonality and a price
# premium/discount relative to the national auction price.
_COUNTRY_PROFILE = {
    #            base_share  share_trend  price_factor  seasonal_amp
    "Russia":   (0.22,       -0.0012,     0.97,         0.8),
    "UAE":      (0.16,        0.0006,     1.05,         0.5),
    "Iran":     (0.14,       -0.0004,     0.95,         0.6),
    "Iraq":     (0.12,        0.0003,     0.98,         0.5),
    "Turkey":   (0.11,        0.0002,     1.00,         0.7),
    "China":    (0.10,        0.0011,     1.12,         0.4),
    "Japan":    (0.08,        0.0008,     1.18,         0.3),
    "Germany":  (0.07,        0.0005,     1.10,         0.4),
}


def generate_country_exports(national: pd.DataFrame) -> pd.DataFrame:
    """Long-format per-destination monthly volume + average price."""
    rng = np.random.default_rng(_SEED + 1)
    dates = pd.to_datetime(national["date"])
    t = np.arange(len(national))
    month = dates.dt.month.to_numpy()
    rows = []

    for country in COUNTRIES:
        base, trend, price_factor, amp = _COUNTRY_PROFILE[country]
        share = np.clip(base + trend * t, 0.01, None)
        seasonal = 1.0 + amp * 0.15 * np.sin(2 * np.pi * (month - 1) / 12)
        vol = national["export_volume_kg"].to_numpy() * share * seasonal
        vol = np.clip(vol * (1 + rng.normal(0, 0.04, len(t))), 200, None)
        price = national["auction_price_usd"].to_numpy() * price_factor
        price = np.round(price * (1 + rng.normal(0, 0.02, len(t))), 3)

        for d, v, p in zip(dates.dt.strftime("%Y-%m-%d"), np.round(vol).astype(int), price):
            rows.append({"date": d, "country": country, "volume_kg": int(v), "avg_price_usd": float(p)})

    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Buyer requirements  (INPUT: buyer requirements / "PDF parsing" output)
# --------------------------------------------------------------------------- #
# In a real deployment these are parsed out of buyer/regulatory PDFs. Here they
# are the structured result of that parsing — see processing/documents.py.
_BUYER_REQUIREMENTS = {
    "Russia":  {"max_pesticide_ppm": 0.05, "max_moisture_pct": 7.0, "min_grade": "BOP",
                "required_certifications": ["ISO 22000"], "packaging": "Paper sack 25kg",
                "import_tariff_pct": 12.5, "demand_outlook": "Softening (sanctions/logistics)"},
    "UAE":     {"max_pesticide_ppm": 0.04, "max_moisture_pct": 6.5, "min_grade": "BOP",
                "required_certifications": ["ISO 22000", "Halal"], "packaging": "Foil-lined 10kg",
                "import_tariff_pct": 5.0, "demand_outlook": "Growing (re-export hub)"},
    "Iran":    {"max_pesticide_ppm": 0.06, "max_moisture_pct": 7.5, "min_grade": "OP",
                "required_certifications": ["Halal"], "packaging": "Paper sack 40kg",
                "import_tariff_pct": 20.0, "demand_outlook": "Stable but FX-constrained"},
    "Iraq":    {"max_pesticide_ppm": 0.06, "max_moisture_pct": 7.5, "min_grade": "OP",
                "required_certifications": ["Halal"], "packaging": "Paper sack 30kg",
                "import_tariff_pct": 15.0, "demand_outlook": "Stable"},
    "Turkey":  {"max_pesticide_ppm": 0.05, "max_moisture_pct": 7.0, "min_grade": "BOP",
                "required_certifications": ["ISO 22000"], "packaging": "Carton 20kg",
                "import_tariff_pct": 18.0, "demand_outlook": "Stable (domestic competition)"},
    "China":   {"max_pesticide_ppm": 0.03, "max_moisture_pct": 6.0, "min_grade": "BOPF",
                "required_certifications": ["ISO 22000", "Organic"], "packaging": "Vacuum 5kg",
                "import_tariff_pct": 10.0, "demand_outlook": "Growing (premium segment)"},
    "Japan":   {"max_pesticide_ppm": 0.01, "max_moisture_pct": 5.5, "min_grade": "BOPF",
                "required_certifications": ["ISO 22000", "Organic", "JAS"], "packaging": "Vacuum 2kg",
                "import_tariff_pct": 8.0, "demand_outlook": "Growing (high-value, strict)"},
    "Germany": {"max_pesticide_ppm": 0.02, "max_moisture_pct": 6.0, "min_grade": "BOPF",
                "required_certifications": ["ISO 22000", "Rainforest Alliance"], "packaging": "Foil 5kg",
                "import_tariff_pct": 6.0, "demand_outlook": "Growing (sustainability-led)"},
}


def generate_buyer_requirements() -> dict:
    return _BUYER_REQUIREMENTS


# --------------------------------------------------------------------------- #
# Knowledge base  (for the RAG advisor)
# --------------------------------------------------------------------------- #
_KNOWLEDGE_BASE = {
    "market_outlook.txt": (
        "Ceylon tea global demand outlook. Premium and organic segments in Japan, China and "
        "Germany are growing at 6-9% annually, driven by health-conscious consumers and "
        "sustainability certification. Traditional bulk markets such as Russia, Iran and Iraq "
        "remain large by volume but are price-sensitive and exposed to currency and logistics "
        "risk. Exporters should prioritise high-value destinations when auction prices are firm "
        "and forecast demand growth is positive."
    ),
    "compliance_guidelines.txt": (
        "Export compliance for Ceylon tea. Each destination enforces maximum pesticide residue "
        "limits (MRL) and maximum moisture content; Japan and the EU (Germany) apply the "
        "strictest MRLs. Required certifications vary: ISO 22000 food safety is near-universal, "
        "Halal is mandatory for Middle East markets, and Organic / JAS / Rainforest Alliance are "
        "required for premium European and Japanese buyers. A shipment failing any mandatory "
        "certification or exceeding an MRL/moisture limit must not be exported to that market."
    ),
    "logistics_storage.txt": (
        "Storage and logistics risk. Tea is hygroscopic: high warehouse humidity, driven by "
        "monsoon rainfall, raises the storage-risk index and can cause mould and quality loss. "
        "Risk is highest in the May-September south-west monsoon. Vacuum and foil-lined packaging "
        "reduce moisture uptake. When the storage-risk forecast is elevated, ship faster or invest "
        "in dehumidified storage rather than holding inventory."
    ),
    "currency_notes.txt": (
        "Currency and pricing. Exporters are paid in USD but incur costs in LKR, so a depreciating "
        "rupee (rising USD/LKR) increases local-currency earnings and improves export "
        "competitiveness. A rising USD/LKR forecast is therefore favourable for the Export "
        "Readiness Index, while a sharp appreciation squeezes margins."
    ),
    "quality_standards.txt": (
        "Grades and quality. Common Ceylon grades from finest to coarse include BOPF (Broken "
        "Orange Pekoe Fannings), BOP (Broken Orange Pekoe) and OP (Orange Pekoe). Premium markets "
        "(Japan, China, Germany) require finer BOPF-grade leaf with low moisture; bulk markets "
        "accept OP/BOP. Matching grade to the destination's minimum requirement is a precondition "
        "for export readiness."
    ),
}


def generate_knowledge_base() -> dict:
    return _KNOWLEDGE_BASE


# --------------------------------------------------------------------------- #
# Write everything to disk
# --------------------------------------------------------------------------- #
def make_sample_files() -> list[Path]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    KB_DIR.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    national = generate_national()
    national.to_csv(CSV_PATH, index=False)
    written.append(CSV_PATH)
    try:
        national.to_excel(XLSX_PATH, index=False)       # needs openpyxl
        written.append(XLSX_PATH)
    except ModuleNotFoundError:
        print("openpyxl not installed -> skipping .xlsx (CSV written).")

    generate_country_exports(national).to_csv(COUNTRY_CSV_PATH, index=False)
    written.append(COUNTRY_CSV_PATH)

    with open(BUYER_REQ_PATH, "w") as fh:
        json.dump(generate_buyer_requirements(), fh, indent=2)
    written.append(BUYER_REQ_PATH)

    for name, text in generate_knowledge_base().items():
        path = KB_DIR / name
        path.write_text(text + "\n")
        written.append(path)

    return written


if __name__ == "__main__":
    paths = make_sample_files()
    print("Wrote:")
    for p in paths:
        print(" ", p)
