from __future__ import annotations

import json
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from axiom.api import engine as engine_api


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(engine_api.router)
    return TestClient(app)


def test_engine_request_accepts_absolute_paths_only_inside_explicit_roots(tmp_path, monkeypatch) -> None:
    root = tmp_path / "models"
    model = root / "tiny-model"
    model.mkdir(parents=True)
    (model / "config.json").write_text('{"model_type":"llama"}', encoding="utf-8")
    monkeypatch.setenv("AXIOM_MODEL_ROOTS", str(root))

    request = engine_api.GenerateRequest(model_path=str(model), prompt="hello")
    assert request.memory_mode == "auto"

    assert request.model_path == str(model.resolve())


def test_engine_request_rejects_absolute_path_outside_configured_roots(tmp_path, monkeypatch) -> None:
    root = tmp_path / "models"
    root.mkdir()
    outside = tmp_path / "private"
    outside.mkdir()
    monkeypatch.setenv("AXIOM_MODEL_ROOTS", str(root))

    with pytest.raises(ValidationError, match="checkpoint directory|trusted model root"):
        engine_api.GenerateRequest(model_path=str(outside), prompt="hello")


def test_engine_request_rejects_symlink_escape(tmp_path, monkeypatch) -> None:
    root = tmp_path / "models"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    escape = root / "escape"
    try:
        escape.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"Directory symlinks are unavailable on this platform: {exc}")
    monkeypatch.setenv("AXIOM_MODEL_ROOTS", str(root))

    with pytest.raises(ValidationError, match="symlink|trusted model root|checkpoint directory"):
        engine_api.GenerateRequest(model_path=str(escape), prompt="hello")


def test_engine_unload_endpoint_calls_lifecycle_handler(monkeypatch) -> None:
    expected = {
        "schema_version": 1,
        "unloaded": True,
        "loaded": False,
        "scope_note": "Model unloaded for test.",
    }
    monkeypatch.setattr(engine_api, "unload_local_model", lambda: expected)

    response = _client().post("/api/engine/unload")

    assert response.status_code == 200
    assert response.json() == expected



