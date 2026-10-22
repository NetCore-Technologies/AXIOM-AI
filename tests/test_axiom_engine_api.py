from __future__ import annotations

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



def test_native_model_discovery_lists_local_metadata_without_loading_weights(tmp_path, monkeypatch) -> None:
    root = tmp_path / "models"
    model = root / "tiny-llama"
    model.mkdir(parents=True)
    (model / "config.json").write_text(
        __import__("json").dumps({
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
