from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
from threading import Lock
from typing import Any, Literal

MAX_RUNTIME_TRACES = 200
TraceOperation = Literal["inference.generate", "inference.benchmark"]
TraceStatus = Literal["success", "error"]

_traces: deque[dict[str, Any]] = deque(maxlen=MAX_RUNTIME_TRACES)
_lock = Lock()


def record_runtime_trace(
    *,
    request_id: str,
    operation: TraceOperation,
    model: str,
    status: TraceStatus,
    started_at: str,
    duration_ms: float,
    prompt_characters: int,
    requested_output_tokens: int,
    temperature: float,
    error_code: str | None = None,
    warmup_runs: int | None = None,
    iterations: int | None = None,
    concurrency: int | None = None,
    measured_requests: int | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    completion_tokens_known: int | None = None,
    completion_tokens_per_second: float | None = None,
) -> dict[str, Any]:
    """Record allow-listed runtime metadata; prompt/response bodies are never accepted."""
    if not isinstance(request_id, str) or not request_id or len(request_id) > 64:
        raise ValueError("Runtime trace request ID is invalid.")
    if operation not in {"inference.generate", "inference.benchmark"}:
        raise ValueError("Runtime trace operation is unsupported.")
    if status not in {"success", "error"}:
        raise ValueError("Runtime trace status is unsupported.")

    trace: dict[str, Any] = {
        "request_id": request_id,
        "operation": operation,
        "model": str(model)[:120],
        "status": status,
        "started_at": str(started_at)[:40],
        "completed_at": datetime.now(UTC).isoformat(),
        "duration_ms": round(max(0.0, float(duration_ms)), 2),
        "prompt_characters": max(0, int(prompt_characters)),
        "requested_output_tokens": max(0, int(requested_output_tokens)),
        "temperature": float(temperature),
        "warmup_runs": warmup_runs,
        "iterations": iterations,
        "concurrency": concurrency,
        "measured_requests": measured_requests,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "completion_tokens_known": completion_tokens_known,
        "completion_tokens_per_second": round(completion_tokens_per_second, 3) if completion_tokens_per_second is not None else None,
        "error_code": error_code,
    }
    with _lock:
        _traces.appendleft(trace)
        return dict(trace)


def list_runtime_traces(limit: int = 50) -> dict[str, Any]:
    """Return the most recent metadata-only traces, newest first."""
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_RUNTIME_TRACES:
        raise ValueError(f"Runtime trace limit must be between 1 and {MAX_RUNTIME_TRACES}.")
    with _lock:
        traces = [dict(item) for item in list(_traces)[:limit]]
        total = len(_traces)
    return {
        "schema_version": 1,
        "traces": traces,
        "total_retained": total,
        "limit": limit,
        "max_retained": MAX_RUNTIME_TRACES,
        "privacy": {
            "prompt_bodies_stored": False,
            "response_bodies_stored": False,
            "disk_persistence": False,
        },
    }


def clear_runtime_traces() -> dict[str, Any]:
    """Clear the in-memory trace buffer and return how many entries were removed."""
    with _lock:
        cleared = len(_traces)
        _traces.clear()
    return {
        "cleared": cleared,
        "remaining": 0,
        "disk_persistence": False,
    }
