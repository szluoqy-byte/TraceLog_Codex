from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EventIn(BaseModel):
    name: str
    time: datetime
    attributes: Dict[str, Any] = Field(default_factory=dict)


class SpanIn(BaseModel):
    span_id: str
    parent_span_id: Optional[str] = None
    name: str
    kind: str = "unknown"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    input: Optional[Dict[str, Any]] = None
    output: Optional[Dict[str, Any]] = None
    status: Optional[Dict[str, Any]] = None
    events: List[EventIn] = Field(default_factory=list)


class TraceIn(BaseModel):
    trace_id: str
    started_at: Optional[datetime] = None
    spans: List[SpanIn] = Field(default_factory=list)


class BundleIn(BaseModel):
    version: str = "tracelog.v1"
    resource: Dict[str, Any] = Field(default_factory=dict)
    traces: List[TraceIn] = Field(default_factory=list)


class SpanEnvelopeIn(BaseModel):
    """
    For distributed ingestion: one node reports one span (optionally with embedded events).
    The server merges spans into the trace by (trace_id, span_id).
    """

    version: str = "tracelog.v1"
    resource: Dict[str, Any] = Field(default_factory=dict)
    trace_id: str
    started_at: Optional[datetime] = None
    span: SpanIn


class EventEnvelopeIn(BaseModel):
    """
    For distributed ingestion: one node reports one event for a span.
    If the span does not exist yet, server will create a placeholder span.
    """

    version: str = "tracelog.v1"
    resource: Dict[str, Any] = Field(default_factory=dict)
    trace_id: str
    span_id: str
    event: EventIn


class IngestResponse(BaseModel):
    ingested_traces: List[str]
    span_count: int
    event_count: int


class TraceSummary(BaseModel):
    trace_id: str
    service_name: Optional[str] = None
    environment: Optional[str] = None
    started_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    span_count: int
    error_count: int
    status: Optional[str] = None


class EventOut(BaseModel):
    event_id: str
    span_id: str
    name: str
    time: datetime
    attributes: Dict[str, Any]


class SpanOut(BaseModel):
    span_id: str
    parent_span_id: Optional[str]
    name: str
    kind: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    duration_ms: Optional[int]
    status_code: Optional[str]
    status_message: Optional[str]
    model: Optional[str]
    prompt: Optional[str]
    tool_name: Optional[str]
    tool_type: Optional[str]
    token_prompt: Optional[int]
    token_completion: Optional[int]
    token_total: Optional[int]
    attributes: Dict[str, Any]
    input: Optional[Dict[str, Any]]
    output: Optional[Dict[str, Any]]
    error: Optional[Dict[str, Any]]


class TraceDetail(BaseModel):
    trace: TraceSummary
    spans: List[SpanOut]
    events: List[EventOut]
