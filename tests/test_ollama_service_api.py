from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from axiom.api import inference
from axiom.core.ollama_service import OllamaServiceError


def _client(client=("testclient", 50000)) -> TestClient:
    app = FastAPI()
    app.include_router(inference.router)
    return TestClient(app, client=client)


def test_status_uses_managed_runtime_report(monkeypatch):
    expected = {
        "backend": "ollama", "endpoint": "http://127.0.0.1:11434",
        "runtime_installed": True, "status": "offline", "models": [],
        "error": "offline", "checked_at": "2026-10-24T00:00:00+00:00",
        "service_managed_by_axiom": False, "service_can_start": True,
        "service_can_stop": False, "service_control_scope": "loopback_only",
        "service_message": "ready",
    }
    monkeypatch.setattr(inference, "managed_service_status", lambda: expected)

    response = _client().get("/api/inference/status")

    assert response.status_code == 200
    assert response.json() == expected


def test_start_service_maps_startup_errors_to_actionable_response(monkeypatch):
    monkeypatch.setattr(
        inference, "start_service",
        lambda: (_ for _ in ()).throw(OllamaServiceError("Ollama binary is missing.")),
    )

    response = _client().post("/api/inference/service/start", json={})

    assert response.status_code == 503
    assert response.json()["detail"] == "Ollama binary is missing."


def test_stop_service_maps_unowned_process_refusal_to_conflict(monkeypatch):
    monkeypatch.setattr(
        inference, "stop_service",
        lambda: (_ for _ in ()).throw(OllamaServiceError("Will not stop an unowned service.")),
    )

    response = _client().post("/api/inference/service/stop", json={})

    assert response.status_code == 409
    assert "unowned" in response.json()["detail"]


def test_model_pull_endpoint_returns_a_bounded_job(monkeypatch):
    expected = {
        "id": "a" * 32, "model": "qwen2.5:0.5b", "status": "queued",
        "created_at": "2026-10-24T00:00:00+00:00", "updated_at": "2026-10-24T00:00:00+00:00",
        "progress": "Queued", "percent": None, "logs": [], "error": None,
        "cancel_requested": False,
    }
    captured = {}
    def fake_start(model):
        captured["model"] = model
        return expected
    monkeypatch.setattr(inference, "start_model_pull", fake_start)

    response = _client().post("/api/inference/models/pull", json={"model": "qwen2.5:0.5b"})

    assert response.status_code == 200
    assert response.json() == expected
    assert captured["model"] == "qwen2.5:0.5b"


def test_model_pull_rejects_remote_urls_before_queueing(monkeypatch):
    monkeypatch.setattr(inference, "start_model_pull", lambda *_args: AssertionError("must not queue a URL"))

    response = _client().post("/api/inference/models/pull", json={"model": "https://example.com/model"})

    assert response.status_code == 422


def test_runtime_management_rejects_nonlocal_clients_by_default(monkeypatch):
    monkeypatch.delenv("AXIOM_ALLOW_REMOTE_RUNTIME_MANAGEMENT", raising=False)
    monkeypatch.setattr(inference, "start_service", lambda: (_ for _ in ()).throw(AssertionError("must be blocked")))

    response = _client(client=("192.168.1.42", 50000)).post("/api/inference/service/start", json={})

    assert response.status_code == 403
