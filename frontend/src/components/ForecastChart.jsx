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

// Merge the historical series with the forecast into one continuous dataset.
// The last historical point is duplicated into the forecast line so the two
// segments visually connect.
function buildSeries(history, field, futureDates, forecast) {
  const rows = history.map((r) => ({ date: r.date, actual: r[field] }));
  if (rows.length) {
    rows[rows.length - 1] = { ...rows[rows.length - 1], forecast: rows[rows.length - 1].actual };
  }
  futureDates.forEach((d, i) => rows.push({ date: d, forecast: forecast[i] }));
  return rows;
}

export default function ForecastChart({ title, history, field, futureDates, forecast, color }) {
  const data = buildSeries(history, field, futureDates, forecast);
  return (
    <div className="card">
      <h3>{title}</h3>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
          <XAxis dataKey="date" tick={{ fontSize: 11 }} minTickGap={32} />
          <YAxis tick={{ fontSize: 11 }} domain={["auto", "auto"]} width={64} />
          <Tooltip />
          <Legend />
          <Line
            type="monotone"
            dataKey="actual"
            name="Historical"
            stroke={color}
            dot={false}
            strokeWidth={2}
            connectNulls
          />
          <Line
            type="monotone"
            dataKey="forecast"
            name="LSTM forecast"
            stroke="#e2711d"
            strokeDasharray="5 4"
            dot={{ r: 2 }}
            strokeWidth={2}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
