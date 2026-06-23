"""
Central configuration: filesystem paths, the series/countries we model, and the
environment flags that toggle optional integrations (the LLM advisor).

Everything else imports paths and constants from here so there is a single
source of truth for "where do models live" and "which countries do we cover".
"""
from __future__ import annotations

import os
from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
APP_DIR = Path(__file__).resolve().parent          # backend/app
BACKEND_DIR = APP_DIR.parent                        # backend
DATA_DIR = BACKEND_DIR / "data"                     # generated CSV/JSON artifacts
MODELS_DIR = BACKEND_DIR / "models"                 # saved .keras / .pkl / xgb / meta
KB_DIR = DATA_DIR / "knowledge_base"                # RAG text documents

CSV_PATH = DATA_DIR / "tea_export.csv"              # national monthly series
XLSX_PATH = DATA_DIR / "tea_export.xlsx"
COUNTRY_CSV_PATH = DATA_DIR / "country_exports.csv"  # long-format per-destination
BUYER_REQ_PATH = DATA_DIR / "buyer_requirements.json"
LEDGER_PATH = DATA_DIR / "ledger.json"              # simulated blockchain ledger

META_PATH = MODELS_DIR / "training_meta.json"
XGB_PATH = MODELS_DIR / "xgb_readiness.json"

# --------------------------------------------------------------------------- #
# What we model
# --------------------------------------------------------------------------- #
# National monthly series forecast with both LSTM and ARIMA.
NATIONAL_SERIES = ["auction_price_usd", "export_volume_kg", "usd_lkr", "storage_risk"]

# Human labels reused by the API/UI.
SERIES_LABELS = {
    "auction_price_usd": "Auction price (USD/kg)",
    "export_volume_kg": "Export volume (kg)",
    "usd_lkr": "USD/LKR rate",
    "storage_risk": "Storage risk index",
}

# Destination markets (real Sri Lanka Ceylon-tea buyers) used for the
# country-wise demand forecast, opportunity map and recommendation.
COUNTRIES = ["Russia", "UAE", "Iran", "Iraq", "Turkey", "China", "Japan", "Germany"]

# --------------------------------------------------------------------------- #
# Optional LLM advisor toggle
# --------------------------------------------------------------------------- #
# Offline templated advisor is the default. Set USE_LLM=1 (and provide an API
# key) to route the advisor narrative through the Claude API instead.
USE_LLM = os.environ.get("USE_LLM", "0") == "1"
LLM_MODEL = os.environ.get("LLM_MODEL", "claude-haiku-4-5-20251001")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
