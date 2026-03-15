import { SpanOut } from "../api";

type Props = {
  spans: SpanOut[];
  selectedSpanId: string | null;
  onSelect: (spanId: string) => void;
};

type Node = {
  span: SpanOut;
  depth: number;
};

function buildTree(spans: SpanOut[]): Node[] {
  const byId = new Map<string, SpanOut>();
  const children = new Map<string, SpanOut[]>();
  for (const s of spans) {
    byId.set(s.span_id, s);
    const parent = s.parent_span_id ?? "__root__";
    const arr = children.get(parent) ?? [];
    arr.push(s);
    children.set(parent, arr);
  }
  for (const [k, arr] of children) {
    arr.sort((a, b) => (a.start_time ?? "").localeCompare(b.start_time ?? ""));
    children.set(k, arr);
  }

  const roots = children.get("__root__") ?? [];
  const out: Node[] = [];

  function walk(list: SpanOut[], depth: number) {
    for (const s of list) {
      out.push({ span: s, depth });
      const kid = children.get(s.span_id) ?? [];
      walk(kid, depth + 1);
    }
  }
  walk(roots, 0);

  // Fallback: if parent links are missing, just return in time order.
  if (out.length === 0 && spans.length > 0) {
    return spans
      .slice()
      .sort((a, b) => (a.start_time ?? "").localeCompare(b.start_time ?? ""))
      .map((s) => ({ span: s, depth: 0 }));
  }

  return out;
}

function kindLabel(kind: string) {
  if (kind === "llm") return "LLM";
  if (kind === "tool") return "Tool";
  if (kind === "agent") return "Agent";
  return kind;
}

export default function SpanTree({ spans, selectedSpanId, onSelect }: Props) {
  const nodes = buildTree(spans);
  return (
    <div style={{ padding: 10 }}>
      {nodes.map(({ span, depth }) => {
        const sel = span.span_id === selectedSpanId;
        const err = span.status_code === "error" || !!span.error;
        return (
          <div
            key={span.span_id}
            className={`treeItem ${sel ? "sel" : ""}`}
            onClick={() => onSelect(span.span_id)}
            style={{ paddingLeft: 10 + depth * 14 }}
          >
            <span className={`dot ${err ? "err" : "ok"}`} />
            <span className="pill" style={{ borderColor: "rgba(255,255,255,0.10)" }}>
              {kindLabel(span.kind)}
            </span>
            <div style={{ display: "flex", flexDirection: "column", minWidth: 0 }}>
              <div style={{ fontSize: 13, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                {span.name}
              </div>
              <div style={{ color: "var(--muted)", fontSize: 12, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                {span.model ? `model: ${span.model}` : span.tool_name ? `tool: ${span.tool_name}` : "\u00A0"}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

