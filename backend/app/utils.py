from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def parse_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value.astimezone(timezone.utc) if value.tzinfo else value
        # Store as naive UTC in SQLite (SQLite has no real timezone-aware datetime type).
        return dt.replace(tzinfo=None)
    if not isinstance(value, str):
        return None
    # Accept "Z" suffix.
    s = value.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)
    return dt.replace(tzinfo=None)


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


def json_loads(value: Optional[str]) -> Dict[str, Any]:
    if not value:
        return {}
    try:
        obj = json.loads(value)
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {"_": obj}


def json_loads_optional(value: Optional[str]):
    if not value:
        return None
    try:
        return json.loads(value)
    except Exception:
        return None


def duration_ms(start: Optional[datetime], end: Optional[datetime]) -> Optional[int]:
    if not start or not end:
        return None
    return max(0, int((end - start).total_seconds() * 1000))


def as_utc(value: Optional[datetime]) -> Optional[datetime]:
    """
    Convert a naive datetime (stored as UTC) to timezone-aware UTC for API responses.
    """
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc)
    return value.replace(tzinfo=timezone.utc)
