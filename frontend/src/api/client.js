// Central API client: JWT storage, automatic refresh, language header, error shaping.
export const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

const ACCESS_KEY = 'anadi.access';
const REFRESH_KEY = 'anadi.refresh';
const LANG_KEY = 'anadi.lang';

function safeGet(key) {
  try { return localStorage.getItem(key); } catch { return null; }
}
function safeSet(key, value) {
  try {
    if (value == null) localStorage.removeItem(key);
    else localStorage.setItem(key, value);
  } catch { /* storage unavailable */ }
}

export const tokens = {
  get access() { return safeGet(ACCESS_KEY); },
  get refresh() { return safeGet(REFRESH_KEY); },
  set(access, refresh) {
    safeSet(ACCESS_KEY, access);
    if (refresh !== undefined) safeSet(REFRESH_KEY, refresh);
  },
  clear() { safeSet(ACCESS_KEY, null); safeSet(REFRESH_KEY, null); },
};

export const getLang = () => safeGet(LANG_KEY) || 'en';
export const setLang = (lang) => safeSet(LANG_KEY, lang);

export class ApiError extends Error {
  constructor(status, data) {
    super(ApiError.describe(status, data));
    this.status = status;
    this.data = data;
  }

  static describe(status, data) {
    if (status === 0) return 'Cannot reach the server. Is the backend running?';
    if (status === 429) return 'Too many requests. Please wait a minute and try again.';
    if (data && typeof data === 'object') {
      if (data.detail) return String(data.detail);
      if (Array.isArray(data)) return data.join(' ');
      const parts = Object.entries(data).map(([field, msgs]) => {
        const text = Array.isArray(msgs) ? msgs.join(' ') : typeof msgs === 'object' ? JSON.stringify(msgs) : String(msgs);
        return field === 'non_field_errors' ? text : `${field.replace(/_/g, ' ')}: ${text}`;
      });
      if (parts.length) return parts.join(' • ');
    }
    if (status === 401) return 'Please log in to continue.';
    if (status === 403) return 'You do not have permission for this action.';
    if (status === 404) return 'Not found.';
    return `Request failed (${status}).`;
  }

  // Field-level errors for forms
  get fields() {
    if (!this.data || typeof this.data !== 'object' || Array.isArray(this.data)) return {};
    const out = {};
    for (const [k, v] of Object.entries(this.data)) {
      if (k !== 'detail' && k !== 'non_field_errors') out[k] = Array.isArray(v) ? v.join(' ') : String(v);
    }
    return out;
  }
}

let refreshing = null;
let onAuthLost = () => {};
export const setAuthLostHandler = (fn) => { onAuthLost = fn; };

async function refreshAccess() {
  const refresh = tokens.refresh;
  if (!refresh) return false;
  if (!refreshing) {
    refreshing = fetch(`${API_BASE}/api/auth/token/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh }),
    })
      .then(async (res) => {
        if (!res.ok) return false;
        const data = await res.json();
        tokens.set(data.access, data.refresh);
        return true;
      })
      .catch(() => false)
      .finally(() => { setTimeout(() => { refreshing = null; }, 0); });
  }
  return refreshing;
}

async function raw(path, { method = 'GET', body, auth = true, headers = {}, binary = false } = {}) {
  const h = { 'Accept-Language': getLang(), ...headers };
  const isForm = typeof FormData !== 'undefined' && body instanceof FormData;
  if (body !== undefined && !isForm) h['Content-Type'] = 'application/json';
  if (auth && tokens.access) h.Authorization = `Bearer ${tokens.access}`;
  let res;
  try {
    res = await fetch(path.startsWith('http') ? path : `${API_BASE}${path}`, {
      method,
      headers: h,
      body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, null);
  }
  return res;
}

export async function request(path, options = {}) {
  let res = await raw(path, options);
  if (res.status === 401 && options.auth !== false && tokens.refresh) {
    if (await refreshAccess()) res = await raw(path, options);
    else { tokens.clear(); onAuthLost(); }
  }
  if (options.binary) {
    if (!res.ok) throw new ApiError(res.status, await res.json().catch(() => null));
    return res;
  }
  if (res.status === 204) return null;
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, data);
  return data;
}

export const api = {
  get: (path, opts) => request(path, { ...opts, method: 'GET' }),
  post: (path, body, opts) => request(path, { ...opts, method: 'POST', body }),
  patch: (path, body, opts) => request(path, { ...opts, method: 'PATCH', body }),
  put: (path, body, opts) => request(path, { ...opts, method: 'PUT', body }),
  del: (path, opts) => request(path, { ...opts, method: 'DELETE' }),
  public: (path) => request(path, { auth: false }),
};

/** Fetch every page of a paginated list (for lookups / dropdowns). */
export async function getAll(path, max = 10) {
  const results = [];
  let url = path;
  for (let i = 0; url && i < max; i += 1) {
    const data = await api.get(url);
    if (Array.isArray(data)) return data;
    results.push(...(data.results || []));
    url = data.next ? data.next.replace(API_BASE, '') : null;
  }
  return results;
}

/** Authenticated binary download (documents). */
export async function downloadFile(path, fallbackName = 'document') {
  const res = await request(path, { binary: true });
  const disposition = res.headers.get('Content-Disposition') || '';
  const match = disposition.match(/filename="?([^";]+)"?/i);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = match ? match[1] : fallbackName;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1500);
}

export async function login(username, password) {
  const data = await request('/api/auth/token/', { method: 'POST', body: { username, password }, auth: false });
  tokens.set(data.access, data.refresh);
  return request('/api/auth/me/');
}
