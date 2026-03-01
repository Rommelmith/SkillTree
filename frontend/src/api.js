const BASE = "/api";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export const fetchAnalytics = () => request("/analytics/");

export const fetchJobs = (params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(Object.entries(params).filter(([, v]) => v !== undefined && v !== ""))
  ).toString();
  return request(`/jobs/${qs ? "?" + qs : ""}`);
};

export const fetchStatus = () => request("/status/");

export const triggerFetch = () =>
  request("/fetch/", { method: "POST" });

export const fetchHotJobs = () => request("/hotjobs/");
