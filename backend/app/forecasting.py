"""
LSTM forecasting engine.

A small, self-contained univariate LSTM (Keras) that:

  1. scales a series to [0, 1],
  2. turns it into supervised look-back windows,
  3. trains an LSTM,
  4. forecasts `horizon` steps ahead recursively, and
  5. reports hold-out accuracy (MAE / RMSE / MAPE).

TensorFlow is imported lazily inside `_build_and_train` so the API process
starts instantly and non-forecast endpoints work even while TF is loading.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np
from sklearn.preprocessing import MinMaxScaler

# Quieten TensorFlow's startup chatter before it is imported anywhere.
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

LOOK_BACK = 12          # use the previous 12 months to predict the next
EPOCHS = 70             # enough for <4% MAPE on this data; keeps first call fast
EVAL_HOLDOUT = 12       # months held out at the tail to measure accuracy


@dataclass
class ForecastResult:
    horizon: int
    forecast: list[float]          # future values, length == horizon
    metrics: dict[str, float]      # MAE / RMSE / MAPE on the hold-out set
    backtest: list[float]          # model's prediction over the hold-out window
    backtest_actual: list[float]   # the matching actual values


def _make_windows(series: np.ndarray, look_back: int):
    """Turn a 1-D array into (X, y) supervised windows."""
    X, y = [], []
    for i in range(len(series) - look_back):
        X.append(series[i : i + look_back])
        y.append(series[i + look_back])
    X = np.array(X).reshape(-1, look_back, 1)
    y = np.array(y)
    return X, y


def _build_and_train(train_scaled: np.ndarray, look_back: int, epochs: int):
    """Build and fit a fresh LSTM. Returns the trained Keras model."""
    # Lazy, seeded import so results are reproducible run-to-run.
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
    """Predict `steps` ahead, feeding each prediction back as input."""
    window = list(history_scaled[-look_back:])
    preds = []
    for _ in range(steps):
        x = np.array(window[-look_back:]).reshape(1, look_back, 1)
        nxt = float(model.predict(x, verbose=0)[0, 0])
        preds.append(nxt)
        window.append(nxt)
    return np.array(preds)


def forecast_series(
    values: list[float],
    horizon: int = 6,
    look_back: int = LOOK_BACK,
    epochs: int = EPOCHS,
) -> ForecastResult:
    """
    Forecast one series `horizon` months ahead.

    Step 1 — back-test: train on everything except the last `EVAL_HOLDOUT`
             months, forecast that window, and score it (honest accuracy).
    Step 2 — train on the FULL series and forecast the real future.
    """
    series = np.asarray(values, dtype="float64").reshape(-1, 1)
    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(series).flatten()

    # ---- Step 1: back-test on a hold-out tail ----------------------------
    holdout = min(EVAL_HOLDOUT, max(3, len(scaled) // 4))
    train_scaled = scaled[:-holdout]
    bt_model = _build_and_train(train_scaled, look_back, epochs)
    bt_pred_scaled = _recursive_forecast(bt_model, train_scaled, holdout, look_back)

    bt_pred = scaler.inverse_transform(bt_pred_scaled.reshape(-1, 1)).flatten()
    bt_actual = series[-holdout:].flatten()
    metrics = _score(bt_actual, bt_pred)

    # ---- Step 2: retrain on all data, forecast the future ----------------
    full_model = _build_and_train(scaled, look_back, epochs)
    fut_scaled = _recursive_forecast(full_model, scaled, horizon, look_back)
    future = scaler.inverse_transform(fut_scaled.reshape(-1, 1)).flatten()

    return ForecastResult(
        horizon=horizon,
        forecast=[round(float(v), 3) for v in future],
        metrics=metrics,
        backtest=[round(float(v), 3) for v in bt_pred],
        backtest_actual=[round(float(v), 3) for v in bt_actual],
    )


def _score(actual: np.ndarray, pred: np.ndarray) -> dict[str, float]:
    err = actual - pred
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err**2)))
    mape = float(np.mean(np.abs(err / np.where(actual == 0, np.nan, actual))) * 100)
    return {
        "MAE": round(mae, 3),
        "RMSE": round(rmse, 3),
        "MAPE": round(mape, 2),
    }
