from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

import axiom.cli.engine as engine_cli

engine_app = engine_cli.engine_app


runner = CliRunner()


def test_engine_discover_json_lists_local_model_and_adapter_metadata(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "trusted-models"
    model = root / "tiny-llama"
    model.mkdir(parents=True)
    config = {
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
    }
    (model / "config.json").write_text(json.dumps(config), encoding="utf-8")
    (model / "tokenizer.json").write_text("{}", encoding="utf-8")
    (model / "model.safetensors").write_bytes(b"deferred until inference")
    adapter = root / "tiny-lora"
    adapter.mkdir()
    (adapter / "adapter_config.json").write_text('{"task_type":"CAUSAL_LM"}', encoding="utf-8")
    (adapter / "adapter_model.safetensors").write_bytes(b"deferred until inference")
    monkeypatch.setenv("AXIOM_MODEL_ROOTS", str(root))

    result = runner.invoke(engine_app, ["discover", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema_version"] == 1
    assert [item["name"] for item in payload["models"]] == ["tiny-llama"]
    assert [item["name"] for item in payload["adapters"]] == ["tiny-lora"]
    assert payload["models"][0]["path"] == str(model.resolve())
    assert payload["adapters"][0]["path"] == str(adapter.resolve())
    assert "not loaded or fully validated" in payload["scope_note"]


def test_engine_telemetry_json_is_machine_readable_and_path_private(monkeypatch) -> None:
    monkeypatch.setattr(engine_cli, "runtime_telemetry", lambda: {
        "schema_version": 1,
        "sampled_at": "2026-10-24T04:00:00+00:00",
        "sample_type": "point_in_time",
        "cpu": {"logical_cores": 8, "system_percent": None, "process_percent": None},
        "memory": {"total_bytes": None, "available_bytes": None, "used_bytes": None, "percent": None},
        "process": {"pid": 1, "rss_bytes": None, "threads": None},
        "devices": [],
        "loaded_runtime": {"loaded": False},
        "disks": [{"label": "trusted_model_root_1", "total_bytes": 1000, "free_bytes": 500, "used_bytes": 500}],
        "privacy_scope": {"model_paths_included": False},
        "scope_note": "Paths omitted.",
    })
    result = runner.invoke(engine_app, ["telemetry", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["sample_type"] == "point_in_time"
    assert payload["disks"][0]["label"] == "trusted_model_root_1"
    serialized = json.dumps(payload).lower()
    assert "/home/" not in serialized
    assert "/tmp/" not in serialized
    assert payload["privacy_scope"]["model_paths_included"] is False


def test_engine_discover_json_returns_empty_inventory_cleanly(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "trusted-models"
    root.mkdir()
    monkeypatch.setenv("AXIOM_MODEL_ROOTS", str(root))

    result = runner.invoke(engine_app, ["discover", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["models"] == []
    assert payload["adapters"] == []
    assert payload["truncated"] is False



def test_engine_run_stream_shows_live_output_and_final_metrics(tmp_path: Path, monkeypatch) -> None:
    model_path = tmp_path / "model"
    model_path.mkdir()
    final_result = {
        "model": "fixture-model",
        "architecture": "LlamaForCausalLM",
        "response": "Hello from the native stream.",
        "completion_tokens": 4,
        "elapsed_ms": 21.5,
        "stop_sequences": ["<END>", "###"],
        "stop_reason": "stop_sequence",
    }
    observed: dict[str, object] = {}

    def fake_stream(*_args, **kwargs):
        observed.update(kwargs)
        yield {"type": "token", "response": "Hel", "completion_tokens": 2}
        yield {"type": "token", "response": "Hello from the native stream.", "completion_tokens": 4}
        yield {"type": "complete", "result": final_result}

    monkeypatch.setattr(engine_cli, "generate_local_stream", fake_stream)
    result = runner.invoke(engine_app, [
        "run", "--model-path", str(model_path), "--prompt", "Say hello.",
        "--stream", "--max-new-tokens", "4", "--temperature", "0", "--precision", "fp16",
        "--stop-sequence", "<END>", "--stop-sequence", "###",
    ])

    assert result.exit_code == 0, result.output
    assert "AXIOM ENGINE" in result.output
    assert "Hello from the native stream." in result.output
    assert "Generated tokens: 4" in result.output
    assert "Finish reason: stop_sequence" in result.output
    assert observed["stop_sequences"] == ["<END>", "###"]
    assert observed["memory_mode"] == "auto"
    assert observed["precision"] == "fp16"


def test_engine_run_rejects_stream_with_json_mode(tmp_path: Path) -> None:
    model_path = tmp_path / "model"
    model_path.mkdir()
    result = runner.invoke(engine_app, [
        "run", "--model-path", str(model_path), "--prompt", "Say hello.",
        "--stream", "--json",
    ])
    assert result.exit_code == 1
    assert "cannot be combined with --json" in result.output



def test_engine_run_passes_explicit_device_to_native_stream(tmp_path: Path, monkeypatch) -> None:
    model_path = tmp_path / "model"
    model_path.mkdir()
    observed: dict[str, object] = {}

    def fake_stream(*_args, **kwargs):
        observed.update(kwargs)
        yield {"type": "complete", "result": {
            "model": "fixture-model",
            "architecture": "LlamaForCausalLM",
            "response": "CPU-selected response",
            "completion_tokens": 3,
            "elapsed_ms": 12.5,
            "stop_reason": "max_new_tokens",
        }}

    monkeypatch.setattr(engine_cli, "generate_local_stream", fake_stream)
    result = runner.invoke(engine_app, [
        "run", "--model-path", str(model_path), "--prompt", "Say hello.",
        "--stream", "--device", "cpu", "--memory-mode", "layer_streaming",
    ])

    assert result.exit_code == 0, result.output
    assert observed["device_preference"] == "cpu"
    assert observed["memory_mode"] == "layer_streaming"
    assert "Memory mode: layer_streaming" in result.output
    assert "CPU-selected response" in result.output


def test_engine_pull_downloads_native_model_for_axiom_runtime(monkeypatch, tmp_path: Path) -> None:
    observed: dict[str, object] = {}

    def fake_pull(repo_id, *, on_log=None, on_progress=None):
        observed["repo_id"] = repo_id
        observed["on_log"] = on_log
        observed["on_progress"] = on_progress
        if on_log:
            on_log("validated native checkpoint")
        if on_progress:
            on_progress(128, 256)
        return {
            "operation": "pull_native",
            "repo_id": repo_id,
            "model_type": "qwen2",
            "path": str(tmp_path / "qwen"),
            "runtime": "axiom-native",
        }

    monkeypatch.setattr(engine_cli.model_studio, "pull_native_model", fake_pull)
    result = runner.invoke(engine_app, ["pull", "Qwen/Qwen2.5-0.5B-Instruct", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["operation"] == "pull_native"
    assert payload["model_type"] == "qwen2"
    assert observed["repo_id"] == "Qwen/Qwen2.5-0.5B-Instruct"
    assert observed["on_log"] is None
    assert observed["on_progress"] is None


def test_engine_pull_reports_unsupported_model_cleanly(monkeypatch) -> None:
    from axiom.core.model_studio import ModelStudioError

    monkeypatch.setattr(
        engine_cli.model_studio,
        "pull_native_model",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ModelStudioError("unsupported architecture")),
    )
    result = runner.invoke(engine_app, ["pull", "example/unsupported"])
    assert result.exit_code == 1
    assert "unsupported architecture" in result.output


def test_engine_backends_cli_json_shows_profile_recommendation(monkeypatch) -> None:
    monkeypatch.setattr(engine_cli, "discover_engine_backends", lambda profile: {
        "profile": profile,
        "backends": [{"id": "llama-cpp", "name": "llama.cpp server", "status": "ready", "model_count": 1, "best_for": ["low_memory"]}],
        "recommendation": {"name": "llama.cpp server", "status": "ready", "reason": "Quantized local inference."},
        "scope_note": "Loopback only.",
    })
    result = runner.invoke(engine_app, ["backends", "--profile", "low-memory", "--json"])
    assert result.exit_code == 0, result.output
    assert '"profile": "low-memory"' in result.output
    assert '"backend_id"' in result.output or '"llama-cpp"' in result.output


def test_engine_route_chat_cli_uses_selected_local_backend(monkeypatch) -> None:
    monkeypatch.setattr(engine_cli, "run_engine_backend_chat", lambda backend, model, messages, **kwargs: {
        "backend_name": "llama.cpp server", "model": model, "response": "local response",
        "eval_count": 3, "total_duration_ms": 7,
    })
    result = runner.invoke(engine_app, [
        "route-chat", "--backend", "llama-cpp", "--model", "tiny-local", "--prompt", "Hello",
    ])
    assert result.exit_code == 0, result.output
    assert "local response" in result.output
    assert "llama.cpp server" in result.output


def test_engine_route_benchmark_cli_outputs_measurements_without_response_text(monkeypatch) -> None:
    monkeypatch.setattr(engine_cli, "run_engine_backend_benchmark", lambda backend, model, prompt, **kwargs: {
        "backend_name": "llama.cpp server", "model": model,
        "configuration": {"measured_requests": 2},
        "measurements": {"latency_ms": {"median": 15.0, "p95": 19.0}, "wall_time_ms": 30.0, "completion_tokens_per_second": 42.0},
        "scope_note": "Session-only timings.",
    })
    result = runner.invoke(engine_app, [
        "route-benchmark", "--backend", "llama-cpp", "--model", "tiny-local",
        "--prompt", "Representative benchmark input.", "--iterations", "2", "--json",
    ])
    assert result.exit_code == 0, result.output
    assert '"median": 15.0' in result.output
    assert "Representative benchmark input." not in result.output
