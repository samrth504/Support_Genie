/**
 * One Axios instance for the whole app.
 *  - attaches the JWT to every request
 *  - on 401 (expired / invalid token) logs the user out
 *  - errorMessage() turns any API error into a human-readable sentence
 */
import axios from "axios";

export const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");
export const TOKEN_KEY = "sg_token";
export const USER_KEY = "sg_user";

// localStorage can throw (private mode, blocked storage) -> never let it crash the app
export const storage = {
  get(key) {
    try { return localStorage.getItem(key); } catch { return null; }
  },
  set(key, value) {
    try { localStorage.setItem(key, value); } catch { /* ignore */ }
  },
  remove(key) {
    try { localStorage.removeItem(key); } catch { /* ignore */ }
  },
};

export const api = axios.create({ baseURL: API_URL, timeout: 90000 });

api.interceptors.request.use((config) => {
  const token = storage.get(TOKEN_KEY);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let unauthorizedHandler = () => {};
export function setUnauthorizedHandler(fn) {
  unauthorizedHandler = fn;
}

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const isLogin = error.config?.url?.includes("/api/auth/login");
    if (error.response?.status === 401 && !isLogin) unauthorizedHandler();
    return Promise.reject(error);
  },
);

export function errorMessage(error, fallback = "Something went wrong. Please try again.") {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => `${d.loc?.slice(-1)[0] ?? ""}: ${(d.msg || "").replace(/^Value error, /, "")}`.replace(/^: /, ""))
      .join(" · ");
  }
  if (error?.code === "ECONNABORTED") return "The server took too long to respond. Please try again.";
  if (!error?.response) return "Cannot reach the server. Is the backend running?";
  return fallback;
}
