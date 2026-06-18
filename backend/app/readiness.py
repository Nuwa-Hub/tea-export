"""
Export Readiness Index (ERI).

This is the layer that turns raw LSTM forecasts into a business decision.
It is the main "research contribution" slot of the project — the weights
and component definitions below are a defensible starting point that you
can justify / tune / validate in your write-up.

    ERI = 0.40 * demand   +   0.30 * price
        + 0.20 * exchange  +   0.10 * (100 - risk)

Each component is normalised to 0..100 and then combined.

    score >= 80  -> "Ready"
    60..79       -> "Conditional"
    < 60         -> "Not Ready"
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


def compute_readiness(
    price_hist: list[float],
    price_fc: list[float],
    volume_hist: list[float],
    volume_fc: list[float],
    fx_hist: list[float],
    fx_fc: list[float],
) -> dict:
    """Return the ERI plus its component breakdown and a recommendation."""
    price_hist = np.asarray(price_hist, dtype="float64")
    volume_hist = np.asarray(volume_hist, dtype="float64")
    fx_hist = np.asarray(fx_hist, dtype="float64")

    recent = slice(-12, None)  # compare forecast against the trailing 12 months

    # --- Demand: forecast volume vs last 12 months -----------------------
    demand = _growth_score(volume_hist[recent].mean(), float(np.mean(volume_fc)), sensitivity=3.0)

    # --- Price: forecast price vs last 12 months -------------------------
    price = _growth_score(price_hist[recent].mean(), float(np.mean(price_fc)), sensitivity=4.0)

    # --- Exchange rate: LKR depreciation => higher LKR earnings => good --
    exchange = _growth_score(fx_hist[recent].mean(), float(np.mean(fx_fc)), sensitivity=2.5)

    # --- Risk: coefficient of variation of the last 12 months of price ---
    cv = price_hist[recent].std() / price_hist[recent].mean() if price_hist[recent].mean() else 0
    risk = _clip(cv * 100 * 5)            # 0 = stable, higher = riskier
    risk_score = 100 - risk               # invert so "high score = low risk"

    eri = (
        WEIGHTS["demand"] * demand
        + WEIGHTS["price"] * price
        + WEIGHTS["exchange"] * exchange
        + WEIGHTS["risk"] * risk_score
    )
    eri = round(_clip(eri), 1)

    if eri >= 80:
        status, action = "Ready", "Proceed with export planning for the next shipment cycle."
    elif eri >= 60:
        status, action = "Conditional", "Export is viable but monitor price and demand before committing volume."
    else:
        status, action = "Not Ready", "Hold. Forecasts suggest waiting for better demand/price conditions."

    return {
        "eri": eri,
        "status": status,
        "recommendation": action,
        "components": {
            "demand": round(demand, 1),
            "price": round(price, 1),
            "exchange": round(exchange, 1),
            "risk": round(risk_score, 1),
        },
        "weights": WEIGHTS,
    }
