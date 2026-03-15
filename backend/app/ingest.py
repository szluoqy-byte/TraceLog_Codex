from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from sqlmodel import Session, select

from .models import Span, SpanEvent, Trace
from .schemas import BundleIn, EventEnvelopeIn, SpanEnvelopeIn
from .utils import duration_ms, json_dumps, parse_dt


@dataclass
class IngestStats:
    trace_ids: List[str]
    span_count: int
    event_count: int


def _event_exists(
    session: Session,
    trace_id: str,
    span_id: str,
    name: str,
    time,
    attributes_json: Optional[str],
) -> bool:
    # Prevent duplicate inserts when the same payload is ingested multiple times.
    stmt = select(SpanEvent).where(
        (SpanEvent.trace_id == trace_id)
        & (SpanEvent.span_id == span_id)
        & (SpanEvent.name == name)
        & (SpanEvent.time == time)
        & (SpanEvent.attributes_json == attributes_json)
    )
    return session.exec(stmt).first() is not None


def _resource_fields(resource: Dict[str, Any]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    service_name = resource.get("service.name")
    service_version = resource.get("service.version")
    environment = resource.get("deployment.environment")
    return (
        service_name if isinstance(service_name, str) else None,
        service_version if isinstance(service_version, str) else None,
        environment if isinstance(environment, str) else None,
    )


def _extract_model(attrs: Dict[str, Any]) -> Optional[str]:
    return (
        attrs.get("gen_ai.request.model")
        or attrs.get("llm.model")
        or attrs.get("model")
        or attrs.get("openai.model")
    )


def _extract_prompt(attrs: Dict[str, Any]) -> Optional[str]:
    prompt = attrs.get("gen_ai.prompt") or attrs.get("llm.prompt") or attrs.get("prompt")
    if isinstance(prompt, str):
        return prompt
    return None


def _extract_tool(attrs: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    tool_name = attrs.get("tool.name") or attrs.get("gen_ai.tool.name") or attrs.get("tool")
    tool_type = attrs.get("tool.type") or attrs.get("gen_ai.tool.type")
    return (tool_name if isinstance(tool_name, str) else None, tool_type if isinstance(tool_type, str) else None)


def _extract_tokens(attrs: Dict[str, Any]) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    def to_int(v: Any) -> Optional[int]:
        try:
            return int(v)
        except Exception:
            return None

    # Support both legacy-ish naming (prompt/completion) and OTel GenAI semconv naming (input/output).
    prompt = to_int(
        attrs.get("gen_ai.usage.input_tokens")
        or attrs.get("gen_ai.usage.prompt_tokens")
        or attrs.get("llm.usage.prompt_tokens")
    )
    completion = to_int(
        attrs.get("gen_ai.usage.output_tokens")
        or attrs.get("gen_ai.usage.completion_tokens")
        or attrs.get("llm.usage.completion_tokens")
    )
    total = to_int(
        attrs.get("gen_ai.usage.total_tokens")
        or attrs.get("llm.usage.total_tokens")
        or attrs.get("gen_ai.usage.tokens")
    )
    if total is None and prompt is not None and completion is not None:
        total = prompt + completion
    return prompt, completion, total


def _extract_status(span_in: Any) -> Tuple[Optional[str], Optional[str], Optional[Dict[str, Any]]]:
    status = getattr(span_in, "status", None) or {}
    if not isinstance(status, dict):
        status = {}
    code = status.get("code")
    message = status.get("message")
    if isinstance(code, str):
        code_norm = code.lower()
        if code_norm in ("ok", "error", "unset"):
            return code_norm, message if isinstance(message, str) else None, None
    # Derive from attributes/event-style error flags
    attrs = getattr(span_in, "attributes", None) or {}
    err = attrs.get("error") or attrs.get("exception")
    if err is None:
        return None, None, None
    if isinstance(err, dict):
        return "error", None, err
    if isinstance(err, str):
        return "error", None, {"message": err}
    return "error", None, {"message": str(err)}


def ingest_bundle(session: Session, payload: Dict[str, Any]) -> IngestStats:
    bundle = BundleIn.model_validate(payload)
    resource = bundle.resource or {}
    service_name, service_version, environment = _resource_fields(resource)

    ingested_trace_ids: List[str] = []
    span_count = 0
    event_count = 0

    for trace_in in bundle.traces:
        trace_id = trace_in.trace_id
        ingested_trace_ids.append(trace_id)

        # Compute aggregate time bounds from spans if not provided.
        min_start = parse_dt(trace_in.started_at)
        max_end = None
        errors = 0

        for s in trace_in.spans:
            st = parse_dt(s.start_time)
            et = parse_dt(s.end_time)
            if st and (min_start is None or st < min_start):
                min_start = st
            if et and (max_end is None or et > max_end):
                max_end = et
            code, _, _ = _extract_status(s)
            if code == "error":
                errors += 1

        tr = session.exec(select(Trace).where(Trace.trace_id == trace_id)).first()
        if tr is None:
            tr = Trace(trace_id=trace_id)

        tr.service_name = service_name or tr.service_name
        tr.service_version = service_version or tr.service_version
        tr.environment = environment or tr.environment
        tr.started_at = min_start
        tr.ended_at = max_end
        tr.duration_ms = duration_ms(min_start, max_end)
        tr.span_count = len(trace_in.spans)
        tr.error_count = errors
        tr.status = "error" if errors > 0 else "ok"
        tr.raw_json = json_dumps(payload)

        session.add(tr)

        for span_in in trace_in.spans:
            attrs = span_in.attributes or {}
            model = _extract_model(attrs)
            prompt = _extract_prompt(attrs)
            tool_name, tool_type = _extract_tool(attrs)
            t_prompt, t_completion, t_total = _extract_tokens(attrs)
            st = parse_dt(span_in.start_time)
            et = parse_dt(span_in.end_time)
            code, message, derived_error = _extract_status(span_in)

            # Upsert span
            span_pk = f"{trace_id}:{span_in.span_id}"
            sp = session.exec(select(Span).where(Span.id == span_pk)).first()
            if sp is None:
                sp = Span(id=span_pk, trace_id=trace_id, span_id=span_in.span_id, name=span_in.name, kind=span_in.kind)

            sp.id = span_pk
            sp.trace_id = trace_id
            sp.span_id = span_in.span_id
            sp.parent_span_id = span_in.parent_span_id
            sp.name = span_in.name
            sp.kind = span_in.kind or "unknown"
            sp.start_time = st
            sp.end_time = et
            sp.duration_ms = duration_ms(st, et)
            sp.status_code = code
            sp.status_message = message
            sp.model = model
            sp.prompt = prompt
            sp.tool_name = tool_name
            sp.tool_type = tool_type
            sp.token_prompt = t_prompt
            sp.token_completion = t_completion
            sp.token_total = t_total
            sp.attributes_json = json_dumps(attrs) if attrs else None
            sp.input_json = json_dumps(span_in.input) if span_in.input is not None else None
            sp.output_json = json_dumps(span_in.output) if span_in.output is not None else None
            if derived_error is not None:
                sp.error_json = json_dumps(derived_error)
            else:
                sp.error_json = None
            session.add(sp)
            span_count += 1

            for ev in span_in.events:
                # For prototype simplicity: always insert new events.
                ev_time = parse_dt(ev.time) or ev.time
                attrs_json = json_dumps(ev.attributes) if ev.attributes else None
                if not _event_exists(session, trace_id, span_in.span_id, ev.name, ev_time, attrs_json):
                    session.add(
                        SpanEvent(
                            trace_id=trace_id,
                            span_id=span_in.span_id,
                            name=ev.name,
                            time=ev_time,
                            attributes_json=attrs_json,
                        )
                    )
                    event_count += 1

    session.commit()
    return IngestStats(trace_ids=ingested_trace_ids, span_count=span_count, event_count=event_count)


def _recompute_trace_aggregates(session: Session, trace_id: str) -> None:
    spans = session.exec(select(Span).where(Span.trace_id == trace_id)).all()
    if not spans:
        return

    min_start = None
    max_end = None
    errors = 0

    for s in spans:
        if s.start_time and (min_start is None or s.start_time < min_start):
            min_start = s.start_time
        if s.end_time and (max_end is None or s.end_time > max_end):
            max_end = s.end_time
        if s.status_code == "error" or (s.error_json is not None and s.error_json != ""):
            errors += 1

    tr = session.exec(select(Trace).where(Trace.trace_id == trace_id)).first()
    if tr is None:
        tr = Trace(trace_id=trace_id)

    tr.started_at = min_start
    tr.ended_at = max_end
    tr.duration_ms = duration_ms(min_start, max_end)
    tr.span_count = len(spans)
    tr.error_count = errors
    tr.status = "error" if errors > 0 else "ok"
    session.add(tr)


def ingest_span_envelope(session: Session, payload: Dict[str, Any]) -> IngestStats:
    """
    Distributed ingestion: one node reports one span. The server upserts and merges by (trace_id, span_id).
    Supports out-of-order arrival; trace aggregates are recomputed after write.
    """

    env = SpanEnvelopeIn.model_validate(payload)
    span_raw = payload.get("span") if isinstance(payload.get("span"), dict) else {}
    resource = env.resource or {}
    service_name, service_version, environment = _resource_fields(resource)

    trace_id = env.trace_id
    span_in = env.span

    tr = session.exec(select(Trace).where(Trace.trace_id == trace_id)).first()
    if tr is None:
        tr = Trace(trace_id=trace_id)
    # In distributed traces, many services will report spans. Prefer the entry/root span's service as trace.service_name.
    if span_in.parent_span_id is None and service_name:
        tr.service_name = service_name
    elif tr.service_name is None and service_name:
        tr.service_name = service_name

    if span_in.parent_span_id is None and service_version:
        tr.service_version = service_version
    elif tr.service_version is None and service_version:
        tr.service_version = service_version

    if tr.environment is None and environment:
        tr.environment = environment
    session.add(tr)

    # For distributed ingestion, spans may arrive as partial updates.
    # Merge behavior: only overwrite fields if the corresponding key exists in the incoming payload.
    has_attributes = "attributes" in span_raw
    has_input = "input" in span_raw
    has_output = "output" in span_raw
    has_status = "status" in span_raw
    has_start = "start_time" in span_raw
    has_end = "end_time" in span_raw
    has_parent = "parent_span_id" in span_raw
    has_kind = "kind" in span_raw
    has_name = "name" in span_raw

    attrs = span_in.attributes or {}
    if has_attributes and resource:
        # Attach resource to span attributes for debugging which node/service emitted this span.
        attrs = dict(attrs)
        attrs.setdefault("resource", resource)

    model = _extract_model(attrs) if has_attributes else None
    prompt = _extract_prompt(attrs) if has_attributes else None
    tool_name, tool_type = _extract_tool(attrs) if has_attributes else (None, None)
    t_prompt, t_completion, t_total = _extract_tokens(attrs) if has_attributes else (None, None, None)
    st = parse_dt(span_in.start_time) if has_start else None
    et = parse_dt(span_in.end_time) if has_end else None
    code, message, derived_error = _extract_status(span_in) if has_status or has_attributes else (None, None, None)

    span_pk = f"{trace_id}:{span_in.span_id}"
    sp = session.exec(select(Span).where(Span.id == span_pk)).first()
    if sp is None:
        sp = Span(id=span_pk, trace_id=trace_id, span_id=span_in.span_id, name=span_in.name, kind=span_in.kind)

    sp.id = span_pk
    sp.trace_id = trace_id
    sp.span_id = span_in.span_id
    if has_parent:
        sp.parent_span_id = span_in.parent_span_id
    if has_name:
        sp.name = span_in.name
    if has_kind:
        sp.kind = span_in.kind or "unknown"
    if has_start:
        sp.start_time = st
    if has_end:
        sp.end_time = et
    if has_start or has_end:
        sp.duration_ms = duration_ms(sp.start_time, sp.end_time)

    if has_status or has_attributes:
        sp.status_code = code
        sp.status_message = message
        sp.error_json = json_dumps(derived_error) if derived_error is not None else None

    if has_attributes:
        sp.model = model
        sp.prompt = prompt
        sp.tool_name = tool_name
        sp.tool_type = tool_type
        sp.token_prompt = t_prompt
        sp.token_completion = t_completion
        sp.token_total = t_total
        sp.attributes_json = json_dumps(attrs) if attrs else None

    if has_input:
        sp.input_json = json_dumps(span_in.input) if span_in.input is not None else None
    if has_output:
        sp.output_json = json_dumps(span_in.output) if span_in.output is not None else None
    session.add(sp)

    event_count = 0
    for ev in span_in.events:
        ev_time = parse_dt(ev.time) or ev.time
        attrs_json = json_dumps(ev.attributes) if ev.attributes else None
        if not _event_exists(session, trace_id, span_in.span_id, ev.name, ev_time, attrs_json):
            session.add(
                SpanEvent(
                    trace_id=trace_id,
                    span_id=span_in.span_id,
                    name=ev.name,
                    time=ev_time,
                    attributes_json=attrs_json,
                )
            )
            event_count += 1

    _recompute_trace_aggregates(session, trace_id)
    session.commit()
    return IngestStats(trace_ids=[trace_id], span_count=1, event_count=event_count)


def ingest_event_envelope(session: Session, payload: Dict[str, Any]) -> IngestStats:
    """
    Distributed ingestion: one node reports one event for a span.
    If span does not exist yet, create a placeholder span and still accept the event (out-of-order safe).
    """

    env = EventEnvelopeIn.model_validate(payload)
    resource = env.resource or {}
    service_name, service_version, environment = _resource_fields(resource)

    trace_id = env.trace_id
    span_id = env.span_id

    tr = session.exec(select(Trace).where(Trace.trace_id == trace_id)).first()
    if tr is None:
        tr = Trace(trace_id=trace_id)
    if tr.service_name is None and service_name:
        tr.service_name = service_name
    if tr.service_version is None and service_version:
        tr.service_version = service_version
    if tr.environment is None and environment:
        tr.environment = environment
    session.add(tr)

    span_pk = f"{trace_id}:{span_id}"
    sp = session.exec(select(Span).where(Span.id == span_pk)).first()
    if sp is None:
        sp = Span(id=span_pk, trace_id=trace_id, span_id=span_id, name="(unknown span)", kind="unknown")
        session.add(sp)

    ev = env.event
    attrs = ev.attributes or {}
    if resource:
        attrs = dict(attrs)
        attrs.setdefault("resource", resource)

    ev_time = parse_dt(ev.time) or ev.time
    attrs_json = json_dumps(attrs) if attrs else None
    if not _event_exists(session, trace_id, span_id, ev.name, ev_time, attrs_json):
        session.add(
            SpanEvent(
                trace_id=trace_id,
                span_id=span_id,
                name=ev.name,
                time=ev_time,
                attributes_json=attrs_json,
            )
        )

    _recompute_trace_aggregates(session, trace_id)
    session.commit()
    return IngestStats(trace_ids=[trace_id], span_count=0, event_count=1)
