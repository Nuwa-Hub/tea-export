import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

// Merge history with the LSTM (and optional ARIMA) forecast into one continuous
// dataset. The last historical point is duplicated into the forecast lines so the
// segments visually connect.
function buildSeries(history, field, futureDates, lstm, arima) {
  const rows = history.map((r) => ({ date: r.date, actual: r[field] }));
  if (rows.length) {
    const last = rows[rows.length - 1];
    rows[rows.length - 1] = { ...last, lstm: last.actual, arima: last.actual };
  }
  futureDates.forEach((d, i) => {
    rows.push({ date: d, lstm: lstm?.[i], arima: arima?.[i] });
  });
  return rows;
}

export default function ForecastChart({ title, history, field, futureDates, lstm, arima, color, showArima }) {
  const data = buildSeries(history, field, futureDates, lstm, showArima ? arima : null);
  return (
    <div className="card">
      <h3>{title}</h3>
      <ResponsiveContainer width="100%" height={250}>
        <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
          <XAxis dataKey="date" tick={{ fontSize: 11 }} minTickGap={32} />
          <YAxis tick={{ fontSize: 11 }} domain={["auto", "auto"]} width={64} />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey="actual" name="Historical" stroke={color}
            dot={false} strokeWidth={2} connectNulls />
          <Line type="monotone" dataKey="lstm" name="LSTM forecast" stroke="#e2711d"
            strokeDasharray="5 4" dot={{ r: 2 }} strokeWidth={2} connectNulls />
          {showArima && (
            <Line type="monotone" dataKey="arima" name="ARIMA baseline" stroke="#8a98a8"
              strokeDasharray="2 3" dot={false} strokeWidth={1.5} connectNulls />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
