"""
Export-opportunity scoring (Opportunity Map + AI Country Recommendation modules).

For every destination we compute a 0-100 suitability score from an additive,
weighted model:

    suitability = 0.35*demand_growth + 0.20*price_premium + 0.20*compliance_ease
                + 0.15*low_tariff    + 0.10*market_momentum

Because the model is additive, the exact per-feature contribution (weight ×
deviation from a neutral 50 baseline) IS the explanation — the same "why" shape
the XGBoost SHAP path produces. ranked() sorts countries; recommend() picks the
best and assembles its drivers for the recommendation module.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import explain

WEIGHTS = {
    "demand_growth": 0.35,
    "price_premium": 0.20,
    "compliance_ease": 0.20,
    "low_tariff": 0.15,
    "market_momentum": 0.10,
}

COMPONENT_LABELS = {
    "demand_growth": "Forecast demand growth",
    "price_premium": "Price premium vs national",
    "compliance_ease": "Compliance ease",
    "low_tariff": "Low import tariff",
    "market_momentum": "Global market momentum",
}


def _clip(x: float) -> float:
    return float(max(0.0, min(100.0, x)))


def _status(score: float) -> str:
    if score >= 70:
        return "High"
    if score >= 55:
        return "Medium"
    return "Low"


def _country_subscores(hist: pd.DataFrame, reqs: dict, compliance_risk: float,
                       national_price: float, market_momentum_pct: float) -> dict[str, float]:
    vol = hist.sort_values("date")["volume_kg"].to_numpy(dtype="float64")
    price = hist.sort_values("date")["avg_price_usd"].to_numpy(dtype="float64")

    recent, prior = vol[-12:].mean(), vol[-24:-12].mean() if len(vol) >= 24 else vol[:-12].mean()
    demand_pct = (recent / prior - 1) * 100 if prior else 0.0
    price_premium_pct = (price[-12:].mean() / national_price - 1) * 100 if national_price else 0.0

    return {
        "demand_growth": _clip(50 + demand_pct * 2.0),
        "price_premium": _clip(50 + price_premium_pct * 3.0),
        "compliance_ease": _clip(100 - compliance_risk),
        "low_tariff": _clip(100 - reqs["import_tariff_pct"] * 3.0),
        "market_momentum": _clip(50 + market_momentum_pct * 4.0),
    }


def suitability(country: str, hist: pd.DataFrame, reqs: dict, compliance_result: dict,
                national_price: float, market_momentum_pct: float) -> dict:
    """Suitability score + additive 'why' for a single destination."""
    subs = _country_subscores(hist, reqs, compliance_result["compliance_risk"],
                              national_price, market_momentum_pct)
    score = round(sum(WEIGHTS[k] * subs[k] for k in WEIGHTS), 1)

    # Additive contribution of each driver around a neutral 50 baseline.
    contrib_values = [WEIGHTS[k] * (subs[k] - 50.0) for k in WEIGHTS]
    contributions = explain.breakdown(list(WEIGHTS.keys()), contrib_values, COMPONENT_LABELS)

    vol = hist.sort_values("date")["volume_kg"].to_numpy(dtype="float64")
    return {
        "country": country,
        "suitability": score,
        "status": _status(score),
        "subscores": {k: round(v, 1) for k, v in subs.items()},
        "contributions": contributions,
        "recent_volume_kg": int(vol[-12:].mean()),
        "import_tariff_pct": reqs["import_tariff_pct"],
        "demand_outlook": reqs["demand_outlook"],
        "compliance_passed": compliance_result["passed"],
    }


def ranked(country_df: pd.DataFrame, requirements: dict, compliance_all: dict,
           national_price: float, market_momentum_pct: float) -> list[dict]:
    """Suitability for every destination, sorted best-first (the opportunity map)."""
    out = []
    for country in requirements:
        hist = country_df[country_df["country"] == country]
        if hist.empty:
            continue
        out.append(suitability(country, hist, requirements[country],
                               compliance_all[country], national_price, market_momentum_pct))
    out.sort(key=lambda d: d["suitability"], reverse=True)
    return out


def recommend(ranking: list[dict]) -> dict:
    """Pick the best destination and surface its positive / negative drivers."""
    if not ranking:
        return {}
    best = ranking[0]
    positives, negatives = explain.top_drivers(best["contributions"])
    runner_up = ranking[1]["country"] if len(ranking) > 1 else None
    return {
        "country": best["country"],
        "suitability": best["suitability"],
        "status": best["status"],
        "positive_drivers": positives,
        "negative_drivers": negatives,
        "runner_up": runner_up,
        "compliance_passed": best["compliance_passed"],
    }
