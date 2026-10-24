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


def test_benchmark_returns_measured_metadata_without_model_text(monkeypatch):
    calls = []

    def fake_chat(backend_id, model, messages, **kwargs):
        calls.append((backend_id, model, messages, kwargs))
        return {
            "response": "DO_NOT_RETURN_THIS_MODEL_TEXT",
            "eval_count": 8,
            "total_duration_ms": 12.0,
            "done": True,
        }

    monkeypatch.setattr(engine_fabric, "run_engine_backend_chat", fake_chat)
    result = engine_fabric.run_engine_backend_benchmark(
        "llama-cpp", "tiny-local", "A representative prompt.",
        warmup_runs=1, iterations=3, max_new_tokens=16,
    )
    assert len(calls) == 4
    assert result["configuration"]["measured_requests"] == 3
    assert result["measurements"]["completion_tokens_known"] == 3
    assert result["measurements"]["total_completion_tokens"] == 24
    assert result["measurements"]["latency_ms"]["median"] >= 0
    assert "DO_NOT_RETURN_THIS_MODEL_TEXT" not in str(result)
    assert "A representative prompt." not in str(result)
    assert result["privacy"]["responses_returned"] is False
    assert result["privacy"]["results_persisted"] is False


def test_benchmark_rejects_unbounded_iterations_before_dispatch(monkeypatch):
    monkeypatch.setattr(engine_fabric, "run_engine_backend_chat", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must not run")))
    try:
        engine_fabric.run_engine_backend_benchmark(
            "llama-cpp", "tiny-local", "Prompt", warmup_runs=1, iterations=6,
        )
    except ValueError as exc:
        assert "between 1 and 5" in str(exc)
    else:
        raise AssertionError("benchmark must enforce iteration cap")


def test_auto_router_fails_over_only_between_ready_exact_model_matches(monkeypatch):
    report = {
        "profile": "balanced",
        "backends": [
            {"id": "axiom-native", "name": "AXIOM Native Engine", "status": "ready", "supports_chat": True, "models": ["tiny-local"]},
            {"id": "llama-cpp", "name": "llama.cpp server", "status": "ready", "supports_chat": True, "models": ["tiny-local"]},
            {"id": "ollama", "name": "Ollama", "status": "ready", "supports_chat": True, "models": ["tiny-local"]},
            {"id": "vllm", "name": "vLLM", "status": "ready", "supports_chat": True, "models": ["other-model"]},
        ],
    }
    monkeypatch.setattr(engine_fabric, "discover_engine_backends", lambda profile: report)
    observed = []

    def fake_chat(backend_id, model, messages, **kwargs):
        observed.append((backend_id, model, messages, kwargs))
        if backend_id == "llama-cpp":
            raise engine_fabric.EngineFabricError("simulated local timeout")
        return {
            "schema_version": 1, "backend_id": "ollama", "backend_name": "Ollama",
            "model": model, "response": "local fallback response", "done": True,
            "prompt_eval_count": 3, "eval_count": 5, "total_duration_ms": 18.0,
            "generated_at": "2026-10-24T00:00:00+00:00", "execution": "local_loopback",
            "privacy": {"prompt_returned": False, "response_persisted": False, "cloud_provider_used": False},
        }

    monkeypatch.setattr(engine_fabric, "run_engine_backend_chat", fake_chat)
    result = engine_fabric.run_engine_fabric_chat(
        "balanced", "tiny-local", [{"role": "user", "content": "Hello"}],
        max_new_tokens=64, temperature=0.2,
    )
    assert [item[0] for item in observed] == ["llama-cpp", "ollama"]
    assert all(item[1] == "tiny-local" for item in observed)
    assert observed[0][3]["request_timeout"] == 45.0
    assert result["response"] == "local fallback response"
    assert result["routing"]["fallback_used"] is True
    assert result["routing"]["max_attempts"] == 3
    assert [item["outcome"] for item in result["routing"]["attempts"]] == ["failed", "selected"]
    assert "do not prove identical checkpoint weights" in result["routing"]["scope_note"]


def test_auto_router_rejects_model_ids_not_advertised_by_any_ready_local_service(monkeypatch):
    monkeypatch.setattr(engine_fabric, "discover_engine_backends", lambda profile: {
        "profile": profile,
        "backends": [
            {"id": "ollama", "name": "Ollama", "status": "ready", "supports_chat": True, "models": ["qwen-local"]},
            {"id": "llama-cpp", "name": "llama.cpp", "status": "offline", "supports_chat": True, "models": ["not-ready"]},
        ],
    })
    monkeypatch.setattr(
        engine_fabric, "run_engine_backend_chat",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("should not dispatch")),
    )
    try:
        engine_fabric.run_engine_fabric_chat(
            "balanced", "missing-model", [{"role": "user", "content": "Hello"}],
        )
    except engine_fabric.EngineFabricError as exc:
        assert "exact model ID" in str(exc)
    else:
        raise AssertionError("auto-routing must not guess a model alias")
