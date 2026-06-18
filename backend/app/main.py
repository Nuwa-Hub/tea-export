"""
FastAPI application.

Pipeline (matches the research road-map up to the Export Readiness Index):

    dummy data  ->  LSTM forecasts (price / volume / FX)  ->  Readiness Index

Endpoints
---------
    GET /api/health                 liveness probe
    GET /api/history                the raw monthly dataset
    GET /api/dashboard?horizon=6    history + forecasts + metrics + ERI (one call)
    GET /api/forecast?horizon=6     just the LSTM forecasts + accuracy
    GET /api/readiness?horizon=6    just the Export Readiness Index

The first forecast call trains the LSTMs (a few seconds) and the result is
cached per horizon, so subsequent calls are instant. POST /api/retrain clears it.
"""
from __future__ import annotations

import threading

import pandas as pd
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from . import data, forecasting, readiness

app = FastAPI(title="Tea Export Forecasting API", version="0.1.0")

# Allow the React dev server (Vite default port) to call us.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_DF = data.generate_dataset()
_LOCK = threading.Lock()
_CACHE: dict[int, dict] = {}    # horizon -> computed payload


def _future_dates(horizon: int) -> list[str]:
    last = _DF["date"].iloc[-1]
    return [
        (last + pd.DateOffset(months=i)).strftime("%Y-%m")
        for i in range(1, horizon + 1)
    ]


def _compute(horizon: int) -> dict:
    """Run the full pipeline for a given forecast horizon (cached)."""
    with _LOCK:
        if horizon in _CACHE:
            return _CACHE[horizon]

        price = forecasting.forecast_series(_DF["auction_price_usd"].tolist(), horizon)
        volume = forecasting.forecast_series(_DF["export_volume_kg"].tolist(), horizon)
        fx = forecasting.forecast_series(_DF["usd_lkr"].tolist(), horizon)

        eri = readiness.compute_readiness(
            price_hist=_DF["auction_price_usd"].tolist(),
            price_fc=price.forecast,
            volume_hist=_DF["export_volume_kg"].tolist(),
            volume_fc=volume.forecast,
            fx_hist=_DF["usd_lkr"].tolist(),
            fx_fc=fx.forecast,
        )

        payload = {
            "horizon": horizon,
            "future_dates": _future_dates(horizon),
            "forecasts": {
                "auction_price_usd": _series_payload(price),
                "export_volume_kg": _series_payload(volume),
                "usd_lkr": _series_payload(fx),
            },
            "readiness": eri,
        }
        _CACHE[horizon] = payload
        return payload


def _series_payload(r: forecasting.ForecastResult) -> dict:
    return {
        "forecast": r.forecast,
        "metrics": r.metrics,
        "backtest": r.backtest,
        "backtest_actual": r.backtest_actual,
    }


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "months_of_data": len(_DF)}


@app.get("/api/history")
def history() -> dict:
    return {"data": data.records(_DF)}


@app.get("/api/forecast")
def forecast(horizon: int = Query(6, ge=1, le=24)) -> dict:
    p = _compute(horizon)
    return {"horizon": horizon, "future_dates": p["future_dates"], "forecasts": p["forecasts"]}


@app.get("/api/readiness")
def get_readiness(horizon: int = Query(6, ge=1, le=24)) -> dict:
    p = _compute(horizon)
    return {"horizon": horizon, "readiness": p["readiness"]}


@app.get("/api/dashboard")
def dashboard(horizon: int = Query(6, ge=1, le=24)) -> dict:
    """Everything the frontend needs in a single request."""
    p = _compute(horizon)
    return {"history": data.records(_DF), **p}


@app.post("/api/retrain")
def retrain() -> dict:
    with _LOCK:
        _CACHE.clear()
    return {"status": "cache cleared; next request will retrain"}
