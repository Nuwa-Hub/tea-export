import { useEffect, useState } from "react";
import { fetchDashboard } from "./api";
import ForecastChart from "./components/ForecastChart";
import MetricsTable from "./components/MetricsTable";
import ReadinessCard from "./components/ReadinessCard";

export default function App() {
  const [horizon, setHorizon] = useState(6);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function load(h) {
    setLoading(true);
    setError(null);
    try {
      setData(await fetchDashboard(h));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  // Load once on mount with the default horizon.
  useEffect(() => {
    load(horizon);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="app">
      <header>
        <h1>🍃 Tea Export Forecasting &amp; Readiness</h1>
        <p className="subtitle">
          LSTM forecasts of Colombo auction price, export volume and USD/LKR &rarr; Export Readiness Index
        </p>
      </header>

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
        <button onClick={() => load(horizon)} disabled={loading}>
          {loading ? "Training LSTM…" : "Run forecast"}
        </button>
        {loading && <span className="hint">First run trains the models — this takes a few seconds.</span>}
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

      <footer>
        Dummy data &amp; baseline model — starter scaffold for the AI-powered tea-export research project.
      </footer>
    </div>
  );
}
