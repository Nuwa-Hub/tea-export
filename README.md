# 🍃 Tea Export Forecasting & Readiness

A starter scaffold for the research project
**"AI-Powered Tea Export Decision Support for Sri Lanka."**

This first stage implements the pipeline **up to the Export Readiness Index**:

```
dummy data  ->  LSTM forecasts (price / volume / FX)  ->  Export Readiness Index
```

- **Backend** — FastAPI + TensorFlow/Keras LSTM (univariate, multi-step) + a
  weighted Export Readiness Index engine.
- **Frontend** — React (Vite) dashboard: forecast charts, back-test accuracy,
  and the Export Readiness Index with its component breakdown.

> The data is **synthetic** (`backend/app/data.py`) so the whole thing runs
> offline. Swap in real Sri Lanka Tea Board / Central Bank CSVs later — the
> rest of the pipeline does not change.

---

## Project layout

```
backend/
  app/
    data.py          # synthetic monthly dataset (price, volume, USD/LKR)
    forecasting.py   # LSTM: scale -> window -> train -> recursive forecast + back-test
    readiness.py     # Export Readiness Index (the research-contribution layer)
    main.py          # FastAPI routes + in-memory forecast cache
  requirements.txt
frontend/
  src/
    App.jsx          # dashboard
    api.js           # backend client
    components/      # ForecastChart, ReadinessCard, MetricsTable
```

---

## Run the backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# from the backend/ directory:
uvicorn app.main:app --reload --port 8000
```

API docs (Swagger) at <http://localhost:8000/docs>. Key endpoints:

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | liveness |
| `GET /api/history` | the raw monthly dataset |
| `GET /api/forecast?horizon=6` | LSTM forecasts + accuracy |
| `GET /api/readiness?horizon=6` | Export Readiness Index only |
| `GET /api/dashboard?horizon=6` | everything in one call (used by the UI) |
| `POST /api/retrain` | clear the cache and retrain on next request |

> The **first** forecast request trains three LSTMs (price, volume, FX) and is
> cached per horizon, so it takes a few seconds; later requests are instant.

## Run the frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

The dev server runs on port **5173**, which the backend's CORS config allows.
Start the backend first.

---

## The Export Readiness Index (ERI)

`backend/app/readiness.py` turns the raw forecasts into a 0–100 decision score:

```
ERI = 0.40 * demand   (forecast export-volume growth)
    + 0.30 * price     (forecast auction-price trend)
    + 0.20 * exchange  (USD/LKR outlook — depreciation favours exporters)
    + 0.10 * stability (inverse of recent price volatility)
```

| Score | Status | Meaning |
|---|---|---|
| 80–100 | **Ready** | proceed with export planning |
| 60–79 | **Conditional** | viable, but monitor price/demand |
| < 60 | **Not Ready** | hold for better conditions |

The weights and component formulas are a defensible starting point — tuning and
validating them is a natural part of the research write-up.

---

## Where to take it next (per the road-map)

1. **Real data** — replace `generate_dataset()` with a CSV loader.
2. **ARIMA / ARIMAX baselines** — add `statsmodels` and compare MAE/RMSE/MAPE
   against the LSTM (the comparison is itself a research contribution).
3. **Multivariate LSTM** — feed price + volume + FX + weather together.
4. Later phases (RAG advisor, blockchain certification) build on top of this
   forecasting + readiness core.
