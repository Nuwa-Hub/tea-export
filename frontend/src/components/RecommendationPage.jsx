import { fetchRecommendation } from "../api";
import { useApi } from "../hooks";
import NeedsTraining from "./NeedsTraining";
import ShapBars from "./ShapBars";

export default function RecommendationPage({ horizon, goTrain }) {
  const { data, loading, error, needsTraining } = useApi(() => fetchRecommendation(horizon), [horizon]);

  if (needsTraining) return <NeedsTraining goTrain={goTrain} />;
  if (loading) return <p className="muted">Generating recommendation…</p>;
  if (error) return <p className="error">⚠ {error}</p>;
  if (!data) return null;

  const rec = data.recommendation || {};
  const advisor = data.advisor || {};
  // The "why" = best country's full contribution list from the opportunity model.
  const best = (data.opportunity || []).find((o) => o.country === rec.country);

  return (
    <div className="page">
      <div className="card recommend">
        <div className="recommend-head">
          <div>
            <span className="muted">AI-recommended destination</span>
            <h2 className="recommend-country">{rec.country}</h2>
          </div>
          <div className="recommend-score">
            <div className="eri-score" style={{ color: "#2e7d32" }}>
              {rec.suitability}<span className="eri-max">/100</span>
            </div>
            <span className="pill ok">{rec.status} suitability</span>
          </div>
        </div>
        {rec.runner_up && (
          <p className="muted">Next-best alternative: <strong>{rec.runner_up}</strong>.</p>
        )}
        {rec.compliance_passed === false && (
          <p className="error">⚠ The representative lot does not yet meet this market's mandatory requirements.</p>
        )}
      </div>

      <div className="card">
        <h3>Why this market? (explainable scoring)</h3>
        {best && <ShapBars contributions={best.contributions} />}
        <p className="hint">
          Each bar is a driver's additive contribution to the suitability score
          (green raises it, red lowers it).
        </p>
      </div>

      <div className="card advisor-panel">
        <h3>🧭 Generative AI advisor</h3>
        <p className="advisor-text">{advisor.narrative}</p>
        <div className="advisor-meta">
          <span className={`pill ${advisor.generator === "llm" ? "ok" : "neutral"}`}>
            {advisor.generator === "llm" ? "Claude (LLM)" : "Offline template + RAG"}
          </span>
          {advisor.citations?.map((c) => (
            <span key={c.source} className="cite">📄 {c.source} ({c.score})</span>
          ))}
        </div>
      </div>
    </div>
  );
}
