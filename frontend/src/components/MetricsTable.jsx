// Back-test accuracy comparison: LSTM (production) vs ARIMA (statistical baseline)
// for each forecast series. Lower MAE/RMSE/MAPE is better; the winner's MAPE is
// highlighted. Measured on a held-out tail of each series.

const LABELS = {
  auction_price_usd: "Auction price (USD/kg)",
  export_volume_kg: "Export volume (kg)",
  usd_lkr: "USD/LKR rate",
  storage_risk: "Storage risk index",
};

function Cell({ m }) {
  if (!m || m.MAE === undefined) return <td colSpan={3} className="muted">—</td>;
  return (
    <>
      <td>{m.MAE}</td>
      <td>{m.RMSE}</td>
      <td>{m.MAPE}</td>
    </>
  );
}

export default function MetricsTable({ forecasts }) {
  const rows = Object.keys(forecasts);
  return (
    <div className="card">
      <h3>Back-test accuracy — LSTM vs ARIMA</h3>
      <div className="table-scroll">
        <table className="metrics">
          <thead>
            <tr>
              <th rowSpan={2}>Series</th>
              <th colSpan={3} className="grp">LSTM (deep)</th>
              <th colSpan={3} className="grp">ARIMA (baseline)</th>
            </tr>
            <tr>
              <th>MAE</th><th>RMSE</th><th>MAPE%</th>
              <th>MAE</th><th>RMSE</th><th>MAPE%</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((k) => {
              const lstm = forecasts[k].metrics;
              const arima = forecasts[k].arima?.metrics;
              const lstmWins = lstm?.MAPE !== undefined && arima?.MAPE !== undefined && lstm.MAPE <= arima.MAPE;
              return (
                <tr key={k}>
                  <td>{LABELS[k] || k}</td>
                  <td>{lstm?.MAE ?? "—"}</td>
                  <td>{lstm?.RMSE ?? "—"}</td>
                  <td className={lstmWins ? "win" : ""}>{lstm?.MAPE ?? "—"}</td>
                  <Cell m={arima} />
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="hint">
        Held-out tail, recursive multi-step forecast vs. actual. Highlighted = better MAPE.
      </p>
    </div>
  );
}
