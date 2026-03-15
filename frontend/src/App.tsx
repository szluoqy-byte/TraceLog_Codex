import { Link, Route, Routes } from "react-router-dom";
import TracesList from "./pages/TracesList";
import TraceDetail from "./pages/TraceDetail";

export default function App() {
  return (
    <div className="shell">
      <div className="topbar">
        <div className="brand">
          <h1>
            <Link to="/">TraceLog</Link>
          </h1>
          <p>Agent trace observability prototype: span tree + waterfall + details</p>
        </div>
      </div>
      <Routes>
        <Route path="/" element={<TracesList />} />
        <Route path="/trace/:traceId" element={<TraceDetail />} />
      </Routes>
    </div>
  );
}

