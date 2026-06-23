"""
ARIMA baseline (statsmodels) — the statistical counterpart to the LSTM.

Two uses:
  * national_compare(values, horizon): a baseline forecast + back-test metrics for
    each national series, so the UI can show LSTM-vs-ARIMA side by side (the
    comparison is itself a research contribution per the project road-map).
  * country_demand(df_long, country, horizon): fast per-country export-demand
    forecast for the country-wise demand module (one ARIMA per destination).

ARIMA is cheap on ~108 points, so it runs at request time (cached per horizon by
the API). Fits are wrapped so a non-converging series degrades gracefully instead
of crashing the endpoint.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from .lstm import EVAL_HOLDOUT, score

# Orders tried in turn; first one that fits wins. (p,d,q)
_ORDERS = [(2, 1, 2), (1, 1, 1), (1, 1, 0), (0, 1, 0)]


def _fit_forecast(values: list[float], horizon: int) -> list[float] | None:
    """Fit ARIMA (trying a few orders) and forecast `horizon` steps."""
    from statsmodels.tsa.arima.model import ARIMA

    series = np.asarray(values, dtype="float64")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for order in _ORDERS:
            try:
                fit = ARIMA(series, order=order).fit()
                fc = np.asarray(fit.forecast(steps=horizon), dtype="float64")
                if np.all(np.isfinite(fc)):
                    return [round(float(v), 3) for v in fc]
            except Exception:
                continue
    return None


def forecast(values: list[float], horizon: int) -> list[float] | None:
    return _fit_forecast(values, horizon)


def backtest(values: list[float], holdout: int | None = None):
    """Fit on all-but-tail, forecast the tail, score against actuals."""
    series = np.asarray(values, dtype="float64")
    h = holdout or min(EVAL_HOLDOUT, max(3, len(series) // 4))
    pred = _fit_forecast(series[:-h].tolist(), h)
    if pred is None:
        return None, [], series[-h:].round(3).tolist()
    actual = series[-h:]
    return score(actual, np.asarray(pred)), [round(v, 3) for v in pred], actual.round(3).tolist()


def national_compare(values: list[float], horizon: int) -> dict:
    """ARIMA forecast + back-test metrics for one national series."""
    metrics, bt_pred, bt_actual = backtest(values)
    return {
        "forecast": forecast(values, horizon) or [],
        "metrics": metrics or {},
        "backtest": bt_pred,
        "backtest_actual": bt_actual,
    }


def country_demand(df_long: pd.DataFrame, country: str, horizon: int) -> dict:
    """Per-country export-volume forecast with ARIMA back-test accuracy."""
    sub = df_long[df_long["country"] == country].sort_values("date")
    values = sub["volume_kg"].astype("float64").tolist()
    metrics, _, _ = backtest(values)
    return {
        "country": country,
        "history": [int(v) for v in values],
        "forecast": [int(round(v)) for v in (forecast(values, horizon) or [])],
        "metrics": metrics or {},
    }
