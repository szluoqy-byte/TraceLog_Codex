from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select

from .db import get_session, init_db
from .ingest import ingest_bundle, ingest_event_envelope, ingest_span_envelope
from .models import Span, SpanEvent, Trace
from .schemas import (
    EventOut,
    IngestResponse,
    SpanOut,
    TraceDetail,
    TraceSummary,
)
from .utils import as_utc, json_loads, json_loads_optional


def create_app() -> FastAPI:
    app = FastAPI(title="TraceLog (Agent Trace Observability Prototype)", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def _startup() -> None:
        init_db()

    @app.get("/api/v1/healthz")
    def healthz() -> Dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/v1/ingest", response_model=IngestResponse)
    def ingest(payload: Dict[str, Any], session: Session = Depends(get_session)) -> IngestResponse:
        try:
            stats = ingest_bundle(session, payload)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid payload: {e}") from e
        return IngestResponse(ingested_traces=stats.trace_ids, span_count=stats.span_count, event_count=stats.event_count)

    @app.post("/api/v1/ingest/span", response_model=IngestResponse)
    def ingest_span(payload: Dict[str, Any], session: Session = Depends(get_session)) -> IngestResponse:
        """
        Distributed ingestion: a single span from a single node.
        """
        try:
            stats = ingest_span_envelope(session, payload)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid payload: {e}") from e
        return IngestResponse(ingested_traces=stats.trace_ids, span_count=stats.span_count, event_count=stats.event_count)

    @app.post("/api/v1/ingest/event", response_model=IngestResponse)
    def ingest_event(payload: Dict[str, Any], session: Session = Depends(get_session)) -> IngestResponse:
        """
        Distributed ingestion: a single event from a single node (out-of-order safe).
        """
        try:
            stats = ingest_event_envelope(session, payload)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid payload: {e}") from e
        return IngestResponse(ingested_traces=stats.trace_ids, span_count=stats.span_count, event_count=stats.event_count)

    @app.get("/api/v1/traces", response_model=List[TraceSummary])
    def list_traces(
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
        q: Optional[str] = Query(default=None, description="Search by trace_id or service_name"),
        session: Session = Depends(get_session),
    ) -> List[TraceSummary]:
        stmt = select(Trace)
        if q:
            like = f"%{q}%"
            stmt = stmt.where((Trace.trace_id.like(like)) | (Trace.service_name.like(like)))
        # SQLite doesn't support "NULLS LAST", so emulate by sorting nulls after non-nulls.
        stmt = (
            stmt.order_by(Trace.started_at.is_(None), Trace.started_at.desc(), Trace.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        traces = session.exec(stmt).all()
        return [
            TraceSummary(
                trace_id=t.trace_id,
                service_name=t.service_name,
                environment=t.environment,
                started_at=as_utc(t.started_at),
                duration_ms=t.duration_ms,
                span_count=t.span_count,
                error_count=t.error_count,
                status=t.status,
            )
            for t in traces
        ]

    @app.get("/api/v1/traces/{trace_id}", response_model=TraceDetail)
    def get_trace(trace_id: str, session: Session = Depends(get_session)) -> TraceDetail:
        trace = session.exec(select(Trace).where(Trace.trace_id == trace_id)).first()
        if trace is None:
            raise HTTPException(status_code=404, detail="Trace not found")

        spans = session.exec(
            select(Span)
            .where(Span.trace_id == trace_id)
            .order_by(Span.start_time.is_(None), Span.start_time.asc())
        ).all()
        events = session.exec(
            select(SpanEvent).where(SpanEvent.trace_id == trace_id).order_by(SpanEvent.time.asc())
        ).all()

        trace_summary = TraceSummary(
            trace_id=trace.trace_id,
            service_name=trace.service_name,
            environment=trace.environment,
            started_at=as_utc(trace.started_at),
            duration_ms=trace.duration_ms,
            span_count=trace.span_count,
            error_count=trace.error_count,
            status=trace.status,
        )

        span_out = [
            SpanOut(
                span_id=s.span_id,
                parent_span_id=s.parent_span_id,
                name=s.name,
                kind=s.kind,
                start_time=as_utc(s.start_time),
                end_time=as_utc(s.end_time),
                duration_ms=s.duration_ms,
                status_code=s.status_code,
                status_message=s.status_message,
                model=s.model,
                prompt=s.prompt,
                tool_name=s.tool_name,
                tool_type=s.tool_type,
                token_prompt=s.token_prompt,
                token_completion=s.token_completion,
                token_total=s.token_total,
                attributes=json_loads(s.attributes_json),
                input=json_loads_optional(s.input_json),
                output=json_loads_optional(s.output_json),
                error=json_loads_optional(s.error_json),
            )
            for s in spans
        ]

        event_out = [
            EventOut(
                event_id=e.event_id,
                span_id=e.span_id,
                name=e.name,
                time=as_utc(e.time),
                attributes=json_loads(e.attributes_json),
            )
            for e in events
        ]

        return TraceDetail(trace=trace_summary, spans=span_out, events=event_out)

    return app
