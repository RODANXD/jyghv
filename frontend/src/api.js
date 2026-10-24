async function get(path, params = {}) {
  const qs = new URLSearchParams(params).toString();
  const res = await fetch(`/api${path}${qs ? `?${qs}` : ""}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

export const api = {
  meta: () => get("/meta"),
  forecast: (p) => get("/forecast", p),
  metrics: (p) => get("/metrics", p),
  horizon: () => get("/metrics/by-horizon"),
};
