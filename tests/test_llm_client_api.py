from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from axiom.api import llm_client as llm_api
from axiom.api import openai_compat
from axiom.core import llm_client


def _client(*routers) -> TestClient:
    app = FastAPI()
    for router in routers:
        app.include_router(router)
    return TestClient(app)


def test_provider_catalog_endpoint_is_read_only_and_secret_free() -> None:
    response = _client(llm_api.router).get("/api/llm/providers")

    assert response.status_code == 200
    body = response.json()
    assert body["credentials_persisted"] is False
    assert {item["id"] for item in body["providers"]} >= {
        "axiom-local", "openai", "anthropic", "gemini", "deepseek", "moonshot", "openai-compatible"
    }


def test_cloud_chat_endpoint_rejects_missing_consent_before_invoking_client(monkeypatch) -> None:
    def unexpected(*_args, **_kwargs):
        raise AssertionError("cloud inference must not run without consent")

    monkeypatch.setattr(llm_client, "chat", unexpected)
    response = _client(llm_api.router).post("/api/llm/chat", json={
        "provider": "deepseek",
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": "private question"}],
        "api_key": "test-secret",
        "consent": False,
    })

    assert response.status_code == 400
    assert "confirm" in response.json()["detail"].lower()
    assert "test-secret" not in response.text


def test_local_model_inventory_endpoint_returns_client_result(monkeypatch) -> None:
    monkeypatch.setattr(llm_client, "list_models", lambda provider, api_key=None, base_url=None: {
        "provider": provider, "models": ["tiny"], "credential_storage": "not_applicable", "execution": "local"
    })
    response = _client(llm_api.router).post("/api/llm/models", json={"provider": "axiom-local"})

    assert response.status_code == 200
    assert response.json()["models"] == ["tiny"]


def test_llm_chat_endpoint_returns_normalized_result(monkeypatch) -> None:
    captured = {}

    def fake_chat(provider, model, messages, **kwargs):
        captured.update({"provider": provider, "model": model, "messages": messages, **kwargs})
        return {
            "provider": "axiom-local",
            "model": "tiny",
            "response": "hello",
            "prompt_tokens": 2,
            "completion_tokens": 1,
            "credential_storage": "not_applicable",
            "execution": "local",
            "device": "cpu",
            "generated_at": "2026-01-01T00:00:00+00:00",
        }

    monkeypatch.setattr(llm_client, "chat", fake_chat)
    response = _client(llm_api.router).post("/api/llm/chat", json={
        "provider": "axiom-local",
        "model": "tiny",
        "messages": [{"role": "user", "content": "hello"}],
        "max_tokens": 16,
        "temperature": 0,
    })

    assert response.status_code == 200
    assert response.json()["response"] == "hello"
    assert captured["device"] == "auto"


def test_ollama_local_chat_does_not_require_cloud_consent(monkeypatch) -> None:
    captured = {}

    def fake_chat(provider, model, messages, **kwargs):
        captured.update({"provider": provider, "model": model, "messages": messages, **kwargs})
        return {
            "provider": "ollama-local",
            "model": model,
            "response": "local Ollama response",
            "prompt_tokens": 4,
            "completion_tokens": 2,
            "credential_storage": "not_applicable",
            "execution": "local",
            "device": "ollama",
            "generated_at": "2026-01-01T00:00:00+00:00",
        }

    monkeypatch.setattr(llm_client, "chat", fake_chat)
    response = _client(llm_api.router).post("/api/llm/chat", json={
        "provider": "ollama-local",
        "model": "qwen2.5:0.5b",
        "messages": [{"role": "user", "content": "hello local model"}],
        "consent": False,
        "max_tokens": 16,
        "temperature": 0,
    })

    assert response.status_code == 200
    assert response.json()["execution"] == "local"
    assert captured["provider"] == "ollama-local"
    assert captured["consent"] is False


def test_openai_compatible_bridge_requires_bearer_token_when_configured(monkeypatch) -> None:
    monkeypatch.setenv("AXIOM_OPENAI_API_TOKEN", "bridge-token-sentinel")
    monkeypatch.setattr(openai_compat, "_native_models", lambda: [{
        "name": "tiny", "path": "/trusted/tiny", "model_type": "llama"
    }])
    client = _client(openai_compat.router)

    unauthorized = client.get("/v1/models")
    bad_token = client.get("/v1/models", headers={"Authorization": "Bearer wrong-token"})
    authorized = client.get("/v1/models", headers={"Authorization": "Bearer bridge-token-sentinel"})

    assert unauthorized.status_code == 401
    assert unauthorized.headers["www-authenticate"] == "Bearer"
    assert bad_token.status_code == 401
    assert authorized.status_code == 200
    assert authorized.json()["data"][0]["id"] == "tiny"
    assert "bridge-token-sentinel" not in authorized.text
