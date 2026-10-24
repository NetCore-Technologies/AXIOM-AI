from __future__ import annotations

from axiom.core import engine_fabric


def test_model_inventory_parses_ollama_and_openai_shapes():
    assert engine_fabric._model_ids("ollama", {"models": [{"name": "qwen2.5:0.5b"}, {"name": "../bad"}]}) == ["qwen2.5:0.5b"]
    assert engine_fabric._model_ids("llama-cpp", {"data": [{"id": "local-model"}, {"id": "bad model"}]}) == ["local-model"]


def test_dispatch_to_openai_compatible_backend_uses_fixed_chat_route(monkeypatch):
    observed = {}

    def fake_request(backend_id, path, payload=None, *, timeout):
        observed.update(backend_id=backend_id, path=path, payload=payload, timeout=timeout)
        return {
            "choices": [{"message": {"role": "assistant", "content": "Hello from llama.cpp"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 7, "completion_tokens": 4},
        }

    monkeypatch.setattr(engine_fabric, "_request_json", fake_request)
    result = engine_fabric.run_engine_backend_chat(
        "llama-cpp", "local-model", [{"role": "user", "content": "Say hello."}],
        max_new_tokens=24, temperature=0.2,
    )
    assert observed["backend_id"] == "llama-cpp"
    assert observed["path"] == "/v1/chat/completions"
    assert observed["payload"]["messages"] == [{"role": "user", "content": "Say hello."}]
    assert observed["payload"]["max_tokens"] == 24
    assert observed["timeout"] == engine_fabric._REQUEST_TIMEOUT
    assert result["response"] == "Hello from llama.cpp"
    assert result["eval_count"] == 4
    assert result["privacy"]["cloud_provider_used"] is False


def test_dispatch_to_ollama_uses_native_chat_options(monkeypatch):
    observed = {}

    def fake_request(backend_id, path, payload=None, *, timeout):
        observed.update(backend_id=backend_id, path=path, payload=payload)
        return {
            "message": {"role": "assistant", "content": "Local answer"},
            "done": True, "prompt_eval_count": 9, "eval_count": 6, "total_duration": 3_000_000,
        }

    monkeypatch.setattr(engine_fabric, "_request_json", fake_request)
    result = engine_fabric.run_engine_backend_chat(
        "ollama", "qwen2.5:0.5b", [{"role": "user", "content": "Answer locally."}],
    )
    assert observed["path"] == "/api/chat"
    assert observed["payload"]["options"] == {"num_predict": 256, "temperature": 0.7}
    assert result["response"] == "Local answer"
    assert result["total_duration_ms"] == 3
    assert result["execution"] == "local_loopback"


def test_native_engine_cannot_be_accidentally_dispatched_to_external_adapter(monkeypatch):
    monkeypatch.setattr(engine_fabric, "_request_json", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must not dispatch")))
    try:
        engine_fabric.run_engine_backend_chat("axiom-native", "local-model", [{"role": "user", "content": "Hi"}])
    except ValueError as exc:
        assert "trusted model-path" in str(exc)
    else:
        raise AssertionError("native engine must use its own trusted model path")


def test_chat_validates_before_any_local_request(monkeypatch):
    monkeypatch.setattr(engine_fabric, "_request_json", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must not dispatch")))
    invalid = [
        ("unknown", "model", [{"role": "user", "content": "Hi"}]),
        ("ollama", "http://remote.invalid", [{"role": "user", "content": "Hi"}]),
        ("ollama", "model", [{"role": "system", "content": "no user turn"}]),
    ]
    for backend, model, messages in invalid:
        try:
            engine_fabric.run_engine_backend_chat(backend, model, messages)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid route, model, or conversation must be rejected")
