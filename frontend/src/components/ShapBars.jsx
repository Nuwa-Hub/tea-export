// Reusable "why" panel: renders per-feature contributions (from XGBoost TreeSHAP
// or the additive opportunity model) as diverging bars — green pushes the score
// up, red pulls it down. Used by Recommendation and Readiness.

export default function ShapBars({ contributions, max }) {
  const items = contributions || [];
  const scale = max || Math.max(1, ...items.map((c) => Math.abs(c.contribution)));

  return (
    <div className="shap">
      {items.map((c) => {
        const pct = (Math.abs(c.contribution) / scale) * 100;
        const up = c.direction === "up";
        return (
          <div className="shap-row" key={c.feature}>
            <span className="shap-label">{c.label}</span>
            <div className="shap-track">
              <div className="shap-mid" />
              <div
                className={up ? "shap-fill up" : "shap-fill down"}
                style={{ width: `${pct / 2}%`, [up ? "left" : "right"]: "50%" }}
              />
            </div>
            <span className={up ? "shap-value up" : "shap-value down"}>
              {up ? "+" : ""}
              {c.contribution}
            </span>
          </div>
        );
      })}
    </div>
  );
}
