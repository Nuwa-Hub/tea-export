import { fetchOpportunity } from "../api";
import { useApi } from "../hooks";
import NeedsTraining from "./NeedsTraining";
import OpportunityMap from "./OpportunityMap";

const STATUS_CLASS = { High: "ok", Medium: "warn", Low: "bad" };

export default function OpportunityMapPage({ horizon, goTrain }) {
  const { data, loading, error, needsTraining } = useApi(() => fetchOpportunity(horizon), [horizon]);

  if (needsTraining) return <NeedsTraining goTrain={goTrain} />;
  if (loading) return <p className="muted">Scoring destinations…</p>;
  if (error) return <p className="error">⚠ {error}</p>;
  if (!data) return null;

  return (
    <div className="page">
      <OpportunityMap opportunity={data.opportunity} />

      <div className="card">
        <h3>Destination ranking</h3>
        <div className="table-scroll">
          <table className="metrics">
            <thead>
              <tr>
                <th>#</th><th>Destination</th><th>Suitability</th><th>Status</th>
                <th>Demand</th><th>Price prem.</th><th>Compliance</th><th>Tariff</th>
                <th>Outlook</th>
              </tr>
            </thead>
            <tbody>
              {data.opportunity.map((o, i) => (
                <tr key={o.country}>
                  <td>{i + 1}</td>
                  <td><strong>{o.country}</strong></td>
                  <td>{o.suitability}</td>
                  <td><span className={`pill ${STATUS_CLASS[o.status]}`}>{o.status}</span></td>
                  <td>{o.subscores.demand_growth}</td>
                  <td>{o.subscores.price_premium}</td>
                  <td>{o.compliance_passed ? "✅" : "❌"}</td>
                  <td>{o.import_tariff_pct}%</td>
                  <td className="muted">{o.demand_outlook}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="hint">
          Suitability = 0.35·demand + 0.20·price premium + 0.20·compliance ease + 0.15·low tariff
          + 0.10·market momentum (all 0-100).
        </p>
      </div>
    </div>
  );
}
