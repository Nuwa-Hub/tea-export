import { useState } from "react";
import DashboardPage from "./components/DashboardPage";
import TrainPage from "./components/TrainPage";

export default function App() {
  const [page, setPage] = useState("dashboard");
  // bumped after training so the dashboard refetches fresh forecasts
  const [trainedTick, setTrainedTick] = useState(0);

  return (
    <div className="app">
      <header>
        <h1>🍃 Tea Export Forecasting &amp; Readiness</h1>
        <p className="subtitle">
          LSTM forecasts of Colombo auction price, export volume and USD/LKR &rarr; Export Readiness Index
        </p>
        <nav className="tabs">
          <button
            className={page === "dashboard" ? "tab active" : "tab"}
            onClick={() => setPage("dashboard")}
          >
            Dashboard
          </button>
          <button
            className={page === "train" ? "tab active" : "tab"}
            onClick={() => setPage("train")}
          >
            Train Models
          </button>
        </nav>
      </header>

      {page === "dashboard" ? (
        <DashboardPage key={trainedTick} goTrain={() => setPage("train")} />
      ) : (
        <TrainPage
          onTrained={() => {
            setTrainedTick((t) => t + 1); // force dashboard to reload with new model
          }}
        />
      )}

      <footer>
        Dummy data &amp; baseline model — starter scaffold for the AI-powered tea-export research project.
      </footer>
    </div>
  );
}
