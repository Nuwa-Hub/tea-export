// LSTM back-test accuracy for each forecast series (lower = better).
// These come from the hold-out window the backend evaluates before
// retraining on the full series.

const LABELS = {
  auction_price_usd: "Auction price (USD/kg)",
  export_volume_kg: "Export volume (kg)",
  usd_lkr: "USD/LKR rate",
};

export default function MetricsTable({ forecasts }) {
  const rows = Object.keys(forecasts);
  return (
    <div className="card">
      <h3>LSTM back-test accuracy</h3>
      <table className="metrics">
        <thead>
          <tr>
            <th>Series</th>
            <th>MAE</th>
            <th>RMSE</th>
            <th>MAPE&nbsp;(%)</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((k) => {
            const m = forecasts[k].metrics;
            return (
              <tr key={k}>
                <td>{LABELS[k] || k}</td>
                <td>{m.MAE}</td>
                <td>{m.RMSE}</td>
                <td>{m.MAPE}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="hint">
        Measured on a held-out tail of the series (recursive multi-step forecast vs. actual).
      </p>
    </div>
  );
}
