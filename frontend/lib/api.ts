import type { Patient, PatientCreate, Report, ReportCreate } from "./types";

// On Vercel, API runs as serverless function at /api/*; locally, separate server.
const API_BASE = process.env.NEXT_PUBLIC_API_URL || (typeof window !== "undefined" ? "/api" : "http://127.0.0.1:8000");
const TOKEN_KEY = "lab_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  auth = true
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (auth) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (body.detail && body.detail[0]?.msg) detail = body.detail[0].msg;
    } catch {
      /* ignore */
    }
    if (res.status === 401) {
      clearToken();
    }
    throw new Error(detail || `Request failed (${res.status})`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  login: (username: string, password: string) =>
    request<{ token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }, false),
  me: () => request<{ username: string }>("/auth/me"),

  listPatients: () => request<Patient[]>("/patients"),
  createPatient: (p: PatientCreate) =>
    request<Patient>("/patients", { method: "POST", body: JSON.stringify(p) }),

  listReports: (q?: string) =>
    request<Report[]>(`/reports${q ? `?q=${encodeURIComponent(q)}` : ""}`),
  reviewQueue: () => request<Report[]>("/reports/queue/review"),
  getReport: (id: number | string) => request<Report>(`/reports/${id}`),
  createReport: (r: ReportCreate) =>
    request<Report>("/reports", { method: "POST", body: JSON.stringify(r) }),
  updateReport: (id: number | string, r: Partial<ReportCreate>) =>
    request<Report>(`/reports/${id}`, { method: "PUT", body: JSON.stringify(r) }),
  verifyReport: (
    id: number | string,
    status: "reviewed" | "revised",
    notes?: string
  ) =>
    request<Report>(`/reports/${id}/verify`, {
      method: "POST",
      body: JSON.stringify({ status, verification_notes: notes || "" }),
    }),
  deleteReport: (id: number | string) =>
    request<void>(`/reports/${id}`, { method: "DELETE" }),
};

export const pdfUrl = (id: number | string) =>
  `${API_BASE}/reports/${id}/pdf`;

export function downloadPdf(id: number | string) {
  const token = getToken();
  fetch(pdfUrl(id), {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
    .then((res) => {
      if (!res.ok) throw new Error("PDF download failed");
      return res.blob();
    })
    .then((blob) => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `report_${id}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    });
}
