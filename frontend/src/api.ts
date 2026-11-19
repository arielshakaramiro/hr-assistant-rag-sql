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

// One prior exchange sent back for follow-up context (backend stays stateless).
export interface Turn {
  question: string;
  answer: string;
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
  p95_ttft_ms: number;
  mean_cost_usd: number;
  failure_rate: number;
  by_route: Record<string, number>;
}

// One roster entry on the HR-admin team dashboard (whole-company, aggregate — no raw rows).
export interface RosterRow {
  full_name: string;
  department: string;
  role: string;
  entitlement_days: number;
  used_days: number;
  remaining_days: number;
}

export interface TeamOverview {
  headcount: number;
  by_department: Record<string, number>;
  leave: {
    entitlement_days: number;
    used_days: number;
    remaining_days: number;
    pending_requests: number;
  };
  attendance: Record<string, number>;
  claims_count: Record<string, number>;
  claims_amount: Record<string, number>;
  roster: RosterRow[];
}

// The signed-in employee's own records (GET /api/v1/me/*). Read-only, scoped to themselves.
export interface LeaveRecordRow {
  leave_type: string;
  start_date: string;
  end_date: string;
  days: number;
  status: string;
}

export interface LeaveSummary {
  entitlement_days: number;
  used_days: number;
  remaining_days: number;
  records: LeaveRecordRow[];
}

export interface AttendanceRecordRow {
  work_date: string;
  status: string;
  minutes_late: number;
}

export interface AttendanceSummary {
  counts: Record<string, number>;
  records: AttendanceRecordRow[];
}

export interface ClaimRow {
  claim_type: string;
  amount: number;
  currency: string;
  status: string;
  submitted: string;
}

export interface ClaimsSummary {
  claims: ClaimRow[];
  totals_count: Record<string, number>;
  totals_amount: Record<string, number>;
}

// The metadata envelope streamed before any answer tokens (everything but the answer text).
export interface StreamMeta {
  route: Route;
  route_reason: string;
  confidence: Confidence;
  outcome: string;
  sources: Sources;
}

export interface StreamHandlers {
  onMeta: (meta: StreamMeta) => void;
  onToken: (text: string) => void;
  onDone: () => void;
  onError: () => void;
}

// Stream an answer over SSE: reads the response body, parses event/data frames, and dispatches
// to the handlers. Same-origin, so the session cookie flows automatically.
async function askStream(
  question: string,
  history: Turn[],
  h: StreamHandlers,
): Promise<void> {
  let r: Response;
  try {
    r = await fetch("/api/v1/chat/ask/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, history }),
    });
  } catch {
    h.onError();
    return;
  }
  if (!r.ok || !r.body) {
    h.onError();
    return;
  }
  const reader = r.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      // SSE frames are separated by a blank line.
      let sep: number;
      while ((sep = buffer.indexOf("\n\n")) !== -1) {
        const frame = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);
        dispatchFrame(frame, h);
      }
    }
  } catch {
    h.onError();
  }
}

function dispatchFrame(frame: string, h: StreamHandlers): void {
  let event = "message";
  let data = "";
  for (const line of frame.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) data += line.slice(5).trim();
  }
  if (!data) return;
  const payload = JSON.parse(data);
  if (event === "meta") h.onMeta(payload as StreamMeta);
  else if (event === "token") h.onToken(payload.text as string);
  else if (event === "done") h.onDone();
}

export const api = {
  login: (email: string, password: string) =>
    post<{ success: boolean; data: { id: number; full_name: string } }>(
      "/api/v1/auth/login",
      { email, password },
    ),
  logout: () => post<{ success: boolean }>("/api/v1/auth/logout", {}),
  me: () => get<{ success: boolean; data: Me }>("/api/v1/auth/me"),
  ask: (question: string, history: Turn[] = []) =>
    post<{ success: boolean; data: ChatData }>("/api/v1/chat/ask", { question, history }),
  askStream,
  feedback: (question: string, answer: string, route: string, rating: "up" | "down") =>
    post<{ success: boolean }>("/api/v1/feedback", { question, answer, route, rating }),
  metrics: () => get<{ success: boolean; data: MetricsData }>("/api/v1/metrics"),
  team: () => get<{ success: boolean; data: TeamOverview }>("/api/v1/admin/team"),
  myLeave: () => get<{ success: boolean; data: LeaveSummary }>("/api/v1/me/leave"),
  myAttendance: () =>
    get<{ success: boolean; data: AttendanceSummary }>("/api/v1/me/attendance"),
  myClaims: () => get<{ success: boolean; data: ClaimsSummary }>("/api/v1/me/claims"),
  // Health is a bare {status, version} (no success/data envelope).
  health: () => get<{ status: string; version: string }>("/api/v1/health"),
};
