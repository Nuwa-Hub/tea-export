import { useEffect, useState } from "react";
import { getModelStatus, trainModels } from "../api";

const SERIES_LABELS = {
  auction_price_usd: "Auction price (USD/kg)",
  export_volume_kg: "Export volume (kg)",
  usd_lkr: "USD/LKR rate",
  storage_risk: "Storage risk index",
};

function fmtDate(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export default function TrainPage({ onTrained }) {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [training, setTraining] = useState(false);
  const [error, setError] = useState(null);

  async function refresh() {
    setLoading(true);
    try {
      setStatus(await getModelStatus());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    refresh();
  }, []);

  async function handleTrain() {
    setTraining(true);
    setError(null);
    try {
      await trainModels();
      await refresh();
      onTrained?.();
    } catch (e) {
      setError(e.message);
    } finally {
      setTraining(false);
    }
  }

  const trained = status?.trained;
  const meta = status?.meta;

  return (
    <div className="page">
      <div className="card">
        <h3>Model training</h3>
        <p className="muted">
          Training fits four LSTMs (auction price, export volume, USD/LKR, storage risk) plus an
          XGBoost readiness model, and saves them to <code>backend/models/</code>. Every module
          then loads these saved models, so the platform serves instantly. Retrain only when the
          data changes.
        </p>

        <div className="status-line">
          {loading ? (
            <span className="muted">Checking status…</span>
          ) : (
            <>
              <span className={status?.lstm_trained ? "badge ok" : "badge warn"}>
                ● LSTM {status?.lstm_trained ? "trained" : "not trained"}
              </span>
              &nbsp;&nbsp;
              <span className={status?.xgb_trained ? "badge ok" : "badge warn"}>
                ● XGBoost {status?.xgb_trained ? "trained" : "not trained"}
              </span>
              {trained && meta && (
                <span className="muted">
                  &nbsp;· last trained {fmtDate(meta.trained_at)} · {meta.epochs} epochs ·{" "}
                  {meta.n_observations} months
                </span>
              )}
            </>
          )}
        </div>

        <button className="primary" onClick={handleTrain} disabled={training}>
          {training ? "Training… (~40-60s, please wait)" : trained ? "Retrain models" : "Train models"}
        </button>
        {training && <p className="hint">Fitting 4 LSTMs + back-tests + XGBoost. This is the only slow step.</p>}
        {error && <p className="error">⚠ {error}</p>}
      </div>

      {trained && meta && (
        <div className="card">
          <h3>LSTM back-test accuracy (saved with the model)</h3>
          <div className="table-scroll">
            <table className="metrics">
              <thead>
                <tr><th>Series</th><th>MAE</th><th>RMSE</th><th>MAPE&nbsp;(%)</th></tr>
              </thead>
              <tbody>
                {Object.keys(meta.series).map((k) => {
                  const m = meta.series[k].metrics;
                  return (
                    <tr key={k}>
                      <td>{SERIES_LABELS[k] || k}</td>
                      <td>{m.MAE}</td>
                      <td>{m.RMSE}</td>
                      <td>{m.MAPE}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="hint">Measured on a held-out tail of each series (recursive multi-step forecast vs. actual).</p>
        </div>
      )}
    </div>
  );
}
