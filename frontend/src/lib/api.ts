export type Agent = {
  id: number;
  business_id: number;
  name: string;
  purpose: string;
  personality: string;
  voice: string;
  language: string;
  speaking_speed: number;
  greeting: string;
  system_prompt: string | null;
  capabilities: Record<string, boolean>;
  status: string;
  phone_number: string | null;
  escalation_number: string | null;
  after_hours_behavior: string;
  created_at: string;
  business_name?: string | null;
  call_count: number;
  avg_duration_seconds: number;
  success_rate: number;
};

export type DocumentItem = {
  id: number;
  agent_id: number;
  filename: string;
  source_type: string;
  status: string;
  created_at: string;
};

export type CallItem = {
  id: number;
  agent_id: number;
  caller_number: string | null;
  started_at: string;
  ended_at: string | null;
  duration_seconds: number;
  status: string;
  summary: string | null;
  outcome: string | null;
  intent: string | null;
  sentiment: string | null;
  successful: boolean;
  agent_name?: string | null;
};

export type CallDetail = CallItem & {
  messages: { id: number; role: string; content: string; timestamp: string }[];
};

export type Analytics = {
  total_calls: number;
  successful_calls: number;
  transferred: number;
  failed: number;
  avg_duration_seconds: number;
  appointments: number;
  leads_captured: number;
};

export type User = {
  id: number;
  email: string;
  name: string;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5050";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("vap_token");
}

export function setToken(token: string) {
  localStorage.setItem("vap_token", token);
}

export function clearToken() {
  localStorage.removeItem("vap_token");
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers || {});
  if (!(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    let detail: unknown = "Request failed";
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* ignore */
    }
    let message = "Request failed";
    if (typeof detail === "string") {
      message = detail;
    } else if (Array.isArray(detail)) {
      message = detail
        .map((d) => {
          if (typeof d === "string") return d;
          if (d && typeof d === "object" && "msg" in d) return String((d as { msg: string }).msg);
          return JSON.stringify(d);
        })
        .join(" · ");
    } else {
      message = JSON.stringify(detail);
    }
    throw new Error(message);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}m ${String(s).padStart(2, "0")}s`;
}
