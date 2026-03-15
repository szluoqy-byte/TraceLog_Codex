import { EventOut, SpanOut } from "../api";

type Props = {
  span: SpanOut | null;
  events: EventOut[];
};

function httpStatusCode(span: SpanOut): number | null {
  const attrs: any = span.attributes ?? {};
  const candidates = [
    attrs["http.status_code"],
    attrs["http.response.status_code"],
    attrs["rpc.http.status_code"],
  ];
  for (const v of candidates) {
    if (typeof v === "number" && Number.isFinite(v)) return v;
    if (typeof v === "string" && v.trim() && Number.isFinite(Number(v))) return Number(v);
  }

  const out: any = span.output;
  if (out && typeof out === "object") {
    const v = out.status;
    if (typeof v === "number" && Number.isFinite(v)) return v;
    if (typeof v === "string" && v.trim() && Number.isFinite(Number(v))) return Number(v);
  }
  return null;
}

function httpStatusClass(code: number): "ok" | "err" | "warn" {
  if (code >= 500) return "err";
  if (code >= 400) return "err";
  if (code >= 300) return "warn";
  return "ok";
}

function fmtTime(iso?: string | null) {
  if (!iso) return "-";
  const d = new Date(iso);
  return Number.isFinite(d.getTime()) ? d.toLocaleString() : iso;
}

function resourceSummary(span: SpanOut): string | null {
  const resource = (span.attributes as any)?.resource;
  if (!resource || typeof resource !== "object") return null;
  const svc = typeof resource["service.name"] === "string" ? resource["service.name"] : null;
  const inst = typeof resource["service.instance.id"] === "string" ? resource["service.instance.id"] : null;
  if (svc && inst) return `${svc} (${inst})`;
  return svc || inst;
}

function pretty(v: unknown): string {
  if (v === null || v === undefined) return "";
  try {
    return JSON.stringify(v, null, 2);
  } catch {
    return String(v);
  }
}

export default function SpanDetails({ span, events }: Props) {
  if (!span) return <div style={{ color: "var(--muted)" }}>Select a span.</div>;

  const relatedEvents = events.filter((e) => e.span_id === span.span_id);
  const res = resourceSummary(span);
  const code = httpStatusCode(span);
  const httpClass = code != null ? httpStatusClass(code) : null;
  const hasError =
    span.status_code === "error" ||
    span.error != null ||
    (code != null && code >= 400);
  const statusLabel =
    code != null
      ? `HTTP ${code}`
      : span.status_code ?? (span.error != null ? "error" : "ok");
  const statusColor =
    httpClass === "ok"
      ? "var(--good)"
      : httpClass === "warn"
        ? "var(--warn)"
        : hasError
          ? "var(--bad)"
          : "var(--muted)";
  const hasAnyTokens =
    span.token_prompt != null || span.token_completion != null || span.token_total != null;

  return (
    <div className="split">
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <div className="kv">
          <div className="k">Name</div>
          <div className="mono">{span.name}</div>
          <div className="k">Kind</div>
          <div>{span.kind}</div>
          {res && (
            <>
              <div className="k">Resource</div>
              <div className="mono">{res}</div>
            </>
          )}
          <div className="k">Span ID</div>
          <div className="mono">{span.span_id}</div>
          <div className="k">Parent</div>
          <div className="mono">{span.parent_span_id ?? "-"}</div>
          <div className="k">Start</div>
          <div className="mono">{fmtTime(span.start_time)}</div>
          <div className="k">End</div>
          <div className="mono">{fmtTime(span.end_time)}</div>
          <div className="k">Duration</div>
          <div>{span.duration_ms ?? "-"} ms</div>
          <div className="k">Status</div>
          <div style={{ color: statusColor }}>
            {statusLabel}
            {span.status_message ? `: ${span.status_message}` : ""}
          </div>
          {span.model && (
            <>
              <div className="k">Model</div>
              <div className="mono">{span.model}</div>
            </>
          )}
          {span.tool_name && (
            <>
              <div className="k">Tool</div>
              <div className="mono">{span.tool_name}</div>
            </>
          )}
          {span.tool_type && (
            <>
              <div className="k">Tool Type</div>
              <div className="mono">{span.tool_type}</div>
            </>
          )}
          {hasAnyTokens && (
            <>
              <div className="k">Tokens</div>
              <div className="mono">
                p={span.token_prompt ?? "-"} c={span.token_completion ?? "-"} t={span.token_total ?? "-"}
              </div>
            </>
          )}
        </div>

        {span.prompt && (
          <div>
            <div style={{ color: "var(--muted)", fontSize: 12, marginBottom: 6 }}>Prompt</div>
            <div className="pre">{span.prompt}</div>
          </div>
        )}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {span.input !== null && span.input !== undefined && (
          <div>
            <div style={{ color: "var(--muted)", fontSize: 12, marginBottom: 6 }}>Input</div>
            <div className="pre">{pretty(span.input)}</div>
          </div>
        )}
        {span.output !== null && span.output !== undefined && (
          <div>
            <div style={{ color: "var(--muted)", fontSize: 12, marginBottom: 6 }}>Output</div>
            <div className="pre">{pretty(span.output)}</div>
          </div>
        )}
        {span.error != null && (
          <div>
            <div style={{ color: "var(--bad)", fontSize: 12, marginBottom: 6 }}>Error</div>
            <div className="pre">{pretty(span.error)}</div>
          </div>
        )}
        {relatedEvents.length > 0 && (
          <div>
            <div style={{ color: "var(--muted)", fontSize: 12, marginBottom: 6 }}>Events</div>
            <div className="pre">{pretty(relatedEvents)}</div>
          </div>
        )}
        <div>
          <div style={{ color: "var(--muted)", fontSize: 12, marginBottom: 6 }}>Attributes</div>
          <div className="pre">{pretty(span.attributes)}</div>
        </div>
      </div>
    </div>
  );
}
