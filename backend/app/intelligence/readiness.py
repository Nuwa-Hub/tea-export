"""
Export Readiness Index (ERI) — the weighted decision score.

This is the project's headline "research contribution" layer: it turns raw
forecasts into a 0-100 go/no-go score. The weights and component formulas are a
defensible starting point to justify / tune / validate in the write-up.

    ERI = 0.40 * demand   +   0.30 * price
        + 0.20 * exchange  +   0.10 * stability(low risk)

    score >= 80 -> "Ready" | 60..79 -> "Conditional" | < 60 -> "Not Ready"

The XGBoost model in xgb_readiness.py *learns* this index from engineered features
so it can be explained with SHAP; this module remains the ground-truth definition.
"""
from __future__ import annotations

import numpy as np

WEIGHTS = {
    "demand": 0.40,      # forecast export-volume growth
    "price": 0.30,       # forecast auction-price trend
    "exchange": 0.20,    # USD/LKR outlook (depreciation favours exporters)
    "risk": 0.10,        # recent price volatility (lower is better)
}


def _clip(x: float) -> float:
    return float(max(0.0, min(100.0, x)))


def _growth_score(recent_avg: float, forecast_avg: float, sensitivity: float) -> float:
    """Map a % change into a 0..100 score centred on 50 (= flat)."""
    if recent_avg == 0:
        return 50.0
    pct = (forecast_avg - recent_avg) / recent_avg * 100.0
    return _clip(50.0 + pct * sensitivity)


def components(
    price_hist, price_fc, volume_hist, volume_fc, fx_hist, fx_fc
) -> dict[str, float]:
    """The four 0-100 component scores that feed the ERI."""
    price_hist = np.asarray(price_hist, dtype="float64")
    volume_hist = np.asarray(volume_hist, dtype="float64")
    fx_hist = np.asarray(fx_hist, dtype="float64")
    recent = slice(-12, None)

    demand = _growth_score(volume_hist[recent].mean(), float(np.mean(volume_fc)), 3.0)
    price = _growth_score(price_hist[recent].mean(), float(np.mean(price_fc)), 4.0)
    exchange = _growth_score(fx_hist[recent].mean(), float(np.mean(fx_fc)), 2.5)

    cv = price_hist[recent].std() / price_hist[recent].mean() if price_hist[recent].mean() else 0
    risk = _clip(cv * 100 * 5)
    risk_score = 100 - risk

    return {
        "demand": round(demand, 1),
        "price": round(price, 1),
        "exchange": round(exchange, 1),
        "risk": round(risk_score, 1),
    }


def score_from_components(comp: dict[str, float]) -> float:
    eri = sum(WEIGHTS[k] * comp[k] for k in WEIGHTS)
    return round(_clip(eri), 1)


def status_for(eri: float) -> tuple[str, str]:
    if eri >= 80:
        return "Ready", "Proceed with export planning for the next shipment cycle."
    if eri >= 60:
        return "Conditional", "Export is viable but monitor price and demand before committing volume."
    return "Not Ready", "Hold. Forecasts suggest waiting for better demand/price conditions."


def compute_readiness(price_hist, price_fc, volume_hist, volume_fc, fx_hist, fx_fc) -> dict:
    """Return the ERI plus its component breakdown and a recommendation."""
    comp = components(price_hist, price_fc, volume_hist, volume_fc, fx_hist, fx_fc)
    eri = score_from_components(comp)
    status, action = status_for(eri)
    return {
        "eri": eri,
        "status": status,
        "recommendation": action,
        "components": comp,
        "weights": WEIGHTS,
    }
