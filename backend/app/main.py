"""
FastAPI application — AI-Powered Tea Export Intelligence Platform (Component 04).

Two-stage design is preserved:
    POST /api/train     trains the LSTMs + XGBoost ONCE and saves them (slow)
    GET  /api/*         loads the saved models and serves instantly (cached per horizon)

Pipeline:
    dummy data -> processing -> {LSTM, ARIMA, XGBoost} -> readiness / opportunity /
    compliance / advisor / blockchain passport

Endpoints are grouped by the 7 output modules — see the route docstrings.
If no models are trained yet, forecast endpoints return HTTP 409 so the UI can
prompt the user to train first.
"""
from __future__ import annotations

import threading

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import config
from .blockchain import ledger, passport
from .data import loaders
from .forecasting import arima, lstm, storage_risk
from .intelligence import advisor, compliance, opportunity, readiness, xgb_readiness
from .processing import documents, pipeline

app = FastAPI(title="Tea Export Intelligence API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data is loaded + enriched once at startup; models are loaded lazily per request.
_DF = pipeline.build_national()
_COUNTRY_DF = loaders.load_country_exports()
_REQUIREMENTS = documents.parse_requirements()

_TRAIN_LOCK = threading.Lock()
_CACHE: dict[int, dict] = {}            # horizon -> core intelligence bundle
_DEMAND_CACHE: dict[int, list] = {}     # horizon -> per-country demand forecast


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _future_dates(horizon: int) -> list[str]:
    last = pd.to_datetime(_DF["date"].iloc[-1])
    return [(last + pd.DateOffset(months=i)).strftime("%Y-%m") for i in range(1, horizon + 1)]


def _require_models() -> None:
    if not (lstm.models_exist() and xgb_readiness.model_exists()):
        raise HTTPException(
            status_code=409,
            detail="No trained model yet. Train the models first (POST /api/train).",
        )


def _momentum_pct(values, short: int = 3, long: int = 12) -> float:
    s = values[-short:].mean()
    l = values[-long:].mean()
    return float(s / l - 1.0) * 100 if l else 0.0


def _compute(horizon: int) -> dict:
    """Forecast with saved models + derive all intelligence. Cached per horizon."""
    _require_models()
    if horizon in _CACHE:
        return _CACHE[horizon]

    meta = lstm.load_meta() or {"series": {}}

    # --- Forecasts: LSTM (production) + ARIMA (baseline) per national series ---
    forecasts = {}
    for name in config.NATIONAL_SERIES:
        s = meta["series"].get(name, {})
        forecasts[name] = {
            "forecast": lstm.load_and_forecast(name, _DF[name].tolist(), horizon),
            "metrics": s.get("metrics", {}),
            "backtest": s.get("backtest", []),
            "backtest_actual": s.get("backtest_actual", []),
            "arima": arima.national_compare(_DF[name].tolist(), horizon),
        }

    # --- Export Readiness Index (exact, closed-form) + XGBoost/SHAP estimate ---
    eri = readiness.compute_readiness(
        price_hist=_DF["auction_price_usd"].tolist(), price_fc=forecasts["auction_price_usd"]["forecast"],
        volume_hist=_DF["export_volume_kg"].tolist(), volume_fc=forecasts["export_volume_kg"]["forecast"],
        fx_hist=_DF["usd_lkr"].tolist(), fx_fc=forecasts["usd_lkr"]["forecast"],
    )
    xgb = xgb_readiness.predict_with_shap(_DF)
    risk = storage_risk.summarize(_DF["storage_risk"].tolist(), forecasts["storage_risk"]["forecast"])

    # --- Opportunity + recommendation across destinations ---
    national_price = float(_DF["auction_price_usd"].to_numpy()[-12:].mean())
    market_momentum = _momentum_pct(_DF["global_tea_price_index"].to_numpy())
    compliance_all = compliance.check_all()
    ranking = opportunity.ranked(_COUNTRY_DF, _REQUIREMENTS, compliance_all, national_price, market_momentum)
    recommendation = opportunity.recommend(ranking)

    # --- Generative advisor narrative (offline RAG by default) ---
    advice = advisor.advise({
        "eri": eri["eri"], "status": eri["status"], "readiness_action": eri["recommendation"],
        "recommendation": recommendation, "storage_risk": risk,
    })

    payload = {
        "horizon": horizon,
        "future_dates": _future_dates(horizon),
        "forecasts": forecasts,
        "readiness": eri,
        "readiness_xgb": xgb,
        "storage_risk": risk,
        "opportunity": ranking,
        "recommendation": recommendation,
        "advisor": advice,
        "compliance": compliance_all,
        "model_trained_at": meta.get("trained_at"),
    }
    _CACHE[horizon] = payload
    return payload


# --------------------------------------------------------------------------- #
# Infra
# --------------------------------------------------------------------------- #
@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "months_of_data": len(_DF),
        "countries": config.COUNTRIES,
        "models_trained": lstm.models_exist() and xgb_readiness.model_exists(),
        "llm_advisor": config.USE_LLM,
    }


@app.get("/api/model-status")
def model_status() -> dict:
    return {
        "trained": lstm.models_exist() and xgb_readiness.model_exists(),
        "lstm_trained": lstm.models_exist(),
        "xgb_trained": xgb_readiness.model_exists(),
        "meta": lstm.load_meta(),
    }


@app.post("/api/train")
def train() -> dict:
    """Train + save all LSTMs and the XGBoost readiness model. Slow (~40-60s)."""
    if not _TRAIN_LOCK.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Training already in progress.")
    try:
        meta = lstm.train_all(_DF)
        xgb_meta = xgb_readiness.train(_DF)
        _CACHE.clear()
        _DEMAND_CACHE.clear()
    finally:
        _TRAIN_LOCK.release()
    return {"status": "trained", "meta": meta, "xgb": xgb_meta}


# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #
@app.get("/api/history")
def history() -> dict:
    return {"data": loaders.records(_DF)}


@app.get("/api/countries")
def countries() -> dict:
    return {"countries": config.COUNTRIES, "requirements": _REQUIREMENTS}


# --------------------------------------------------------------------------- #
# Modules 1-3: forecasting (price / volume / FX / storage), LSTM vs ARIMA
# --------------------------------------------------------------------------- #
@app.get("/api/forecast")
def forecast(horizon: int = Query(6, ge=1, le=24)) -> dict:
    p = _compute(horizon)
    return {
        "horizon": horizon,
        "history": loaders.records(_DF),
        "future_dates": p["future_dates"],
        "forecasts": p["forecasts"],
        "storage_risk": p["storage_risk"],
        "model_trained_at": p["model_trained_at"],
    }


@app.get("/api/demand/countries")
def country_demand(horizon: int = Query(6, ge=1, le=24)) -> dict:
    """Module 1: country-wise export-demand forecast (one ARIMA per destination)."""
    _require_models()
    if horizon not in _DEMAND_CACHE:
        _DEMAND_CACHE[horizon] = [
            arima.country_demand(_COUNTRY_DF, c, horizon) for c in config.COUNTRIES
        ]
    return {"horizon": horizon, "future_dates": _future_dates(horizon), "countries": _DEMAND_CACHE[horizon]}


# --------------------------------------------------------------------------- #
# Module 4: Export Opportunity Map
# --------------------------------------------------------------------------- #
@app.get("/api/opportunity")
def get_opportunity(horizon: int = Query(6, ge=1, le=24)) -> dict:
    p = _compute(horizon)
    return {"horizon": horizon, "opportunity": p["opportunity"], "weights": opportunity.WEIGHTS}


# --------------------------------------------------------------------------- #
# Module 5: AI Country Recommendation
# --------------------------------------------------------------------------- #
@app.get("/api/recommendation")
def get_recommendation(horizon: int = Query(6, ge=1, le=24)) -> dict:
    p = _compute(horizon)
    return {
        "horizon": horizon,
        "recommendation": p["recommendation"],
        "advisor": p["advisor"],
        "opportunity": p["opportunity"],
    }


# --------------------------------------------------------------------------- #
# Module 6: Export Readiness & Compliance
# --------------------------------------------------------------------------- #
@app.get("/api/readiness")
def get_readiness(horizon: int = Query(6, ge=1, le=24)) -> dict:
    p = _compute(horizon)
    rec_country = p["recommendation"].get("country")
    return {
        "horizon": horizon,
        "readiness": p["readiness"],
        "readiness_xgb": p["readiness_xgb"],
        "storage_risk": p["storage_risk"],
        "compliance": p["compliance"].get(rec_country),
        "compliance_all": p["compliance"],
    }


@app.get("/api/compliance")
def get_compliance(country: str = Query(...)) -> dict:
    """Module 6: compliance checklist + risk for a specific destination."""
    if country not in _REQUIREMENTS:
        raise HTTPException(status_code=404, detail=f"Unknown destination: {country}")
    return {"compliance": compliance.check(country)}


# --------------------------------------------------------------------------- #
# Module 7: Blockchain Digital Passport
# --------------------------------------------------------------------------- #
class ShipmentRequest(BaseModel):
    estate: str = "Nuwara Eliya Estate"
    grade: str = "BOPF"
    volume_kg: int = 5000
    destination: str = "Germany"
    moisture_pct: float = 6.2
    pesticide_ppm: float = 0.02
    certifications: list[str] = ["ISO 22000", "Halal"]


@app.post("/api/passport")
def create_passport(req: ShipmentRequest) -> dict:
    """Run compliance, enforce the smart-contract gate, and record the passport on-chain."""
    if req.destination not in _REQUIREMENTS:
        raise HTTPException(status_code=404, detail=f"Unknown destination: {req.destination}")

    lot = {
        "grade": req.grade, "moisture_pct": req.moisture_pct,
        "pesticide_ppm": req.pesticide_ppm, "certifications": req.certifications,
    }
    comp = compliance.check(req.destination, lot)
    eri = _CACHE.get(6, {}).get("readiness", {}).get("eri")

    shipment = {
        "estate": req.estate, "grade": req.grade, "volume_kg": req.volume_kg,
        "destination": req.destination, "compliance_passed": comp["passed"],
        "certifications": req.certifications, "eri": eri,
    }
    try:
        result = passport.create_passport(shipment)
    except ledger.SmartContractError as e:
        # Smart-contract rejection (e.g. failed compliance) -> 400 with the reason + checklist.
        raise HTTPException(status_code=400, detail={"reason": str(e), "compliance": comp})
    return {**result, "compliance": comp}


@app.get("/api/passport/chain")
def passport_chain() -> dict:
    return {"chain": ledger.get_chain(), "integrity": ledger.verify_chain()}


@app.get("/api/passport/{passport_id}")
def get_passport(passport_id: str) -> dict:
    result = passport.get_passport(passport_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Passport not found: {passport_id}")
    return result


# --------------------------------------------------------------------------- #
# Overview bundle (landing page)
# --------------------------------------------------------------------------- #
@app.get("/api/dashboard")
def dashboard(horizon: int = Query(6, ge=1, le=24)) -> dict:
    """Everything the overview page needs in a single request (uses saved models)."""
    p = _compute(horizon)
    return {"history": loaders.records(_DF), **p}
