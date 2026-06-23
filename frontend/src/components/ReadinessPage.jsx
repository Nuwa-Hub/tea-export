import { fetchReadiness } from "../api";
import { useApi } from "../hooks";
import CompliancePanel from "./CompliancePanel";
import NeedsTraining from "./NeedsTraining";
import ReadinessCard from "./ReadinessCard";
import ShapBars from "./ShapBars";

const RISK_COLOR = { Low: "#2e7d32", Moderate: "#ed9b00", High: "#c0392b" };

export default function ReadinessPage({ horizon, goTrain }) {
  const { data, loading, error, needsTraining } = useApi(() => fetchReadiness(horizon), [horizon]);

  if (needsTraining) return <NeedsTraining goTrain={goTrain} />;
  if (loading) return <p className="muted">Computing readiness…</p>;
  if (error) return <p className="error">⚠ {error}</p>;
  if (!data) return null;

  const xgb = data.readiness_xgb || {};
  const risk = data.storage_risk || {};

  return (
    <div className="page">
      <ReadinessCard readiness={data.readiness} />

      <div className="grid">
        <div className="card">
          <h3>XGBoost readiness estimate + SHAP</h3>
          <p className="muted">
            Learned estimate of the index from current conditions:{" "}
            <strong>{xgb.predicted_eri}</strong>/100 (model base {xgb.base_value}).
          </p>
          <ShapBars contributions={xgb.contributions} />
          <p className="hint">Exact per-feature TreeSHAP contributions (XGBoost native).</p>
        </div>

        <div className="card">
          <h3>Storage risk forecast</h3>
          <div className="risk-block">
            <div className="eri-score" style={{ color: RISK_COLOR[risk.level] }}>
              {risk.forecast_avg}<span className="eri-max">/100</span>
            </div>
            <span className="pill" style={{ background: RISK_COLOR[risk.level], color: "#fff" }}>
              {risk.level} risk
            </span>
          </div>
          <p className="muted">{risk.note}</p>
          <p className="hint">Current {risk.current} · forecast peak {risk.peak} (month {risk.peak_month}).</p>
        </div>
      </div>

      <CompliancePanel compliance={data.compliance} />
    </div>
  );
}
