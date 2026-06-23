// Compliance checklist + risk for a destination: each buyer requirement is shown
// as a pass/fail row, with the overall verdict and a compliance-risk score.

export default function CompliancePanel({ compliance }) {
  if (!compliance) return null;
  const { country, passed, checks, compliance_risk, import_tariff_pct, demand_outlook, summary } = compliance;

  return (
    <div className="card">
      <div className="compliance-head">
        <h3>Compliance — {country}</h3>
        <span className={passed ? "badge ok" : "badge warn"}>
          {passed ? "✓ Export-ready" : "✗ Not compliant"}
        </span>
      </div>
      <p className="muted">{summary}</p>
      <table className="checklist">
        <tbody>
          {checks.map((c) => (
            <tr key={c.requirement}>
              <td className="chk-icon">{c.ok ? "✅" : "❌"}</td>
              <td className="chk-req">{c.requirement}</td>
              <td className="chk-need">req: {c.required}</td>
              <td className="chk-act">lot: {c.actual}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="compliance-foot">
        <span>Compliance risk: <strong>{compliance_risk}</strong>/100</span>
        <span>Import tariff: <strong>{import_tariff_pct}%</strong></span>
        <span>Demand outlook: <strong>{demand_outlook}</strong></span>
      </div>
    </div>
  );
}
