from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    # Store as naive UTC in SQLite.
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Trace(SQLModel, table=True):
    trace_id: str = Field(primary_key=True, index=True)

    service_name: Optional[str] = Field(default=None, index=True)
    service_version: Optional[str] = Field(default=None, index=True)
    environment: Optional[str] = Field(default=None, index=True)

    started_at: Optional[datetime] = Field(default=None, index=True)
    ended_at: Optional[datetime] = Field(default=None, index=True)
    duration_ms: Optional[int] = Field(default=None, index=True)

    status: Optional[str] = Field(default=None, index=True)  # ok|error|unset
    span_count: int = Field(default=0, index=True)
    error_count: int = Field(default=0, index=True)

    created_at: datetime = Field(default_factory=utc_now, index=True)

    raw_json: Optional[str] = Field(default=None)


class Span(SQLModel, table=True):
    id: str = Field(primary_key=True, index=True)
    trace_id: str = Field(index=True, foreign_key="trace.trace_id")
    span_id: str = Field(index=True)
    parent_span_id: Optional[str] = Field(default=None, index=True)

    name: str = Field(index=True)
    kind: str = Field(index=True)  # agent|llm|tool|chain|retriever|unknown

    start_time: Optional[datetime] = Field(default=None, index=True)
    end_time: Optional[datetime] = Field(default=None, index=True)
    duration_ms: Optional[int] = Field(default=None, index=True)

    status_code: Optional[str] = Field(default=None, index=True)  # ok|error|unset
    status_message: Optional[str] = Field(default=None)

    model: Optional[str] = Field(default=None, index=True)
    prompt: Optional[str] = Field(default=None)

    tool_name: Optional[str] = Field(default=None, index=True)
    tool_type: Optional[str] = Field(default=None, index=True)

    token_prompt: Optional[int] = Field(default=None)
    token_completion: Optional[int] = Field(default=None)
    token_total: Optional[int] = Field(default=None)

    attributes_json: Optional[str] = Field(default=None)
    input_json: Optional[str] = Field(default=None)
    output_json: Optional[str] = Field(default=None)
    error_json: Optional[str] = Field(default=None)


class SpanEvent(SQLModel, table=True):
    event_id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True, index=True)
    trace_id: str = Field(index=True)
    span_id: str = Field(index=True)

    name: str = Field(index=True)
    time: datetime = Field(index=True)
    attributes_json: Optional[str] = Field(default=None)
