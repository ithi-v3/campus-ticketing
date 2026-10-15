const BASE = import.meta.env.VITE_API_URL || "";

let token = null;
try {
  token = localStorage.getItem("token");
} catch {
  /* storage blocked: user just has to log in each visit */
}

let onUnauthorized = () => {};

export function setToken(value) {
  token = value;
  try {
    if (value) localStorage.setItem("token", value);
    else localStorage.removeItem("token");
  } catch {
    /* ignore */
  }
}

export const hasToken = () => Boolean(token);
export function setUnauthorizedHandler(fn) {
  onUnauthorized = fn;
}

export async function api(path, { method = "GET", body, params } = {}) {
  let url = `${BASE}/api${path}`;
  if (params) {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== "" && v !== undefined && v !== null) qs.set(k, v);
    });
    const s = qs.toString();
    if (s) url += `?${s}`;
  }

  let res;
  try {
    res = await fetch(url, {
      method,
      headers: {
        ...(body ? { "Content-Type": "application/json" } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new Error("Can't reach the server. Check your connection and try again.");
  }

  let data = null;
  try {
    data = await res.json();
  } catch {
    /* empty or non-JSON body */
  }

  if (!res.ok) {
    if (res.status === 401 && token && !path.startsWith("/auth/login")) onUnauthorized();
    throw new Error((data && data.error) || `Request failed (${res.status})`);
  }
  return data;
}
