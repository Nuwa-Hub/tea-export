import {
  CartesianGrid,
  Cell,
  Label,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";

// Offline "opportunity map": a suitability landscape rather than a geographic map
// (no external tile servers). X = suitability score, Y = forecast demand-growth
// subscore, bubble size = recent monthly volume, colour = status band.
const STATUS_COLOR = { High: "#2e7d32", Medium: "#ed9b00", Low: "#c0392b" };

function Dot(props) {
  const { cx, cy, payload } = props;
  return (
    <g>
      <circle cx={cx} cy={cy} r={Math.max(8, props.r || 8)} fill={STATUS_COLOR[payload.status]}
        fillOpacity={0.65} stroke="#fff" strokeWidth={1.5} />
      <text x={cx} y={cy - 12} textAnchor="middle" fontSize={11} fill="#33413a">
        {payload.country}
      </text>
    </g>
  );
}

export default function OpportunityMap({ opportunity }) {
  const data = (opportunity || []).map((o) => ({
    country: o.country,
    suitability: o.suitability,
    demand: o.subscores.demand_growth,
    volume: o.recent_volume_kg,
    status: o.status,
  }));

  return (
    <div className="card">
      <h3>Export Opportunity Map — suitability landscape</h3>
      <ResponsiveContainer width="100%" height={360}>
        <ScatterChart margin={{ top: 20, right: 24, left: 8, bottom: 24 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
          <XAxis type="number" dataKey="suitability" name="Suitability" domain={[40, 80]}
            tick={{ fontSize: 11 }}>
            <Label value="Suitability score →" position="bottom" offset={4} fontSize={12} />
          </XAxis>
          <YAxis type="number" dataKey="demand" name="Demand growth" domain={[0, 100]}
            tick={{ fontSize: 11 }}>
            <Label value="Demand growth →" angle={-90} position="left" offset={-4} fontSize={12} />
          </YAxis>
          <ZAxis type="number" dataKey="volume" range={[120, 800]} name="Volume" />
          <Tooltip cursor={{ strokeDasharray: "3 3" }}
            formatter={(v, n) => (n === "Volume" ? `${v.toLocaleString()} kg` : v)} />
          <Scatter data={data} shape={<Dot />}>
            {data.map((d, i) => (
              <Cell key={i} fill={STATUS_COLOR[d.status]} />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
      <p className="hint">
        Bubble size = recent monthly volume. Top-right = the best opportunities (high suitability
        and growing demand). Colour: <span style={{ color: "#2e7d32" }}>High</span> /{" "}
        <span style={{ color: "#ed9b00" }}>Medium</span> / <span style={{ color: "#c0392b" }}>Low</span>.
      </p>
    </div>
  );
}
