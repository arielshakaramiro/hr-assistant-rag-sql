// API client. Same-origin (the backend serves this build), so cookies flow automatically.

export type Route = "POLICY" | "DATA" | "BOTH" | "CLARIFY";
export type Confidence = "high" | "low";

export interface Citation {
  doc_title: string;
  section: string;
  text: string;
}

export interface Sources {
  citations?: Citation[];
  sql?: string;
  rows?: Record<string, unknown>[];
  blocked?: { code: string; message: string };
}

export interface ChatData {
  route: Route;
  route_reason: string;
  answer: string;
  confidence: Confidence;
  outcome: string;
  sources: Sources;
}

export interface Me {
  id: number;
  full_name: string;
  department: string;
  role: string;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new ApiError(r.status, await safeJson(r));
  return (await r.json()) as T;
}

async function get<T>(path: string): Promise<T> {
  const r = await fetch(path);
  if (!r.ok) throw new ApiError(r.status, await safeJson(r));
  return (await r.json()) as T;
}

async function safeJson(r: Response): Promise<unknown> {
  try {
    return await r.json();
  } catch {
    return null;
  }
}

export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, body: unknown) {
    super(`API error ${status}`);
    this.status = status;
    this.body = body;
  }
}

export interface MetricsData {
  count: number;
  p95_latency_ms: number;
  mean_cost_usd: number;
  failure_rate: number;
  by_route: Record<string, number>;
}

export const api = {
  login: (email: string, password: string) =>
    post<{ success: boolean; data: { id: number; full_name: string } }>(
      "/api/v1/auth/login",
      { email, password },
    ),
  logout: () => post<{ success: boolean }>("/api/v1/auth/logout", {}),
  me: () => get<{ success: boolean; data: Me }>("/api/v1/auth/me"),
  ask: (question: string) =>
    post<{ success: boolean; data: ChatData }>("/api/v1/chat/ask", { question }),
  feedback: (question: string, answer: string, route: string, rating: "up" | "down") =>
    post<{ success: boolean }>("/api/v1/feedback", { question, answer, route, rating }),
  metrics: () => get<{ success: boolean; data: MetricsData }>("/api/v1/metrics"),
};
