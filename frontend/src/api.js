// Base URL of the FastAPI backend. Override with VITE_API_URL if needed.
const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request(path, opts) {
  const res = await fetch(`${API}${path}`, opts);
  if (res.status === 409) {
    // Models not trained yet (or training in progress) — surface a typed error.
    const body = await res.json().catch(() => ({}));
    const err = new Error(body.detail || "Not ready");
    err.code = 409;
    throw err;
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const err = new Error(typeof body.detail === "string" ? body.detail : `API error ${res.status}`);
    err.code = res.status;
    err.detail = body.detail;
    throw err;
  }
  return res.json();
}

const getJSON = (path) => request(path);

// Infra / training
export const getModelStatus = () => getJSON(`/api/model-status`);
export const trainModels = () => request(`/api/train`, { method: "POST" });

// Data
export const fetchHistory = () => getJSON(`/api/history`);
export const fetchCountries = () => getJSON(`/api/countries`);

// Modules 1-3: forecasting + overview bundle
export const fetchDashboard = (h) => getJSON(`/api/dashboard?horizon=${h}`);
export const fetchForecast = (h) => getJSON(`/api/forecast?horizon=${h}`);
export const fetchCountryDemand = (h) => getJSON(`/api/demand/countries?horizon=${h}`);

// Module 4 / 5
export const fetchOpportunity = (h) => getJSON(`/api/opportunity?horizon=${h}`);
export const fetchRecommendation = (h) => getJSON(`/api/recommendation?horizon=${h}`);

// Module 6
export const fetchReadiness = (h) => getJSON(`/api/readiness?horizon=${h}`);
export const fetchCompliance = (country) => getJSON(`/api/compliance?country=${encodeURIComponent(country)}`);

// Module 7: blockchain passport
export const createPassport = (shipment) =>
  request(`/api/passport`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(shipment),
  });
export const fetchChain = () => getJSON(`/api/passport/chain`);
