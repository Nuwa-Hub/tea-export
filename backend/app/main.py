"""
FastAPI application.

Two-stage design:

    POST /api/train        -> trains the LSTMs ONCE and saves them to disk (slow)
    GET  /api/dashboard     -> loads the saved models and forecasts (instant)

Pipeline (up to the Export Readiness Index):

    CSV data  ->  saved LSTM models  ->  forecasts  ->  Export Readiness Index

Endpoints
---------
    GET  /api/health                 liveness
    GET  /api/history                the raw monthly dataset (from CSV)
    GET  /api/model-status           are models trained? when? with what accuracy?
    POST /api/train                  train + save all LSTMs (a few seconds)
    GET  /api/forecast?horizon=6     forecasts + accuracy (needs trained models)
    GET  /api/readiness?horizon=6    Export Readiness Index (needs trained models)
    GET  /api/dashboard?horizon=6    everything in one call (used by the UI)

If no models are trained yet, the forecast endpoints return HTTP 409 so the UI
can prompt the user to train first.
"""
from __future__ import annotations

import threading

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import data, forecasting, readiness

app = FastAPI(title="Tea Export Forecasting API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_DF = data.load_dataset()
_TRAIN_LOCK = threading.Lock()
_CACHE: dict[int, dict] = {}    # horizon -> forecast payload (cleared on retrain)


def _future_dates(horizon: int) -> list[str]:
    last = pd.to_datetime(_DF["date"].iloc[-1])
    return [(last + pd.DateOffset(months=i)).strftime("%Y-%m") for i in range(1, horizon + 1)]


def _require_models() -> None:
    if not forecasting.models_exist():
        raise HTTPException(
            status_code=409,
            detail="No trained model yet. Train the models first (POST /api/train).",
        )


def _compute(horizon: int) -> dict:
    """Forecast using the SAVED models (fast). Cached per horizon."""
    _require_models()
    if horizon in _CACHE:
        return _CACHE[horizon]

    meta = forecasting.load_meta() or {"series": {}}
    forecasts = {}
    for name in forecasting.SERIES:
        s = meta["series"].get(name, {})
        forecasts[name] = {
            "forecast": forecasting.load_and_forecast(name, _DF[name].tolist(), horizon),
            "metrics": s.get("metrics", {}),
            "backtest": s.get("backtest", []),
            "backtest_actual": s.get("backtest_actual", []),
        }

    eri = readiness.compute_readiness(
        price_hist=_DF["auction_price_usd"].tolist(),
        price_fc=forecasts["auction_price_usd"]["forecast"],
        volume_hist=_DF["export_volume_kg"].tolist(),
        volume_fc=forecasts["export_volume_kg"]["forecast"],
        fx_hist=_DF["usd_lkr"].tolist(),
        fx_fc=forecasts["usd_lkr"]["forecast"],
    )

    payload = {
        "horizon": horizon,
        "future_dates": _future_dates(horizon),
        "forecasts": forecasts,
        "readiness": eri,
        "model_trained_at": meta.get("trained_at"),
    }
    _CACHE[horizon] = payload
    return payload


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "months_of_data": len(_DF), "models_trained": forecasting.models_exist()}


@app.get("/api/history")
def history() -> dict:
    return {"data": data.records(_DF)}


@app.get("/api/model-status")
def model_status() -> dict:
    return {"trained": forecasting.models_exist(), "meta": forecasting.load_meta()}


@app.post("/api/train")
def train() -> dict:
    """Train + save all LSTMs. Slow (a few seconds) — but only done on demand."""
    if not _TRAIN_LOCK.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Training already in progress.")
    try:
        meta = forecasting.train_all(_DF)
        _CACHE.clear()                 # saved models changed -> drop cached forecasts
    finally:
        _TRAIN_LOCK.release()
    return {"status": "trained", "meta": meta}


@app.get("/api/forecast")
def forecast(horizon: int = Query(6, ge=1, le=24)) -> dict:
    p = _compute(horizon)
    return {
        "horizon": horizon,
        "future_dates": p["future_dates"],
        "forecasts": p["forecasts"],
        "model_trained_at": p["model_trained_at"],
    }


@app.get("/api/readiness")
def get_readiness(horizon: int = Query(6, ge=1, le=24)) -> dict:
    p = _compute(horizon)
    return {"horizon": horizon, "readiness": p["readiness"]}


@app.get("/api/dashboard")
def dashboard(horizon: int = Query(6, ge=1, le=24)) -> dict:
    """Everything the frontend needs in a single request (uses saved models)."""
    p = _compute(horizon)
    return {"history": data.records(_DF), **p}
