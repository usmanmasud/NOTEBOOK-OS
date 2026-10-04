import type {
  AppConfig,
  BusinessRecord,
  Dashboard,
  EditableFields,
  Evidence,
  MetricKey,
  PublicReport,
  Report,
  Sample,
  Upload,
  User,
} from "../types";

const TOKEN_KEY = "notebookos.session";

export const session = {
  get(): string | null {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set(token: string | null) {
    try {
      if (token) localStorage.setItem(TOKEN_KEY, token);
      else localStorage.removeItem(TOKEN_KEY);
    } catch {
      /* storage unavailable: session lasts for this page only */
    }
  },
};

export class ApiError extends Error {
  status: number;
  details: unknown;
  constructor(status: number, message: string, details?: unknown) {
    super(message);
    this.status = status;
    this.details = details;
  }
}

type Listener = () => void;
const unauthorizedListeners = new Set<Listener>();
export function onUnauthorized(fn: Listener) {
  unauthorizedListeners.add(fn);
  return () => {
    unauthorizedListeners.delete(fn);
  };
}

async function request<T>(path: string, init: RequestInit = {}, auth = true): Promise<T> {
  const headers = new Headers(init.headers);
  const token = session.get();
  if (auth && token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");

  let response: Response;
  try {
    response = await fetch(`/api${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, "Can't reach NotebookOS. Check your connection and try again.");
  }
  if (response.status === 401 && auth) {
    session.set(null);
    unauthorizedListeners.forEach((fn) => fn());
  }
  if (!response.ok) {
    let message = "Something went wrong. Please try again.";
    let details: unknown;
    try {
      const body = await response.json();
      details = body.detail;
      if (typeof body.detail === "string") message = body.detail;
      else if (body.detail?.message) message = body.detail.message;
      if (Array.isArray(body.fields) && body.fields.length) {
        message = body.fields.map((f: { field: string; message: string }) => `${f.field}: ${f.message}`).join("; ");
      }
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(response.status, message, details);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

const json = (body: unknown): RequestInit => ({ method: "POST", body: JSON.stringify(body) });

function qs(params: Record<string, string | null | undefined>) {
  const entries = Object.entries(params).filter(([, v]) => v) as [string, string][];
  return entries.length ? `?${new URLSearchParams(entries)}` : "";
}

export const api = {
  config: () => request<AppConfig>("/config", {}, false),

  requestOtp: (phone: string) =>
    request<{ sent: boolean; expires_in: number; dev_code?: string }>("/auth/request-otp", json({ phone }), false),
  verifyOtp: (phone: string, code: string) =>
    request<{ token: string; user: User }>("/auth/verify-otp", json({ phone, code }), false),
  demoLogin: () => request<{ token: string; user: User }>("/auth/demo", { method: "POST" }, false),
  me: () => request<User>("/auth/me"),
  updateMe: (body: { name?: string; business_name?: string }) =>
    request<User>("/auth/me", { method: "PATCH", body: JSON.stringify(body) }),
  logout: () => request<{ ok: boolean }>("/auth/logout", { method: "POST" }),

  uploadFile: (kind: "photo" | "voice", file: Blob, filename: string) => {
    const form = new FormData();
    form.append("file", file, filename);
    return request<Upload>(`/uploads/${kind}`, { method: "POST", body: form });
  },
  uploadText: (text: string) => request<Upload>("/uploads/text", json({ text })),
  uploads: () => request<Upload[]>("/uploads"),
  upload: (id: string) => request<Upload>(`/uploads/${id}`),
  uploadRecords: (id: string) => request<BusinessRecord[]>(`/uploads/${id}/records`),
  addRecord: (id: string, fields: EditableFields) =>
    request<BusinessRecord>(`/uploads/${id}/records`, json(fields)),
  confirmUpload: (id: string) => request<{ confirmed: number; upload: Upload }>(`/uploads/${id}/confirm`, json({})),
  retryUpload: (id: string) => request<Upload>(`/uploads/${id}/retry`, { method: "POST" }),
  deleteUpload: (id: string) =>
    request<{ deleted: boolean; records_removed: number }>(`/uploads/${id}`, { method: "DELETE" }),
  async uploadFileBlob(id: string): Promise<Blob> {
    const token = session.get();
    const r = await fetch(`/api/uploads/${id}/file`, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
    if (!r.ok) throw new ApiError(r.status, "The original file is not available.");
    return r.blob();
  },

  record: (id: string) => request<BusinessRecord>(`/records/${id}`),
  updateRecord: (id: string, fields: EditableFields) =>
    request<BusinessRecord>(`/records/${id}`, { method: "PATCH", body: JSON.stringify(fields) }),
  confirmRecord: (id: string) => request<BusinessRecord>(`/records/${id}/confirm`, { method: "POST" }),
  rejectRecord: (id: string) => request<BusinessRecord>(`/records/${id}/reject`, { method: "POST" }),

  dashboard: (start?: string, end?: string) => request<Dashboard>(`/dashboard${qs({ start, end })}`),
  evidence: (metric: MetricKey, person?: string | null) =>
    request<Evidence>(`/dashboard/evidence/${metric}${qs({ person })}`),

  createReport: (body: { consent: boolean; period_start?: string; period_end?: string; title?: string }) =>
    request<Report>("/reports", json(body)),
  reports: () => request<Report[]>("/reports"),
  revokeReport: (id: string) => request<Report>(`/reports/${id}/revoke`, { method: "POST" }),
  publicReport: (token: string) => request<PublicReport>(`/reports/${encodeURIComponent(token)}`, {}, false),

  samples: () => request<Sample[]>("/demo/samples", {}, false),
  async sampleFile(id: string): Promise<Blob> {
    const r = await fetch(`/api/demo/samples/${id}/file`);
    if (!r.ok) throw new ApiError(r.status, "Sample not available.");
    return r.blob();
  },
  resetDemo: (with_history: boolean) =>
    request<{ reset: boolean; history_records_confirmed: number }>("/demo/reset", json({ with_history })),
};
