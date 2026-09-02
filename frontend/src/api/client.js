const TOKEN_KEY = "biospecimen.token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  constructor(code, message, details, status) {
    super(message);
    this.code = code;
    this.details = details;
    this.status = status;
  }
}

async function parseError(res) {
  let body = {};
  try {
    body = await res.json();
  } catch {
    body = { code: "HTTP_ERROR", message: res.statusText };
  }
  throw new ApiError(body.code || "HTTP_ERROR", body.message || "Request failed", body.details || {}, res.status);
}

export async function api(path, { method = "GET", body, headers, isForm } = {}) {
  const token = getToken();
  const h = { ...(headers || {}) };
  if (token) h.Authorization = `Bearer ${token}`;
  if (body && !isForm && !(body instanceof FormData)) h["Content-Type"] = "application/json";
  const res = await fetch(path, {
    method,
    headers: h,
    body: body && !isForm && !(body instanceof FormData) ? JSON.stringify(body) : body,
  });
  if (!res.ok) await parseError(res);
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  if (ct.includes("text/")) return res.text();
  return res.blob();
}

export async function downloadAuth(path, filename) {
  const token = getToken();
  const res = await fetch(path, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
  if (!res.ok) throw new ApiError("DOWNLOAD_FAILED", "Unable to download file", {}, res.status);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.target = "_blank";
  a.click();
  URL.revokeObjectURL(url);
}

export const AuthAPI = {
  login: (email, password) => api("/api/v1/auth/login", { method: "POST", body: { email, password } }),
  me: () => api("/api/v1/auth/me"),
};

export const ManifestAPI = {
  list: () => api("/api/v1/manifests"),
  get: (id) => api(`/api/v1/manifests/${id}`),
  upload: (file) => {
    const fd = new FormData();
    fd.append("file", file);
    return api("/api/v1/manifests", { method: "POST", body: fd, isForm: true });
  },
  validate: (id) => api(`/api/v1/manifests/${id}/validate`, { method: "POST" }),
  commit: (id) => api(`/api/v1/manifests/${id}/commit`, { method: "POST" }),
  validationReportUrl: (id) => `/api/v1/manifests/${id}/validation-report`,
};

export const SampleAPI = {
  list: (params = {}) => {
    const q = new URLSearchParams(Object.fromEntries(Object.entries(params).filter(([, v]) => v)));
    return api(`/api/v1/samples?${q}`);
  },
  get: (id) => api(`/api/v1/samples/${id}`),
  get360: (id) => api(`/api/v1/samples/${id}/360`),
  lookup: (q) => api(`/api/v1/samples/lookup?q=${encodeURIComponent(q)}`),
  accession: (id) => api(`/api/v1/samples/${id}/accession`, { method: "POST" }),
  createLabel: (id) => api(`/api/v1/samples/${id}/labels`, { method: "POST" }),
  assignStorage: (id, storage_location_id, reason) =>
    api(`/api/v1/samples/${id}/storage`, { method: "POST", body: { storage_location_id, reason } }),
  move: (id, destination_location_id, reason) =>
    api(`/api/v1/samples/${id}/move`, { method: "POST", body: { destination_location_id, reason } }),
  assignCustodian: (id, custodian_id, reason) =>
    api(`/api/v1/samples/${id}/custodian`, { method: "POST", body: { custodian_id, reason } }),
  custodianHistory: (id) => api(`/api/v1/samples/${id}/custodian`),
  checkout: (id, purpose) => api(`/api/v1/samples/${id}/checkout`, { method: "POST", body: { purpose } }),
  returnTo: (id, storage_location_id) =>
    api(`/api/v1/samples/${id}/return`, { method: "POST", body: { storage_location_id } }),
  children: (id, payload) => api(`/api/v1/samples/${id}/children`, { method: "POST", body: payload }),
  lineage: (id) => api(`/api/v1/samples/${id}/lineage`),
  environmental: (id, payload) =>
    api(`/api/v1/samples/${id}/environmental-events/json`, { method: "POST", body: payload }),
};

export const LabelAPI = {
  reprint: (id, reason) => api(`/api/v1/labels/${id}/reprint`, { method: "POST", body: { reason } }),
  png: (id) => `/api/v1/labels/${id}/png`,
  pdf: (id) => `/api/v1/labels/${id}/pdf`,
};

export const InventoryAPI = {
  tree: (parent_id) => api(`/api/v1/inventory/tree${parent_id ? `?parent_id=${parent_id}` : ""}`),
  occupancy: (id) => api(`/api/v1/inventory/locations/${id}/occupancy`),
};

export const PlatformAPI = {
  dashboard: () => api("/api/v1/dashboard"),
  search: (q) => api(`/api/v1/search?q=${encodeURIComponent(q)}`),
  audit: (params = {}) => {
    const q = new URLSearchParams(Object.fromEntries(Object.entries(params).filter(([, v]) => v)));
    return api(`/api/v1/audit?${q}`);
  },
  shipments: () => api("/api/v1/shipments"),
  shipment: (id) => api(`/api/v1/shipments/${id}`),
  custodians: () => api("/api/v1/custodians"),
  exceptions: (status) => api(`/api/v1/exceptions${status ? `?status=${status}` : ""}`),
  exception: (id) => api(`/api/v1/exceptions/${id}`),
  resolve: (id, payload) => api(`/api/v1/exceptions/${id}/resolve`, { method: "POST", body: payload }),
  sampleHistory: (id) => api(`/api/v1/reports/sample-history/${id}`),
  inventoryReport: () => api("/api/v1/reports/inventory"),
  sampleHistoryCsv: (id) => `/api/v1/reports/sample-history/${id}/csv`,
  traceability: () => api("/api/v1/traceability"),
  users: () => api("/api/v1/admin/users"),
  createUser: (payload) => api("/api/v1/admin/users", { method: "POST", body: payload }),
  deleteUser: (id) => api(`/api/v1/admin/users/${id}`, { method: "DELETE" }),
};
