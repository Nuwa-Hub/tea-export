"""
Load the generated datasets from disk, generating them on first run if missing.

These return raw data exactly as stored. Cleaning, integration and feature
engineering happen in processing/pipeline.py, not here.
"""
from __future__ import annotations

import json

import pandas as pd

from ..config import (
    BUYER_REQ_PATH,
    COUNTRY_CSV_PATH,
    CSV_PATH,
    KB_DIR,
)
from . import generate


def _ensure_files() -> None:
    if not CSV_PATH.exists() or not COUNTRY_CSV_PATH.exists() or not BUYER_REQ_PATH.exists():
        generate.make_sample_files()


def load_national() -> pd.DataFrame:
    """National monthly series (price, volume, FX, weather, market)."""
    _ensure_files()
    return pd.read_csv(CSV_PATH, parse_dates=["date"])


def load_country_exports() -> pd.DataFrame:
    """Long-format per-destination monthly volume + price."""
    _ensure_files()
    return pd.read_csv(COUNTRY_CSV_PATH, parse_dates=["date"])


def load_buyer_requirements() -> dict:
    """Per-country compliance specs / tariffs / demand outlook."""
    _ensure_files()
    with open(BUYER_REQ_PATH) as fh:
        return json.load(fh)


def load_knowledge_base() -> dict[str, str]:
    """{filename: text} of the RAG knowledge-base documents."""
    _ensure_files()
    docs: dict[str, str] = {}
    if KB_DIR.exists():
        for path in sorted(KB_DIR.glob("*.txt")):
            docs[path.name] = path.read_text()
    return docs


def records(df: pd.DataFrame) -> list[dict]:
    """Serialise a dataframe to JSON-friendly records (date as YYYY-MM)."""
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m")
    return out.to_dict(orient="records")
