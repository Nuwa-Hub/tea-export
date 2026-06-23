import { useEffect, useState } from "react";
import { createPassport, fetchChain } from "../api";

const GRADES = ["BOPF", "BOP", "OP"];
const CERTS = ["ISO 22000", "Halal", "Organic", "JAS", "Rainforest Alliance"];
const DESTINATIONS = ["Russia", "UAE", "Iran", "Iraq", "Turkey", "China", "Japan", "Germany"];

export default function PassportPage() {
  const [form, setForm] = useState({
    estate: "Pedro Estate",
    grade: "BOPF",
    volume_kg: 5000,
    destination: "UAE",
    moisture_pct: 6.2,
    pesticide_ppm: 0.02,
    certifications: ["ISO 22000", "Halal"],
  });
  const [result, setResult] = useState(null);
  const [reject, setReject] = useState(null);
  const [busy, setBusy] = useState(false);
  const [chain, setChain] = useState(null);

  async function loadChain() {
    try {
      setChain(await fetchChain());
    } catch (e) {
      /* ignore */
    }
  }
  useEffect(() => {
    loadChain();
  }, []);

  function set(k, v) {
    setForm((f) => ({ ...f, [k]: v }));
  }
  function toggleCert(c) {
    setForm((f) => ({
      ...f,
      certifications: f.certifications.includes(c)
        ? f.certifications.filter((x) => x !== c)
        : [...f.certifications, c],
    }));
  }

  async function submit() {
    setBusy(true);
    setReject(null);
    setResult(null);
    try {
      const res = await createPassport({ ...form, volume_kg: Number(form.volume_kg) });
      setResult(res);
      await loadChain();
    } catch (e) {
      // 400 = smart-contract rejection (carries reason + compliance checklist)
      if (e.code === 400 && e.detail) setReject(e.detail);
      else setReject({ reason: e.message, compliance: null });
    } finally {
      setBusy(false);
    }
  }

  const integrity = chain?.integrity;

  return (
    <div className="page">
      <div className="grid">
        <div className="card">
          <h3>Issue export passport</h3>
          <p className="muted">
            The shipment is checked against the destination's buyer requirements, gated by an
            on-chain "smart contract", then written to the immutable ledger with a QR code.
          </p>
          <div className="form">
            <label>Estate
              <input value={form.estate} onChange={(e) => set("estate", e.target.value)} />
            </label>
            <label>Destination
              <select value={form.destination} onChange={(e) => set("destination", e.target.value)}>
                {DESTINATIONS.map((d) => <option key={d}>{d}</option>)}
              </select>
            </label>
            <label>Grade
              <select value={form.grade} onChange={(e) => set("grade", e.target.value)}>
                {GRADES.map((g) => <option key={g}>{g}</option>)}
              </select>
            </label>
            <label>Volume (kg)
              <input type="number" value={form.volume_kg} onChange={(e) => set("volume_kg", e.target.value)} />
            </label>
            <label>Moisture (%)
              <input type="number" step="0.1" value={form.moisture_pct}
                onChange={(e) => set("moisture_pct", Number(e.target.value))} />
            </label>
            <label>Pesticide (ppm)
              <input type="number" step="0.01" value={form.pesticide_ppm}
                onChange={(e) => set("pesticide_ppm", Number(e.target.value))} />
            </label>
          </div>
          <div className="certs">
            <span className="muted">Certifications:</span>
            {CERTS.map((c) => (
              <label key={c} className="cert-chk">
                <input type="checkbox" checked={form.certifications.includes(c)} onChange={() => toggleCert(c)} />
                {c}
              </label>
            ))}
          </div>
          <button className="primary" onClick={submit} disabled={busy}>
            {busy ? "Recording on-chain…" : "Issue passport"}
          </button>
          {reject && (
            <div className="reject">
              <strong>⛔ Smart contract rejected this shipment.</strong>
              <p>{reject.reason}</p>
              {reject.compliance && (
                <ul>
                  {reject.compliance.checks.filter((c) => !c.ok).map((c) => (
                    <li key={c.requirement}>{c.requirement}: needs {c.required}, lot has {c.actual}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>

        <div className="card passport-result">
          <h3>Digital passport</h3>
          {!result && <p className="muted">Issue a passport to see its on-chain record and QR code.</p>}
          {result && (
            <div className="passport-card">
              <div className="qr" dangerouslySetInnerHTML={{ __html: result.qr_svg }} />
              <div className="passport-meta">
                <div className="passport-id">{result.passport.passport_id}</div>
                <div>{result.passport.estate} → <strong>{result.passport.destination}</strong></div>
                <div>{result.passport.grade} · {result.passport.volume_kg.toLocaleString()} kg</div>
                <div className="badge ok">✓ Compliance passed</div>
                <div className="hash">block #{result.block.index} · {result.block.hash.slice(0, 24)}…</div>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="card">
        <div className="compliance-head">
          <h3>Ledger (immutable chain)</h3>
          {integrity && (
            <span className={integrity.valid ? "badge ok" : "badge warn"}>
              {integrity.valid ? `✓ Verified · ${integrity.length} blocks` : `✗ Tampered at #${integrity.broken_at}`}
            </span>
          )}
        </div>
        <div className="table-scroll">
          <table className="metrics">
            <thead>
              <tr><th>#</th><th>Type</th><th>Passport</th><th>Destination</th><th>Volume</th><th>Hash</th></tr>
            </thead>
            <tbody>
              {(chain?.chain || []).map((b) => (
                <tr key={b.index}>
                  <td>{b.index}</td>
                  <td>{b.data.type}</td>
                  <td>{b.data.passport_id || "—"}</td>
                  <td>{b.data.destination || "—"}</td>
                  <td>{b.data.volume_kg ? b.data.volume_kg.toLocaleString() : "—"}</td>
                  <td className="mono">{b.hash.slice(0, 18)}…</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="hint">
          Each block's hash chains to the previous one; altering any record breaks the chain
          (a simulated Hyperledger-Fabric-style ledger).
        </p>
      </div>
    </div>
  );
}
