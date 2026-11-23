/** Every backend call in one place. Pages never build URLs themselves. */
import { api } from "./client";

const data = (r) => r.data;

export const healthApi = {
  check: () => api.get("/health", { timeout: 70000 }).then(data),
};

export const authApi = {
  // FastAPI's OAuth2 login expects a FORM with "username" (= email) and "password"
  login: (email, password) =>
    api
      .post("/api/auth/login", new URLSearchParams({ username: email, password }), {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      })
      .then(data),
  signup: (payload) => api.post("/api/auth/signup", payload).then(data),
  me: () => api.get("/api/auth/me").then(data),
  changePassword: (current, next) =>
    api.post("/api/auth/change-password", { current_password: current, new_password: next }),
};

export const ticketsApi = {
  create: (payload) => api.post("/api/tickets", payload).then(data),
  list: () => api.get("/api/tickets").then(data),
  get: (id) => api.get(`/api/tickets/${id}`).then(data),
  feedback: (id, rating) => api.post(`/api/tickets/${id}/feedback`, { rating }).then(data),
};

export const reviewApi = {
  queue: () => api.get("/api/review/queue").then(data),
  all: (status) => api.get("/api/review/tickets", { params: status ? { status } : {} }).then(data),
  get: (id) => api.get(`/api/review/tickets/${id}`).then(data),
  act: (id, action, reply) => api.post(`/api/review/tickets/${id}`, { action, reply: reply ?? null }).then(data),
};

export const kbApi = {
  list: () => api.get("/api/kb/documents").then(data),
  upload: (file) => {
    const form = new FormData();
    form.append("file", file);
    return api.post("/api/kb/upload", form).then(data);
  },
  remove: (id) => api.delete(`/api/kb/documents/${id}`),
  search: (q, k = 5) => api.get("/api/kb/search", { params: { q, k } }).then(data),
};

export const analyticsApi = {
  summary: (days = 14) => api.get("/api/analytics/summary", { params: { days } }).then(data),
  trends: (days = 30) => api.get("/api/analytics/trends", { params: { days } }).then(data),
  gaps: (limit = 50) => api.get("/api/analytics/gaps", { params: { limit } }).then(data),
};