def test_native_stream_api_emits_ndjson_token_and_completion_events(monkeypatch) -> None:
    monkeypatch.setattr(engine_api, "resolve_local_model_directory", lambda value, label: value)

    observed: dict[str, object] = {}

    def fake_stream(
        model_path, prompt, *, adapter_path=None, max_new_tokens=256, temperature=0.7,
        top_p=0.9, top_k=0, repetition_penalty=1.0, seed=None, stop_sequences=(), include_token_events=True,
        cancel_event=None, device_preference="auto", memory_mode="full",
    ):
        observed.update({
            "model_path": model_path, "prompt": prompt, "max_new_tokens": max_new_tokens,
            "temperature": temperature, "top_p": top_p, "top_k": top_k,
            "repetition_penalty": repetition_penalty, "seed": seed,
            "stop_sequences": list(stop_sequences),
            "include_token_events": include_token_events,
            "device_preference": device_preference,
            "memory_mode": memory_mode,
        })
        yield {"type": "token", "response": "hi", "completion_tokens": 1}
        yield {
            "type": "complete",
            "result": {
                "engine": "axiom-native-engine",
                "execution_backend": "pytorch-native-axiom",
                "response": "hi",
                "completion_tokens": 1,
                "local_only": True,
            },
        }

    monkeypatch.setattr(engine_api, "generate_local_stream", fake_stream)
    response = _client().post(
        "/api/engine/generate/stream",
        json={
            "model_path": "/trusted/models/tiny",
            "prompt": "hello",
            "max_new_tokens": 3,
            "temperature": 0,
            "top_p": 0.8,
            "top_k": 4,
            "repetition_penalty": 1.1,
            "seed": 42,
            "stop_sequences": ["<END>", "###"],
            "device": "cpu",
            "memory_mode": "layer_streaming",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")
    events = [json.loads(line) for line in response.text.splitlines() if line]
    assert events[0] == {"type": "token", "response": "hi", "completion_tokens": 1}
    assert events[1]["type"] == "complete"
    assert events[1]["result"]["execution_backend"] == "pytorch-native-axiom"
    assert observed == {
        "model_path": "/trusted/models/tiny",
        "prompt": "hello",
        "max_new_tokens": 3,
        "temperature": 0,
        "top_p": 0.8,
        "top_k": 4,
        "repetition_penalty": 1.1,
        "seed": 42,
        "stop_sequences": ["<END>", "###"],
        "include_token_events": True,
        "device_preference": "cpu",
        "memory_mode": "layer_streaming",
    }


def test_generate_request_rejects_invalid_stop_sequence_lists(monkeypatch) -> None:
    from pydantic import ValidationError
    from axiom.api import engine as engine_module
    from axiom.api.engine import GenerateRequest

    monkeypatch.setattr(engine_module, "resolve_local_model_directory", lambda value, label: value)
    base = {"model_path": "/trusted/models/tiny", "prompt": "hello"}
    with pytest.raises(ValidationError, match="device"):
        engine_api.GenerateRequest(**base, device="network")
    assert engine_api.GenerateRequest(**base, memory_mode="disk_streaming").memory_mode == "disk_streaming"
    with pytest.raises(ValidationError, match="memory_mode"):
        engine_api.GenerateRequest(**base, memory_mode="automatic")
    with pytest.raises(ValidationError, match="stop sequences|Stop sequences"):
        GenerateRequest(**base, stop_sequences=[" "])
    with pytest.raises(ValidationError, match="stop sequence|Stop sequence"):
        GenerateRequest(**base, stop_sequences=["x" * 257])
    with pytest.raises(ValidationError):
        GenerateRequest(**base, stop_sequences=["END"] * 17)


def test_adapter_compatibility_api_returns_per_device_report(monkeypatch) -> None:
    monkeypatch.setattr(engine_api, "resolve_local_model_directory", lambda value, label: value)
    expected = {
        "schema_version": 1,
        "base_model": {"name": "base", "model_type": "llama", "architecture": "LlamaForCausalLM"},
        "adapter": {"name": "lora", "rank": 8, "alpha": 16.0, "target_modules": ["q_proj", "v_proj"]},
        "structurally_compatible": True,
        "compatible_on_any_device": True,
        "adapter_tensor_count": 4,
        "checked_layers": 12,
        "devices": [{"name": "CPU", "available": True, "compatible": True, "status": "compatible", "reason": "Preflight passed."}],
        "issues": [],
        "scope_note": "Metadata only.",
    }
    monkeypatch.setattr(engine_api, "check_local_adapter_compatibility", lambda model_path, adapter_path: expected)
    response = _client().post("/api/engine/adapters/compatibility", json={
        "model_path": "/trusted/models/base",
        "adapter_path": "/trusted/models/lora",
    })

    assert response.status_code == 200
    assert response.json() == expected


def test_quantization_estimator_compares_formats_against_memory_budgets(tmp_path, monkeypatch) -> None:
    root = tmp_path / "models"
    model = root / "tiny-llama"
    model.mkdir(parents=True)
    (model / "config.json").write_text(json.dumps({
        "model_type": "llama",
        "architectures": ["LlamaForCausalLM"],
        "hidden_size": 8,
        "intermediate_size": 12,
        "num_hidden_layers": 1,
        "num_attention_heads": 2,
        "num_key_value_heads": 1,
        "vocab_size": 8,
        "max_position_embeddings": 32,
        "rms_norm_eps": 1e-6,
        "rope_theta": 10000.0,
        "bos_token_id": 1,
        "tie_word_embeddings": False,
    }), encoding="utf-8")
    monkeypatch.setenv("AXIOM_MODEL_ROOTS", str(root))

    response = _client().post("/api/engine/quantization/estimate", json={
        "model_path": str(model),
        "context_length": 16,
        "batch_size": 1,
        "ram_budget_gib": 8,
        "vram_budget_gib": 4,
    })

    assert response.status_code == 200, response.text
    report = response.json()
    assert report["schema_version"] == 1
    assert report["model"]["name"] == "tiny-llama"
    assert report["request"]["context_length"] == 16
    candidates = {item["format"]: item for item in report["candidates"]}
    assert set(candidates) == {"int4", "int8", "bf16", "fp16", "fp32"}
    assert candidates["int4"]["estimated_total_gib"] > 0
    assert candidates["int4"]["estimated_total_gib"] < candidates["int8"]["estimated_total_gib"]
    assert candidates["int8"]["estimated_total_gib"] < candidates["fp16"]["estimated_total_gib"]
    assert report["recommendation"]["format"] == "bf16"
    assert report["recommendation"]["status"] == "fits_budget"
    assert candidates["int8"]["estimated_total_gib"] < candidates["fp16"]["estimated_total_gib"]
    assert candidates["fp16"]["estimated_total_gib"] < candidates["fp32"]["estimated_total_gib"]
    assert candidates["int4"]["native_checkpoint_supported"] is False
    assert candidates["int8"]["native_checkpoint_supported"] is False
    assert candidates["fp16"]["native_checkpoint_supported"] is True
    assert candidates["fp32"]["native_checkpoint_supported"] is True
    assert candidates["int4"]["fits_ram_budget"] is True
    assert candidates["fp32"]["fits_vram_budget"] is True
    assert report["assumptions"]["safety_margin_percent"] == 20
    assert report["assumptions"]["uncertainty_range_percent"] == {"low": -15, "high": 25}
    assert "not predict model quality/speed" in report["scope_note"]
    assert "not inspect tensor contents" in report["scope_note"]


def test_quantization_estimator_reports_no_native_fit_for_small_budget(tmp_path, monkeypatch) -> None:
    root = tmp_path / "models"
    model = root / "large-llama"
    model.mkdir(parents=True)
    (model / "config.json").write_text(json.dumps({
        "model_type": "llama",
        "architectures": ["LlamaForCausalLM"],
        "hidden_size": 8192,
        "intermediate_size": 22016,
        "num_hidden_layers": 80,
        "num_attention_heads": 64,
        "num_key_value_heads": 8,
        "vocab_size": 128000,
        "max_position_embeddings": 8192,
        "rms_norm_eps": 1e-6,
        "rope_theta": 10000.0,
        "tie_word_embeddings": False,
    }), encoding="utf-8")
    monkeypatch.setenv("AXIOM_MODEL_ROOTS", str(root))

    response = _client().post("/api/engine/quantization/estimate", json={
        "model_path": str(model),
        "context_length": 4096,
        "batch_size": 1,
        "ram_budget_gib": 0.1,
        "vram_budget_gib": 0.1,
    })

    assert response.status_code == 200, response.text
    report = response.json()
    assert report["recommendation"]["format"] is None
    assert report["recommendation"]["status"] == "no_native_candidate_fits"
    assert "No currently native-supported precision" in report["recommendation"]["note"]


def test_quantization_estimator_rejects_context_above_model_limit(tmp_path, monkeypatch) -> None:
    root = tmp_path / "models"
    model = root / "tiny-llama"
    model.mkdir(parents=True)
    (model / "config.json").write_text(json.dumps({
        "model_type": "llama",
        "architectures": ["LlamaForCausalLM"],
        "hidden_size": 8,
        "intermediate_size": 12,
        "num_hidden_layers": 1,
        "num_attention_heads": 2,
        "num_key_value_heads": 1,
        "vocab_size": 8,
        "max_position_embeddings": 32,
        "rms_norm_eps": 1e-6,
        "rope_theta": 10000.0,
        "bos_token_id": 1,
        "tie_word_embeddings": False,
    }), encoding="utf-8")
    monkeypatch.setenv("AXIOM_MODEL_ROOTS", str(root))

    response = _client().post("/api/engine/quantization/estimate", json={
        "model_path": str(model),
        "context_length": 33,
        "batch_size": 1,
        "ram_budget_gib": 8,
    })

    assert response.status_code == 422
    assert "exceeds this checkpoint's limit" in response.json()["detail"]


def test_quantization_estimator_requires_at_least_one_budget(tmp_path, monkeypatch) -> None:
    root = tmp_path / "models"
    model = root / "tiny-llama"
    model.mkdir(parents=True)
    (model / "config.json").write_text(json.dumps({
        "model_type": "llama",
        "architectures": ["LlamaForCausalLM"],
        "hidden_size": 8,
        "intermediate_size": 12,
        "num_hidden_layers": 1,
        "num_attention_heads": 2,
        "num_key_value_heads": 1,
        "vocab_size": 8,
        "max_position_embeddings": 32,
        "rms_norm_eps": 1e-6,
        "rope_theta": 10000.0,
        "bos_token_id": 1,
        "tie_word_embeddings": False,
    }), encoding="utf-8")
    monkeypatch.setenv("AXIOM_MODEL_ROOTS", str(root))

    response = _client().post("/api/engine/quantization/estimate", json={
        "model_path": str(model), "context_length": 16, "batch_size": 1,
    })

    assert response.status_code == 422
    assert "Provide a RAM and/or VRAM budget" in response.text


def test_native_model_discovery_lists_local_metadata_without_loading_weights(tmp_path, monkeypatch) -> None:
    root = tmp_path / "models"
    model = root / "tiny-llama"
    model.mkdir(parents=True)
    (model / "config.json").write_text(
        json.dumps({
            "model_type": "llama",
            "architectures": ["LlamaForCausalLM"],
            "hidden_size": 8,
            "intermediate_size": 12,
            "num_hidden_layers": 1,
            "num_attention_heads": 2,
            "num_key_value_heads": 1,
            "vocab_size": 8,
            "max_position_embeddings": 32,
            "rms_norm_eps": 1e-6,
            "rope_theta": 10000.0,
            "bos_token_id": 1,
            "tie_word_embeddings": False,
        }),
        encoding="utf-8",
    )
    (model / "tokenizer.json").write_text("{}", encoding="utf-8")
    (model / "model.safetensors").write_bytes(b"metadata discovery does not load tensor data")
    adapter = root / "tiny-lora"
    adapter.mkdir()
    (adapter / "adapter_config.json").write_text('{"task_type":"CAUSAL_LM"}', encoding="utf-8")
    (adapter / "adapter_model.safetensors").write_bytes(b"deferred until load")
    monkeypatch.setenv("AXIOM_MODEL_ROOTS", str(root))

    response = _client().get("/api/engine/models")

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == 1
    assert payload["models"] == [{
        "path": str(model.resolve()),
        "name": "tiny-llama",
        "model_type": "llama",
        "architecture": "LlamaForCausalLM",
        "weight_format": "safetensors",
        "ready_for_native_attempt": True,
    }]
    assert payload["adapters"] == [{
        "path": str(adapter.resolve()),
        "name": "tiny-lora",
        "weight_format": "safetensors LoRA",
    }]
    assert "not loaded or fully validated" in payload["scope_note"]



def test_engine_request_rejects_adapter_directory_as_base_model(tmp_path, monkeypatch) -> None:
    root = tmp_path / "models"
    adapter = root / "adapter"
    adapter.mkdir(parents=True)
    (adapter / "adapter_config.json").write_text('{"task_type":"CAUSAL_LM"}', encoding="utf-8")
    monkeypatch.setenv("AXIOM_MODEL_ROOTS", str(root))

    with pytest.raises(ValidationError, match="checkpoint directory|trusted model root"):
        engine_api.GenerateRequest(model_path=str(adapter), prompt="hello")


def test_engine_request_rejects_base_model_directory_as_adapter(tmp_path, monkeypatch) -> None:
    root = tmp_path / "models"
    model = root / "base-model"
    model.mkdir(parents=True)
    (model / "config.json").write_text('{"model_type":"llama"}', encoding="utf-8")
    monkeypatch.setenv("AXIOM_MODEL_ROOTS", str(root))

    with pytest.raises(ValidationError, match="checkpoint directory|trusted model root"):
        engine_api.GenerateRequest(model_path=str(model), adapter_path=str(model), prompt="hello")


def test_engine_stream_endpoint_yields_token_snapshots_and_final_metrics(tmp_path, monkeypatch) -> None:
    root = tmp_path / "models"
    model = root / "tiny-model"
    model.mkdir(parents=True)
    (model / "config.json").write_text('{"model_type":"llama"}', encoding="utf-8")
    monkeypatch.setenv("AXIOM_MODEL_ROOTS", str(root))
    completed = {
        "engine": "axiom-native-engine",
        "execution_backend": "pytorch-native-axiom",
        "transformers_generation_used": False,
        "ollama_used": False,
        "model": "tiny-model",
        "architecture": "LlamaForCausalLM",
        "model_type": "llama",
        "adapter": None,
        "device": "cpu",
        "checkpoint_format": "safetensors",
        "decoder": "axiom-autoregressive-kv-cache",
        "attention_backend": "pytorch-scaled-dot-product-attention",
        "sampling": {
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 0,
            "repetition_penalty": 1.0,
            "seed": None,
        },
        "prefill_ms": 4.2,
        "decode_ms": 5.3,
        "time_to_first_token_ms": 4.2,
        "generation_tokens_per_second": 188.679,
        "response": "Hello",
        "prompt_tokens": 1,
        "completion_tokens": 1,
        "elapsed_ms": 12.5,
        "generated_at": "2026-10-22T00:00:00+00:00",
        "local_only": True,
    }
    monkeypatch.setattr(engine_api, "generate_local_stream", lambda *_args, **_kwargs: iter([
        {"type": "token", "response": "Hel", "completion_tokens": 1},
        {"type": "complete", "result": completed},
    ]))

    response = _client().post("/api/engine/generate/stream", json={
        "model_path": str(model), "prompt": "hello", "max_new_tokens": 2, "temperature": 0,
    })

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")
    events = [json.loads(line) for line in response.text.splitlines()]
    assert events[0] == {"type": "token", "response": "Hel", "completion_tokens": 1}
    assert events[1] == {"type": "complete", "result": completed}
    assert events[1]["result"]["sampling"] == {
        "temperature": 0.7,
        "top_p": 0.9,
        "top_k": 0,
        "repetition_penalty": 1.0,
        "seed": None,
    }
