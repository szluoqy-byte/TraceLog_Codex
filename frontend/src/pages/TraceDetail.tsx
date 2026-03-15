import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getTrace, SpanOut, TraceDetail as TraceDetailType } from "../api";
import SpanTree from "../components/SpanTree";
import Waterfall from "../components/Waterfall";
import SpanDetails from "../components/SpanDetails";

export default function TraceDetail() {
  const { traceId } = useParams();
  const [data, setData] = useState<TraceDetailType | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [selectedSpanId, setSelectedSpanId] = useState<string | null>(null);

  useEffect(() => {
    if (!traceId) return;
    setLoading(true);
    setErr(null);
    getTrace(traceId)
      .then((d) => {
        setData(d);
        setSelectedSpanId(d.spans[0]?.span_id ?? null);
      })
      .catch((e) => setErr(e?.message ?? String(e)))
      .finally(() => setLoading(false));
  }, [traceId]);

  const selectedSpan: SpanOut | null = useMemo(() => {
    if (!data || !selectedSpanId) return null;
    return data.spans.find((s) => s.span_id === selectedSpanId) ?? null;
  }, [data, selectedSpanId]);

  if (!traceId) return null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <div className="card">
        <div className="panel" style={{ display: "flex", justifyContent: "space-between", gap: 14, flexWrap: "wrap" }}>
          <div>
            <div style={{ color: "var(--muted)", fontSize: 12 }}>Trace</div>
            <div className="mono" style={{ fontSize: 13 }}>{traceId}</div>
          </div>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <Link className="btn" to="/">Back</Link>
          </div>
        </div>
      </div>

      {loading && <div className="card"><div className="panel">Loading...</div></div>}
      {err && <div className="card"><div className="panel" style={{ color: "var(--bad)" }}>Failed: {err}</div></div>}

      {data && (
        <div className="row">
          <div className="card">
            <div className="panel">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                <div style={{ fontWeight: 600 }}>Span Tree</div>
                <div style={{ color: "var(--muted)", fontSize: 12 }}>{data.spans.length} spans</div>
              </div>
            </div>
            <SpanTree spans={data.spans} selectedSpanId={selectedSpanId} onSelect={setSelectedSpanId} />
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div className="card">
              <div className="panel">
                <div style={{ fontWeight: 600, marginBottom: 8 }}>Waterfall</div>
              </div>
              <Waterfall spans={data.spans} selectedSpanId={selectedSpanId} onSelect={setSelectedSpanId} />
            </div>

            <div className="card">
              <div className="panel">
                <div style={{ fontWeight: 600, marginBottom: 10 }}>Span Details</div>
                <SpanDetails span={selectedSpan} events={data.events} />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

