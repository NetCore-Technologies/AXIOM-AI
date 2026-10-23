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
        "--stream", "--max-new-tokens", "4", "--temperature", "0",
        "--stop-sequence", "<END>", "--stop-sequence", "###",
    ])

    assert result.exit_code == 0, result.output
    assert "AXIOM ENGINE" in result.output
    assert "Hello from the native stream." in result.output
    assert "Generated tokens: 4" in result.output
    assert "Finish reason: stop_sequence" in result.output
    assert observed["stop_sequences"] == ["<END>", "###"]


def test_engine_run_rejects_stream_with_json_mode(tmp_path: Path) -> None:
    model_path = tmp_path / "model"
    model_path.mkdir()
    result = runner.invoke(engine_app, [
        "run", "--model-path", str(model_path), "--prompt", "Say hello.",
        "--stream", "--json",
    ])
    assert result.exit_code == 1
    assert "cannot be combined with --json" in result.output
