"""
Storage-risk interpretation.

The storage-risk *series* is derived in processing.pipeline.derive_storage_risk and
forecast by the LSTM engine (it is one of config.NATIONAL_SERIES). This module turns
the raw 0-100 forecast into a human-readable risk assessment for the
Readiness & Compliance module.
"""
from __future__ import annotations

import numpy as np

# Thresholds on the 0-100 storage-risk index.
LOW, HIGH = 35.0, 60.0


def level_for(value: float) -> str:
    if value >= HIGH:
        return "High"
    if value >= LOW:
        return "Moderate"
    return "Low"


def summarize(history: list[float], forecast: list[float]) -> dict:
    """Current vs forecast storage risk, peak month and a mitigation note."""
    current = float(history[-1]) if history else 0.0
    fc = np.asarray(forecast, dtype="float64") if forecast else np.array([current])
    forecast_avg = float(fc.mean())
    peak = float(fc.max())
    peak_month = int(fc.argmax()) + 1
    level = level_for(forecast_avg)

    if level == "High":
        note = (
            "Elevated storage risk ahead (monsoon humidity). Ship faster or use "
            "dehumidified / vacuum storage rather than holding inventory."
        )
    elif level == "Moderate":
        note = "Moderate storage risk. Monitor warehouse humidity and prioritise older lots."
    else:
        note = "Storage conditions favourable for holding and consolidating shipments."

    return {
        "current": round(current, 1),
        "forecast_avg": round(forecast_avg, 1),
        "peak": round(peak, 1),
        "peak_month": peak_month,
        "level": level,
        "note": note,
    }
