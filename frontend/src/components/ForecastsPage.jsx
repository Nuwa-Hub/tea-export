import { useState } from "react";
import { fetchCountryDemand, fetchForecast } from "../api";
import { useApi } from "../hooks";
import CountryDemandChart from "./CountryDemandChart";
import ForecastChart from "./ForecastChart";
import MetricsTable from "./MetricsTable";
import NeedsTraining from "./NeedsTraining";

const SERIES = [
  { key: "auction_price_usd", title: "Auction price (USD/kg)", color: "#2e7d32" },
  { key: "export_volume_kg", title: "Export volume (kg)", color: "#1565c0" },
  { key: "usd_lkr", title: "USD/LKR exchange rate", color: "#6a1b9a" },
  { key: "storage_risk", title: "Storage risk index (0-100)", color: "#c0392b" },
];

export default function ForecastsPage({ horizon, goTrain }) {
  const [showArima, setShowArima] = useState(true);
  const fc = useApi(() => fetchForecast(horizon), [horizon]);
  const demand = useApi(() => fetchCountryDemand(horizon), [horizon]);

  if (fc.needsTraining) return <NeedsTraining goTrain={goTrain} />;
  if (fc.loading) return <p className="muted">Loading forecasts…</p>;
  if (fc.error) return <p className="error">⚠ {fc.error}</p>;
  if (!fc.data) return null;

  const { forecasts, future_dates } = fc.data;
  return (
    <div className="page">
      <div className="controls">
        <label className="toggle">
          <input type="checkbox" checked={showArima} onChange={(e) => setShowArima(e.target.checked)} />
          &nbsp;Show ARIMA baseline
        </label>
        <span className="hint">Modules 1-3: auction price · export volume · FX · storage risk</span>
      </div>

      <div className="grid">
        {SERIES.map((s) => (
          <ForecastChart key={s.key} title={s.title} history={fc.data.history || []} field={s.key}
            futureDates={future_dates} lstm={forecasts[s.key].forecast}
            arima={forecasts[s.key].arima?.forecast} color={s.color} showArima={showArima} />
        ))}
      </div>

      <MetricsTable forecasts={forecasts} />

      {demand.data && <CountryDemandChart countries={demand.data.countries} />}
    </div>
  );
}
