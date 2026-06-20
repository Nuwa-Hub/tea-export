"""
LSTM forecasting engine — split into TRAIN (slow, once) and FORECAST (fast, many).

Training
    train_all(df)  trains one LSTM per series, runs an honest hold-out back-test,
    and SAVES each model (.keras) + its scaler (.pkl) to backend/models/, plus a
    training_meta.json holding accuracy metrics and the back-test arrays.

Forecasting
    load_and_forecast(name, values, horizon)  loads the saved model + scaler and
    only runs inference (recursive multi-step). No training -> milliseconds.

This is why the dashboard is instant: it never trains, it just loads.
TensorFlow is imported lazily so the API process starts quickly.
"""
from __future__ import annotations

import json
import os
import pickle
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.preprocessing import MinMaxScaler

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

LOOK_BACK = 12          # use the previous 12 months to predict the next
EPOCHS = 70
EVAL_HOLDOUT = 12       # months held out at the tail to measure accuracy

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
META_PATH = MODELS_DIR / "training_meta.json"

# The three series we forecast (column name in the dataframe).
SERIES = ["auction_price_usd", "export_volume_kg", "usd_lkr"]


# --------------------------------------------------------------------------- #
# Low-level helpers
# --------------------------------------------------------------------------- #
def _make_windows(series: np.ndarray, look_back: int):
    X, y = [], []
    for i in range(len(series) - look_back):
        X.append(series[i : i + look_back])
        y.append(series[i + look_back])
    return np.array(X).reshape(-1, look_back, 1), np.array(y)


def _build_and_train(train_scaled: np.ndarray, look_back: int, epochs: int):
    import tensorflow as tf
    from tensorflow.keras.layers import LSTM, Dense, Input
    from tensorflow.keras.models import Sequential

    tf.random.set_seed(42)
    np.random.seed(42)

    X, y = _make_windows(train_scaled, look_back)
    model = Sequential(
        [
            Input(shape=(look_back, 1)),
            LSTM(32, activation="tanh"),
            Dense(16, activation="relu"),
            Dense(1),
        ]
    )
    model.compile(optimizer="adam", loss="mse")
    model.fit(X, y, epochs=epochs, batch_size=8, verbose=0)
    return model


def _recursive_forecast(model, history_scaled: np.ndarray, steps: int, look_back: int):
    window = list(history_scaled[-look_back:])
    preds = []
    for _ in range(steps):
        x = np.array(window[-look_back:]).reshape(1, look_back, 1)
        nxt = float(model.predict(x, verbose=0)[0, 0])
        preds.append(nxt)
        window.append(nxt)
    return np.array(preds)


def _score(actual: np.ndarray, pred: np.ndarray) -> dict[str, float]:
    err = actual - pred
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err**2)))
    mape = float(np.mean(np.abs(err / np.where(actual == 0, np.nan, actual))) * 100)
    return {"MAE": round(mae, 3), "RMSE": round(rmse, 3), "MAPE": round(mape, 2)}


# --------------------------------------------------------------------------- #
# TRAIN (slow) — called by POST /api/train
# --------------------------------------------------------------------------- #
def _train_one(values: list[float], look_back: int, epochs: int):
    """Train one series; return (production_model, scaler, metrics, backtest, actual)."""
    series = np.asarray(values, dtype="float64").reshape(-1, 1)
    holdout = min(EVAL_HOLDOUT, max(3, len(series) // 4))

    # --- Back-test with its OWN scaler fit only on the training part -------
    # (fitting the scaler on the full series would leak test-range info).
    bt_scaler = MinMaxScaler().fit(series[:-holdout])
    bt_train = bt_scaler.transform(series[:-holdout]).flatten()
    bt_model = _build_and_train(bt_train, look_back, epochs)
    bt_pred_scaled = _recursive_forecast(bt_model, bt_train, holdout, look_back)
    bt_pred = bt_scaler.inverse_transform(bt_pred_scaled.reshape(-1, 1)).flatten()
    bt_actual = series[-holdout:].flatten()
    metrics = _score(bt_actual, bt_pred)

    # --- Production model: scaler + LSTM fit on the FULL series ------------
    scaler = MinMaxScaler().fit(series)
    scaled = scaler.transform(series).flatten()
    model = _build_and_train(scaled, look_back, epochs)

    return (
        model,
        scaler,
        metrics,
        [round(float(v), 3) for v in bt_pred],
        [round(float(v), 3) for v in bt_actual],
    )


def train_all(df, look_back: int = LOOK_BACK, epochs: int = EPOCHS) -> dict:
    """Train + save every series. Returns the training_meta dict."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    meta = {
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "look_back": look_back,
        "epochs": epochs,
        "n_observations": int(len(df)),
        "series": {},
    }

    for name in SERIES:
        model, scaler, metrics, backtest, actual = _train_one(
            df[name].tolist(), look_back, epochs
        )
        model.save(MODELS_DIR / f"{name}.keras")
        with open(MODELS_DIR / f"{name}.scaler.pkl", "wb") as fh:
            pickle.dump(scaler, fh)
        meta["series"][name] = {
            "metrics": metrics,
            "backtest": backtest,
            "backtest_actual": actual,
        }

    with open(META_PATH, "w") as fh:
        json.dump(meta, fh, indent=2)
    return meta


# --------------------------------------------------------------------------- #
# FORECAST (fast) — called by the dashboard
# --------------------------------------------------------------------------- #
def models_exist() -> bool:
    return META_PATH.exists() and all(
        (MODELS_DIR / f"{n}.keras").exists() for n in SERIES
    )


def load_meta() -> dict | None:
    if not META_PATH.exists():
        return None
    with open(META_PATH) as fh:
        return json.load(fh)


def load_and_forecast(name: str, values: list[float], horizon: int) -> list[float]:
    """Load the saved model + scaler and forecast `horizon` steps (inference only)."""
    from tensorflow.keras.models import load_model

    model = load_model(MODELS_DIR / f"{name}.keras")
    with open(MODELS_DIR / f"{name}.scaler.pkl", "rb") as fh:
        scaler = pickle.load(fh)

    series = np.asarray(values, dtype="float64").reshape(-1, 1)
    scaled = scaler.transform(series).flatten()
    fut_scaled = _recursive_forecast(model, scaled, horizon, LOOK_BACK)
    future = scaler.inverse_transform(fut_scaled.reshape(-1, 1)).flatten()
    return [round(float(v), 3) for v in future]
