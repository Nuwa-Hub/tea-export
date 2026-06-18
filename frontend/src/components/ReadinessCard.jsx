// Big Export Readiness Index panel: score, status, recommendation and the
// weighted component breakdown that produced the score.

const STATUS_COLOR = {
  Ready: "#2e7d32",
  Conditional: "#ed9b00",
  "Not Ready": "#c62828",
};

const COMPONENT_LABELS = {
  demand: "Demand (volume ↑)",
  price: "Price trend",
  exchange: "FX outlook",
  risk: "Stability (low risk)",
};

function Bar({ label, value, weight }) {
  return (
    <div className="bar-row">
      <span className="bar-label">
        {label} <em>({Math.round(weight * 100)}%)</em>
      </span>
      <div className="bar-track">
        <div className="bar-fill" style={{ width: `${value}%` }} />
      </div>
      <span className="bar-value">{value}</span>
    </div>
  );
}

export default function ReadinessCard({ readiness }) {
  const { eri, status, recommendation, components, weights } = readiness;
  const color = STATUS_COLOR[status] || "#555";

  return (
    <div className="card readiness">
      <div className="eri-block">
        <div className="eri-score" style={{ color }}>
          {eri}
          <span className="eri-max">/100</span>
        </div>
        <div className="eri-status" style={{ background: color }}>
          {status}
        </div>
      </div>
      <div className="eri-detail">
        <h3>Export Readiness Index</h3>
        <p className="eri-reco">{recommendation}</p>
        <div className="bars">
          {Object.keys(components).map((k) => (
            <Bar key={k} label={COMPONENT_LABELS[k] || k} value={components[k]} weight={weights[k]} />
          ))}
        </div>
      </div>
    </div>
  );
}
