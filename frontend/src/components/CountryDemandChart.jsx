import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

// Country-wise export-demand forecast (ARIMA per destination). Shows the average
// recent monthly volume vs the average forecast volume so growth/decline is
// visible at a glance; bars are coloured by direction.
function avg(arr) {
  if (!arr || !arr.length) return 0;
  return arr.reduce((a, b) => a + b, 0) / arr.length;
}

export default function CountryDemandChart({ countries }) {
  const data = (countries || []).map((c) => {
    const recent = avg(c.history.slice(-12));
    const forecast = avg(c.forecast);
    return {
      country: c.country,
      recent: Math.round(recent),
      forecast: Math.round(forecast),
      up: forecast >= recent,
      mape: c.metrics?.MAPE,
    };
  });

  return (
    <div className="card">
      <h3>Country demand — recent vs forecast (avg monthly kg)</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
          <XAxis dataKey="country" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} width={64} />
          <Tooltip />
          <Legend />
          <Bar dataKey="recent" name="Recent 12m avg" fill="#b9c6bb" />
          <Bar dataKey="forecast" name="Forecast avg">
            {data.map((d, i) => (
              <Cell key={i} fill={d.up ? "#2e7d32" : "#c0392b"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <p className="hint">Green forecast bar = growing demand, red = softening. ARIMA per country.</p>
    </div>
  );
}
