export type TraceSummary = {
  trace_id: string;
  service_name?: string | null;
  environment?: string | null;
  started_at?: string | null;
  duration_ms?: number | null;
  span_count: number;
  error_count: number;
  status?: string | null;
};

export type SpanOut = {
  span_id: string;
  parent_span_id?: string | null;
  name: string;
  kind: string;
  start_time?: string | null;
  end_time?: string | null;
  duration_ms?: number | null;
  status_code?: string | null;
  status_message?: string | null;
  model?: string | null;
  prompt?: string | null;
  tool_name?: string | null;
  tool_type?: string | null;
  token_prompt?: number | null;
  token_completion?: number | null;
  token_total?: number | null;
  attributes: Record<string, unknown>;
  input?: unknown;
  output?: unknown;
  error?: unknown;
};

export type EventOut = {
  event_id: string;
  span_id: string;
  name: string;
  time: string;
  attributes: Record<string, unknown>;
};

export type TraceDetail = {
  trace: TraceSummary;
  spans: SpanOut[];
  events: EventOut[];
};

async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return (await res.json()) as T;
}

export async function listTraces(q: string, limit = 50, offset = 0): Promise<TraceSummary[]> {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  if (q.trim()) params.set("q", q.trim());
  return apiGet<TraceSummary[]>(`/api/v1/traces?${params.toString()}`);
}

export async function getTrace(traceId: string): Promise<TraceDetail> {
  return apiGet<TraceDetail>(`/api/v1/traces/${encodeURIComponent(traceId)}`);
}

