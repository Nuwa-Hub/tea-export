// Base URL of the FastAPI backend. Override with VITE_API_URL if needed.
const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function getJSON(path, opts) {
  const res = await fetch(`${API}${path}`, opts);
  if (res.status === 409) {
    // Models not trained yet (or training in progress) — surface a typed error.
    const body = await res.json().catch(() => ({}));
    const err = new Error(body.detail || "Not ready");
    err.code = 409;
    throw err;
  }
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

export const fetchDashboard = (horizon) => getJSON(`/api/dashboard?horizon=${horizon}`);
export const getModelStatus = () => getJSON(`/api/model-status`);
export const trainModels = () => getJSON(`/api/train`, { method: "POST" });
