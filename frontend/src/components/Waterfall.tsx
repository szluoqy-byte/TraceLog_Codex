import { SpanOut } from "../api";

type Props = {
  spans: SpanOut[];
  selectedSpanId: string | null;
  onSelect: (spanId: string) => void;
};

function t(iso?: string | null): number | null {
  if (!iso) return null;
  // Some backends emit 6-digit fractional seconds (microseconds). Date.parse is not consistent across engines,
  // so we normalize to millisecond precision.
  let s = iso.trim();
  // If timezone is missing, treat as UTC for this prototype.
  if (!/[zZ]$/.test(s) && !/[+-]\d{2}:\d{2}$/.test(s)) s += "Z";
  s = s.replace(/\.(\d{3})\d+(Z|[+-]\d{2}:\d{2})$/, ".$1$2");
  const n = Date.parse(s);
  return Number.isFinite(n) ? n : null;
}

function buildDepth(spans: SpanOut[]): Map<string, number> {
  const byId = new Map<string, SpanOut>();
  const children = new Map<string, string[]>();
  for (const s of spans) {
    byId.set(s.span_id, s);
    const parent = s.parent_span_id ?? "__root__";
    const arr = children.get(parent) ?? [];
    arr.push(s.span_id);
    children.set(parent, arr);
  }

  const depth = new Map<string, number>();
  const roots = children.get("__root__") ?? [];
  const queue: Array<{ id: string; d: number }> = roots.map((id) => ({ id, d: 0 }));
  while (queue.length) {
    const cur = queue.shift()!;
    depth.set(cur.id, cur.d);
    for (const kid of children.get(cur.id) ?? []) {
      queue.push({ id: kid, d: cur.d + 1 });
    }
  }
  // For orphan spans, default depth to 0.
  for (const s of spans) {
    if (!depth.has(s.span_id)) depth.set(s.span_id, 0);
  }
  return depth;
}

function buildOrder(spans: SpanOut[]): SpanOut[] {
  const byId = new Map<string, SpanOut>();
  const children = new Map<string, SpanOut[]>();
  for (const s of spans) {
    byId.set(s.span_id, s);
    const parent = s.parent_span_id ?? "__root__";
    const arr = children.get(parent) ?? [];
    arr.push(s);
    children.set(parent, arr);
  }

  const sortByStart = (a: SpanOut, b: SpanOut) => {
    const aStart = t(a.start_time);
    const bStart = t(b.start_time);
    if (aStart !== null && bStart !== null && aStart !== bStart) return aStart - bStart;
    if (aStart === null && bStart !== null) return 1;
    if (aStart !== null && bStart === null) return -1;
    const aEnd = t(a.end_time);
    const bEnd = t(b.end_time);
    if (aEnd !== null && bEnd !== null && aEnd !== bEnd) return aEnd - bEnd;
    return a.span_id.localeCompare(b.span_id);
  };

  for (const [k, arr] of children) {
    arr.sort(sortByStart);
    children.set(k, arr);
  }

  // Roots are spans with missing parent or parent=null.
  const roots: SpanOut[] = [];
  for (const s of spans) {
    if (!s.parent_span_id) {
      roots.push(s);
      continue;
    }
    if (!byId.has(s.parent_span_id)) roots.push(s);
  }
  roots.sort(sortByStart);

  const out: SpanOut[] = [];
  const visited = new Set<string>();

  function walk(span: SpanOut) {
    if (visited.has(span.span_id)) return;
    visited.add(span.span_id);
    out.push(span);
    for (const kid of children.get(span.span_id) ?? []) walk(kid);
  }

  for (const r of roots) walk(r);

  // Safety net for cycles/isolated nodes: append anything not reached.
  const remaining = spans.filter((s) => !visited.has(s.span_id)).sort(sortByStart);
  for (const s of remaining) walk(s);

  return out;
}

function resourceLabel(span: SpanOut): string | null {
  const resource = (span.attributes as any)?.resource;
  if (!resource || typeof resource !== "object") return null;
  const inst = resource["service.instance.id"];
  if (typeof inst === "string" && inst.trim()) return inst.trim();
  const svc = resource["service.name"];
  if (typeof svc === "string" && svc.trim()) return svc.trim();
  return null;
}

export default function Waterfall({ spans, selectedSpanId, onSelect }: Props) {
  const depth = buildDepth(spans);
  const times = spans
    .map((s) => t(s.start_time))
    .filter((x): x is number => x !== null);
  const minStart = times.length ? Math.min(...times) : Date.now();
  const ends = spans
    .map((s) => t(s.end_time))
    .filter((x): x is number => x !== null);
  const maxEnd = ends.length ? Math.max(...ends) : minStart + 1;
  const total = Math.max(1, maxEnd - minStart);

  // Waterfall should reflect dependency structure first (parent -> children),
  // while siblings are ordered by start_time.
  const ordered = buildOrder(spans);

  return (
    <div>
      {ordered.map((s) => {
        const st = t(s.start_time) ?? minStart;
        const et = t(s.end_time) ?? st;
        const leftPct = ((st - minStart) / total) * 100;
        const widthPct = (Math.max(1, et - st) / total) * 100;
        const sel = s.span_id === selectedSpanId;
        const err = s.status_code === "error" || !!s.error;
        const d = depth.get(s.span_id) ?? 0;
        const res = resourceLabel(s);
        return (
          <div
            key={s.span_id}
            className="waterRow"
            onClick={() => onSelect(s.span_id)}
            style={{ cursor: "pointer", background: sel ? "rgba(102, 166, 255, 0.08)" : "transparent" }}
            title={`${s.name} (${s.duration_ms ?? "-"} ms)`}
          >
            <div style={{ display: "flex", gap: 10, alignItems: "center", minWidth: 0, paddingLeft: 6 + d * 12 }}>
              <span className={`dot ${err ? "err" : "ok"}`} />
              <div style={{ minWidth: 0 }}>
                <div style={{ fontSize: 13, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                  {s.name}
                </div>
                <div style={{ color: "var(--muted)", fontSize: 12, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                  {s.kind === "llm" && s.model
                    ? `LLM ${s.model}`
                    : s.kind === "tool" && s.tool_name
                      ? `Tool ${s.tool_name}`
                      : s.kind}
                  {res ? ` · ${res}` : ""}
                </div>
              </div>
            </div>
            <div className="barWrap">
              <div className={`bar ${err ? "err" : ""}`} style={{ left: `${leftPct}%`, width: `${widthPct}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
