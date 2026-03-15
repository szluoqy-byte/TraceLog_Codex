import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { listTraces, TraceSummary } from "../api";

function fmtMs(ms?: number | null) {
  if (ms === null || ms === undefined) return "-";
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}

function fmtTime(iso?: string | null) {
  if (!iso) return "-";
  const d = new Date(iso);
  return d.toLocaleString();
}

export default function TracesList() {
  const [q, setQ] = useState("");
  const [items, setItems] = useState<TraceSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const hint = useMemo(() => {
    return "Tip: ingest sample via curl.exe -d @samples/trace_sample.json";
  }, []);

  async function refresh() {
    setLoading(true);
    setErr(null);
    try {
      const data = await listTraces(q);
      setItems(data);
    } catch (e: any) {
      setErr(e?.message ?? String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="card">
      <div className="panel">
        <div className="toolbar">
          <input
            className="input"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search trace_id / service name"
          />
          <button className="btn" onClick={refresh} disabled={loading}>
            {loading ? "Loading..." : "Search"}
          </button>
          <span style={{ color: "var(--muted)", fontSize: 12 }}>{hint}</span>
        </div>
        {err && (
          <div style={{ marginTop: 10, color: "var(--bad)", fontSize: 13 }}>
            Failed to load: {err}
          </div>
        )}
      </div>

      <table className="table">
        <thead>
          <tr>
            <th>Trace</th>
            <th>Service</th>
            <th>Start</th>
            <th>Duration</th>
            <th>Spans</th>
            <th>Errors</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {items.map((t) => (
            <tr key={t.trace_id}>
              <td className="mono">
                <Link to={`/trace/${encodeURIComponent(t.trace_id)}`}>{t.trace_id.slice(0, 16)}...</Link>
              </td>
              <td>{t.service_name ?? "-"}</td>
              <td>{fmtTime(t.started_at)}</td>
              <td>{fmtMs(t.duration_ms)}</td>
              <td>{t.span_count}</td>
              <td style={{ color: t.error_count > 0 ? "var(--bad)" : "var(--muted)" }}>{t.error_count}</td>
              <td>
                <span className="pill">
                  <span className={`dot ${t.error_count > 0 ? "err" : "ok"}`} />
                  {t.status ?? (t.error_count > 0 ? "error" : "ok")}
                </span>
              </td>
            </tr>
          ))}
          {items.length === 0 && (
            <tr>
              <td colSpan={7} style={{ color: "var(--muted)", padding: 16 }}>
                No traces yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

