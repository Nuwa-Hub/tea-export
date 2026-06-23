# 🍃 AI-Powered Tea Export Intelligence Platform

Decision-support platform for **Sri Lanka Ceylon-tea exports** — the full
**"Component 04"** architecture, implemented end-to-end on synthetic data so it
runs entirely **offline**.

```
INPUT            PROCESSING           MODELS                       OUTPUT (7 modules)
volumes          cleaning             ARIMA + LSTM (price/vol/FX)  1 Export demand (country-wise)
auction prices   integration          Storage-risk LSTM           2 Auction price forecast
exchange rates   feature engineering  XGBoost readiness + SHAP    3 FX rate forecast
weather          PDF/doc parsing      RAG advisor (+ LLM toggle)  4 Export opportunity map
market data                           simulated blockchain        5 AI country recommendation
buyer reqs                                                         6 Readiness & compliance
                                                                   7 Blockchain digital passport
```

- **Backend** — FastAPI. statsmodels **ARIMA** + Keras **LSTM** forecasts,
  **XGBoost** Export-Readiness model with native **TreeSHAP** explanations, a
  TF-IDF **RAG advisor**, country **opportunity scoring**, a **compliance** engine,
  and a **simulated hash-chained ledger** with QR digital passports.
- **Frontend** — React (Vite) dashboard with seven module-aligned tabs.

> All data is **synthetic** (`backend/app/data/generate.py`). Swap in real Sri
> Lanka Tea Board / Central Bank CSVs later — the column names are the only
> contract; nothing downstream changes.

---

## What is real vs. simulated

| Capability | Implementation |
|---|---|
| Auction price / volume / FX / storage-risk forecasts | **Real** Keras LSTM + statsmodels ARIMA baseline (compared on a back-test) |
| Country-wise demand | **Real** ARIMA per destination |
| Export Readiness Index | **Real** weighted index **and** an XGBoost model that learns it |
| Explainable AI ("why") | **Real** XGBoost native **TreeSHAP** + additive opportunity contributions |
| Generative AI advisor | **Offline** TF-IDF RAG + templated narrative by default; **optional** Claude API via `USE_LLM=1` |
| Blockchain traceability | **Simulated** SHA-256 hash-chained permissioned ledger + smart-contract gate + QR (not real Hyperledger Fabric) |
| PDF parsing of buyer requirements | Structured JSON stand-in with a documented `pypdf` seam |

---

## Project layout

```
backend/app/
  config.py                 # paths, series, countries, USE_LLM flag
  main.py                   # FastAPI routes (grouped by the 7 modules)
  data/      generate.py    # synthetic generators   loaders.py
  processing/ pipeline.py   # clean / integrate / feature-engineer + storage-risk
              documents.py  # buyer-requirements + PDF-parsing seam + knowledge base
  forecasting/ lstm.py      # generalised LSTM engine (train/forecast)
               arima.py     # ARIMA baselines + per-country demand
               storage_risk.py
  intelligence/ readiness.py    # ERI weighted index
                xgb_readiness.py # XGBoost + TreeSHAP
                compliance.py    # buyer-requirement checks + risk
                opportunity.py   # suitability scoring + recommendation
                advisor.py       # RAG + NL generation (offline / LLM)
                explain.py       # SHAP-contribution formatting
  blockchain/ ledger.py     # hash-chained ledger + smart-contract gate
              passport.py   # digital passport + QR (SVG)
backend/data/               # generated CSV/JSON + knowledge_base/*.txt + ledger.json
backend/models/             # saved .keras + scalers + xgb_readiness.json + meta
frontend/src/               # App.jsx + components/ (one page per module)
```

---

## Run the backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate    # or reuse the repo .venv
pip install -r requirements.txt

# regenerate the synthetic data (optional — done automatically on first run)
python -m app.data.generate

uvicorn app.main:app --port 8000
```

Swagger docs at <http://localhost:8000/docs>. Train once, then everything is instant.

| Endpoint | Module |
|---|---|
| `POST /api/train` | trains 4 LSTMs + XGBoost (~40-60s, one-off) |
| `GET /api/forecast?horizon=6` | price / volume / FX / storage (LSTM + ARIMA) |
| `GET /api/demand/countries?horizon=6` | country-wise demand (ARIMA) |
| `GET /api/opportunity?horizon=6` | destination suitability scores |
| `GET /api/recommendation?horizon=6` | best country + SHAP "why" + advisor |
| `GET /api/readiness?horizon=6` | ERI + XGBoost/SHAP + storage risk + compliance |
| `GET /api/compliance?country=Japan` | per-country compliance checklist |
| `POST /api/passport` | issue a blockchain digital passport (QR) |
| `GET /api/passport/chain` | the ledger + integrity verification |
| `GET /api/dashboard?horizon=6` | overview bundle (used by the landing page) |

> Forecast endpoints return **HTTP 409** until the models are trained, so the UI
> can prompt you to train first.

## Run the frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

The dev server runs on port **5173** (allowed by the backend's CORS config).
Point it at a non-default backend with `VITE_API_URL=http://localhost:8001 npm run dev`.

---

## Optional: real LLM advisor

The advisor is offline by default. To route its narrative through Claude:

```bash
export USE_LLM=1
export ANTHROPIC_API_KEY=sk-ant-...
pip install anthropic           # optional dependency
# (override the model with LLM_MODEL=...)
```

Any failure (no key, no network) transparently falls back to the offline
template, so the app never breaks.

---

## The Export Readiness Index (ERI)

`backend/app/intelligence/readiness.py` turns forecasts into a 0–100 score:

```
ERI = 0.40*demand + 0.30*price + 0.20*exchange + 0.10*stability
```

| Score | Status | Meaning |
|---|---|---|
| 80–100 | **Ready** | proceed with export planning |
| 60–79 | **Conditional** | viable, but monitor price/demand |
| < 60 | **Not Ready** | hold for better conditions |

The XGBoost model in `xgb_readiness.py` learns this index from engineered
features so it can be explained with TreeSHAP — the index stays the ground truth.

## Where to take it next

1. **Real data** — replace the generators with Sri Lanka Tea Board / Central Bank CSVs.
2. **Real PDF parsing** — wire `pypdf` into `processing/documents.parse_requirements()`.
3. **Real LLM advisor** — set `USE_LLM=1` with an API key.
4. **Real blockchain** — swap the simulated ledger for Hyperledger Fabric chaincode
   (the `blockchain/` API mirrors what chaincode would expose).
