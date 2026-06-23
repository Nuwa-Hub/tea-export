import { useState } from "react";
import ForecastsPage from "./components/ForecastsPage";
import OpportunityMapPage from "./components/OpportunityMapPage";
import OverviewPage from "./components/OverviewPage";
import PassportPage from "./components/PassportPage";
import ReadinessPage from "./components/ReadinessPage";
import RecommendationPage from "./components/RecommendationPage";
import TrainPage from "./components/TrainPage";

const TABS = [
  { key: "overview", label: "Overview" },
  { key: "forecasts", label: "Forecasts" },
  { key: "opportunity", label: "Opportunity Map" },
  { key: "recommendation", label: "Recommendation" },
  { key: "readiness", label: "Readiness & Compliance" },
  { key: "passport", label: "Digital Passport" },
  { key: "train", label: "Train Models" },
];

// Pages that take a forecast horizon (everything except passport + train).
const HORIZON_PAGES = new Set(["overview", "forecasts", "opportunity", "recommendation", "readiness"]);

export default function App() {
  const [page, setPage] = useState("overview");
  const [horizon, setHorizon] = useState(6);
  const [trainedTick, setTrainedTick] = useState(0);

  const goTrain = () => setPage("train");
  const common = { horizon, goTrain };

  return (
    <div className="app">
      <header>
        <h1>🍃 Tea Export Intelligence Platform</h1>
        <p className="subtitle">
          ARIMA + LSTM forecasts · Export Readiness Index · Opportunity scoring · AI advisor ·
          Blockchain traceability — Sri Lanka Ceylon tea
        </p>
        <nav className="tabs">
          {TABS.map((t) => (
            <button key={t.key} className={page === t.key ? "tab active" : "tab"}
              onClick={() => setPage(t.key)}>
              {t.label}
            </button>
          ))}
        </nav>
        {HORIZON_PAGES.has(page) && (
          <div className="horizon-bar">
            <label>
              Forecast horizon:&nbsp;
              <select value={horizon} onChange={(e) => setHorizon(Number(e.target.value))}>
                {[3, 6, 9, 12].map((h) => <option key={h} value={h}>{h} months</option>)}
              </select>
            </label>
          </div>
        )}
      </header>

      <main key={`${page}-${trainedTick}`}>
        {page === "overview" && <OverviewPage {...common} />}
        {page === "forecasts" && <ForecastsPage {...common} />}
        {page === "opportunity" && <OpportunityMapPage {...common} />}
        {page === "recommendation" && <RecommendationPage {...common} />}
        {page === "readiness" && <ReadinessPage {...common} />}
        {page === "passport" && <PassportPage />}
        {page === "train" && (
          <TrainPage onTrained={() => { setTrainedTick((t) => t + 1); setPage("overview"); }} />
        )}
      </main>

      <footer>
        Dummy data · offline scaffold for the AI-Powered Tea Export Decision Support research project.
        Advisor defaults to offline RAG; blockchain is a simulated permissioned ledger.
      </footer>
    </div>
  );
}
