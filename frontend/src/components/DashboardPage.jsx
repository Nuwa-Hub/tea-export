import { useEffect, useState } from "react";
import { fetchDashboard } from "../api";
import ForecastChart from "./ForecastChart";
import MetricsTable from "./MetricsTable";
import ReadinessCard from "./ReadinessCard";

export default function DashboardPage({ goTrain }) {
  const [horizon, setHorizon] = useState(6);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [needsTraining, setNeedsTraining] = useState(false);

  async function load(h) {
    setLoading(true);
    setError(null);
    setNeedsTraining(false);
    try {
      setData(await fetchDashboard(h));
    } catch (e) {
      if (e.code === 409) {
        setNeedsTraining(true);
        setData(null);
      } else {
        setError(e.message);
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load(horizon);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (needsTraining) {
    return (
      <div className="card notice">
        <h3>No trained model yet</h3>
        <p className="muted">
          The dashboard loads a saved LSTM model — but none exists yet. Train the models
          once and the forecasts will appear here (and load instantly afterwards).
        </p>
        <button className="primary" onClick={goTrain}>
          Go to Train Models →
        </button>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="controls">
        <label>
          Forecast horizon:&nbsp;
          <select value={horizon} onChange={(e) => setHorizon(Number(e.target.value))}>
            {[3, 6, 9, 12].map((h) => (
              <option key={h} value={h}>
                {h} months
              </option>
            ))}
          </select>
        </label>
        <button className="primary" onClick={() => load(horizon)} disabled={loading}>
          {loading ? "Loading…" : "Run forecast"}
        </button>
        {data?.model_trained_at && (
          <span className="hint">
            model trained {new Date(data.model_trained_at).toLocaleString()}
          </span>
        )}
        {error && <span className="error">⚠ {error}</span>}
      </div>

      {data && (
        <>
          <ReadinessCard readiness={data.readiness} />
          <div className="grid">
            <ForecastChart
              title="Auction price (USD/kg)"
              history={data.history}
              field="auction_price_usd"
              futureDates={data.future_dates}
              forecast={data.forecasts.auction_price_usd.forecast}
              color="#2e7d32"
            />
            <ForecastChart
              title="Export volume (kg)"
              history={data.history}
              field="export_volume_kg"
              futureDates={data.future_dates}
              forecast={data.forecasts.export_volume_kg.forecast}
              color="#1565c0"
            />
            <ForecastChart
              title="USD/LKR exchange rate"
              history={data.history}
              field="usd_lkr"
              futureDates={data.future_dates}
              forecast={data.forecasts.usd_lkr.forecast}
              color="#6a1b9a"
            />
            <MetricsTable forecasts={data.forecasts} />
          </div>
        </>
      )}
    </div>
  );
}
