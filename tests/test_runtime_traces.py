from __future__ import annotations

import pytest

from axiom.core.runtime_traces import (
    MAX_RUNTIME_TRACES,
    clear_runtime_traces,
    list_runtime_traces,
    record_runtime_trace,
)


def _record(index: int) -> dict:
    return record_runtime_trace(
        request_id=f"request-{index:03d}",
        operation="inference.generate",
        model="test-model",
        status="success",
        started_at="2026-10-22T10:00:00+00:00",
        duration_ms=23.5,
        prompt_characters=100,
        requested_output_tokens=64,
        temperature=0.2,
        prompt_tokens=12,
        completion_tokens=8,
    )


def test_trace_store_is_bounded_and_newest_first() -> None:
    clear_runtime_traces()
    for index in range(MAX_RUNTIME_TRACES + 5):
        _record(index)

    report = list_runtime_traces(10)
    assert report["total_retained"] == MAX_RUNTIME_TRACES
    assert report["max_retained"] == MAX_RUNTIME_TRACES
    assert report["traces"][0]["request_id"] == f"request-{MAX_RUNTIME_TRACES + 4:03d}"
    assert report["traces"][-1]["request_id"] == f"request-{MAX_RUNTIME_TRACES - 5:03d}"
    assert len(report["traces"]) == 10
    assert report["privacy"] == {
        "prompt_bodies_stored": False,
        "response_bodies_stored": False,
        "disk_persistence": False,
    }
    clear_runtime_traces()


def test_trace_records_only_allowlisted_metadata_not_prompt_or_response() -> None:
    clear_runtime_traces()
    trace = record_runtime_trace(
        request_id="trace-123",
        operation="inference.benchmark",
        model="test-model",
        status="success",
        started_at="2026-10-22T10:00:00+00:00",
        duration_ms=111.2,
        prompt_characters=27,
        requested_output_tokens=32,
        temperature=0.4,
        warmup_runs=1,
        iterations=2,
        concurrency=2,
        measured_requests=4,
        completion_tokens=20,
        completion_tokens_known=4,
        completion_tokens_per_second=35.7,
    )

    assert trace["request_id"] == "trace-123"
    assert trace["operation"] == "inference.benchmark"
    assert trace["duration_ms"] == 111.2
    assert trace["prompt_characters"] == 27
    assert "prompt" not in trace
    assert "response" not in trace
    assert "generated_text" not in trace
    assert "API_KEY=SECRET_SENTINEL" not in str(trace)
    clear_runtime_traces()


@pytest.mark.parametrize("limit", [0, -1, MAX_RUNTIME_TRACES + 1, True])
def test_trace_listing_rejects_invalid_limits(limit: int) -> None:
    with pytest.raises(ValueError, match="limit"):
        list_runtime_traces(limit)


def test_clear_reports_removed_count_and_leaves_empty_buffer() -> None:
    clear_runtime_traces()
    _record(1)
    _record(2)
    result = clear_runtime_traces()
    assert result == {"cleared": 2, "remaining": 0, "disk_persistence": False}
    assert list_runtime_traces()["total_retained"] == 0
