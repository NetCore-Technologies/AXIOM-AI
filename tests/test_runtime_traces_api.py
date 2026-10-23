from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from axiom.api import diagnostics, inference
from axiom.core.runtime_traces import clear_runtime_traces


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(inference.router)
    app.include_router(diagnostics.router)
    return TestClient(app)


def setup_function() -> None:
    clear_runtime_traces()


def teardown_function() -> None:
    clear_runtime_traces()


def test_generate_endpoint_returns_correlatable_request_id_and_never_traces_text(monkeypatch) -> None:
    monkeypatch.setattr(
        inference,
        "run_local_inference",
        lambda model, prompt, **kwargs: {
            "model": model,
            "response": "PRIVATE_RESPONSE_SENTINEL",
            "done": True,
            "prompt_eval_count": 4,
            "eval_count": 7,
            "generated_at": "ignored",
        },
    )
    response = _client().post(
        "/api/inference/generate",
        json={
            "model": "test-model",
            "prompt": "PRIVATE_PROMPT_SENTINEL",
            "num_predict": 32,
            "temperature": 0.2,
        },
    )

    assert response.status_code == 200
    request_id = response.headers["X-Request-ID"]
    assert response.json()["request_id"] == request_id
    assert response.json()["response"] == "PRIVATE_RESPONSE_SENTINEL"
    traces = _client().get("/api/diagnostics/runtime-traces").json()["traces"]
    trace = traces[0]
    assert trace["request_id"] == request_id
    assert trace["operation"] == "inference.generate"
    assert trace["status"] == "success"
    assert trace["prompt_characters"] == len("PRIVATE_PROMPT_SENTINEL")
    assert trace["completion_tokens"] == 7
    assert "PRIVATE_PROMPT_SENTINEL" not in str(trace)
    assert "PRIVATE_RESPONSE_SENTINEL" not in str(trace)


def test_generate_runtime_failure_records_safe_error_code(monkeypatch) -> None:
    from axiom.core.inference import InferenceRuntimeError

    def fail(*args, **kwargs):
        raise InferenceRuntimeError("sensitive raw runtime detail must not be returned")

    monkeypatch.setattr(inference, "run_local_inference", fail)
    client = _client()
    response = client.post(
        "/api/inference/generate",
        json={"model": "test-model", "prompt": "safe prompt"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Local inference runtime did not complete the request."
    assert "sensitive raw runtime detail" not in response.text
    trace = client.get("/api/diagnostics/runtime-traces").json()["traces"][0]
    assert trace["request_id"] == response.headers["X-Request-ID"]
    assert trace["status"] == "error"
    assert trace["error_code"] == "runtime_unavailable"
    assert "safe prompt" not in str(trace)


def test_runtime_trace_endpoints_list_and_clear_the_same_process_buffer() -> None:
    from axiom.core.runtime_traces import record_runtime_trace

    record_runtime_trace(
        request_id="same-buffer",
        operation="inference.generate",
        model="test-model",
        status="success",
        started_at="2026-10-22T00:00:00+00:00",
        duration_ms=10,
        prompt_characters=12,
        requested_output_tokens=20,
        temperature=0.2,
    )
    client = _client()
    listed = client.get("/api/diagnostics/runtime-traces")

    assert listed.status_code == 200
    assert listed.json()["traces"][0]["request_id"] == "same-buffer"
    cleared = client.delete("/api/diagnostics/runtime-traces")
    assert cleared.status_code == 200
    assert cleared.json()["cleared"] == 1
    assert client.get("/api/diagnostics/runtime-traces").json()["traces"] == []
