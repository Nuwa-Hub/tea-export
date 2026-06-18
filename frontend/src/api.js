// Base URL of the FastAPI backend. Override with VITE_API_URL if needed.
const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function fetchDashboard(horizon) {
  const res = await fetch(`${API}/api/dashboard?horizon=${horizon}`);
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}
