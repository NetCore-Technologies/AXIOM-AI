from __future__ import annotations

import json
from pathlib import Path

import pytest

from axiom.core.native_engine import NativeEngineError, NativeLlamaConfig, _resolve_safetensor_files


def _config(**overrides):
    value = {
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
    value.update(overrides)
    return value


def test_native_config_accepts_standard_llama_and_mistral() -> None:
    assert NativeLlamaConfig.from_mapping(_config()).model_type == "llama"
    assert NativeLlamaConfig.from_mapping(
        _config(model_type="mistral", architectures=["MistralForCausalLM"], sliding_window=16)
    ).sliding_window == 16


@pytest.mark.parametrize(
    "overrides,detail",
    [
        ({"model_type": "qwen2"}, "supports llama and mistral"),
        ({"hidden_size": 7}, "even-sized attention heads"),
        ({"rope_scaling": {"rope_type": "yarn", "factor": 2.0}}, "RoPE scaling"),
        ({"num_attention_heads": 3, "hidden_size": 12, "num_key_value_heads": 2}, "num_key_value_heads"),
    ],
)
def test_native_config_rejects_unsupported_or_inconsistent_architecture(overrides, detail) -> None:
    with pytest.raises(NativeEngineError, match=detail):
        NativeLlamaConfig.from_mapping(_config(**overrides))


def test_safetensor_index_rejects_relative_path_traversal(tmp_path: Path) -> None:
    (tmp_path / "model.safetensors.index.json").write_text(
        json.dumps({"weight_map": {"model.embed_tokens.weight": "../outside.safetensors"}}),
        encoding="utf-8",
    )
    with pytest.raises(NativeEngineError, match="unsafe or unsupported shard path"):
        _resolve_safetensor_files(tmp_path)


def test_native_asset_symlink_must_resolve_inside_trusted_roots(tmp_path: Path) -> None:
    from axiom.core.native_engine import _resolve_trusted_file

    trusted = tmp_path / "trusted"
    blobs = trusted / "blobs"
    checkpoint = trusted / "snapshot"
    outside = tmp_path / "outside"
    blobs.mkdir(parents=True)
    checkpoint.mkdir()
    outside.mkdir()
    safe_blob = blobs / "config.json"
    safe_blob.write_text('{"model_type":"llama"}', encoding="utf-8")
    safe_link = checkpoint / "config.json"
    try:
        safe_link.symlink_to(safe_blob)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"File symlinks are unavailable on this platform: {exc}")
    assert _resolve_trusted_file(safe_link, (trusted.resolve(),), "Model config") == safe_blob.resolve()

    external = outside / "config.json"
    external.write_text('{"model_type":"llama"}', encoding="utf-8")
    unsafe_link = checkpoint / "external-config.json"
    unsafe_link.symlink_to(external)
    with pytest.raises(NativeEngineError, match="outside the configured trusted model roots"):
        _resolve_trusted_file(unsafe_link, (trusted.resolve(),), "Model config")


def _tiny_weights(torch, vocab_size=8, hidden=8, intermediate=12):
    weights = {
        "model.embed_tokens.weight": torch.randn(vocab_size, hidden) * 0.02,
        "model.norm.weight": torch.ones(hidden),
        "lm_head.weight": torch.randn(vocab_size, hidden) * 0.02,
        "model.layers.0.input_layernorm.weight": torch.ones(hidden),
        "model.layers.0.post_attention_layernorm.weight": torch.ones(hidden),
    }
    dimensions = {
        "self_attn.q_proj": (hidden, hidden),
        "self_attn.k_proj": (hidden // 2, hidden),
        "self_attn.v_proj": (hidden // 2, hidden),
        "self_attn.o_proj": (hidden, hidden),
        "mlp.gate_proj": (intermediate, hidden),
        "mlp.up_proj": (intermediate, hidden),
        "mlp.down_proj": (hidden, intermediate),
    }
    for name, shape in dimensions.items():
        weights["model.layers.0." + name + ".weight"] = torch.randn(*shape) * 0.02
    return weights


def test_native_forward_and_incremental_kv_cache_run_without_transformers() -> None:
    torch = pytest.importorskip("torch")
    from axiom.core.native_engine import NativeLlamaRuntime

    config = NativeLlamaConfig.from_mapping(_config())
    runtime = NativeLlamaRuntime(config, _tiny_weights(torch), torch, torch.device("cpu"))
    with torch.inference_mode():
        logits, cache = runtime.forward(torch.tensor([[1, 3, 4]], dtype=torch.long))
        assert tuple(logits.shape) == (1, config.vocab_size)
        assert len(cache) == config.num_hidden_layers
        assert tuple(cache[0][0].shape) == (1, config.num_key_value_heads, 3, 4)
        next_logits, next_cache = runtime.forward(torch.tensor([[5]], dtype=torch.long), cache)
        full_logits, full_cache = runtime.forward(torch.tensor([[1, 3, 4, 5]], dtype=torch.long))
    assert tuple(next_logits.shape) == (1, config.vocab_size)
    assert tuple(next_cache[0][0].shape) == (1, config.num_key_value_heads, 4, 4)
    assert torch.allclose(next_logits, full_logits, atol=1e-5, rtol=1e-4)
    assert tuple(full_cache[0][0].shape) == (1, config.num_key_value_heads, 4, 4)


def test_native_decoder_stops_before_emitting_eos_and_does_not_step_past_output_limit() -> None:
    torch = pytest.importorskip("torch")
    from axiom.core.native_engine import NativeLlamaRuntime

    config = NativeLlamaConfig.from_mapping(_config(max_position_embeddings=2))
    runtime = NativeLlamaRuntime(config, _tiny_weights(torch), torch, torch.device("cpu"))
    with torch.inference_mode():
        initial_logits, _ = runtime.forward(torch.tensor([[1]], dtype=torch.long))
        eos_id = int(torch.argmax(initial_logits, dim=-1).item())
        assert runtime.generate([1], max_new_tokens=1, temperature=0, eos_token_ids=(eos_id,)) == []
        # With no EOS override, the final token can fill the last context slot;
        # the decoder must not run an extra, out-of-window forward pass.
        output = runtime.generate([1], max_new_tokens=1, temperature=0, eos_token_ids=())
    assert len(output) == 1
    assert runtime.last_generation["completion_tokens"] == 1


def test_native_iterator_honors_cancellation_before_prompt_prefill(monkeypatch) -> None:
    from threading import Event

    torch = pytest.importorskip("torch")
    from axiom.core.native_engine import NativeLlamaRuntime

    config = NativeLlamaConfig.from_mapping(_config())
    runtime = NativeLlamaRuntime(config, _tiny_weights(torch), torch, torch.device("cpu"))
    cancel_event = Event()
    cancel_event.set()

    def unexpected_forward(input_ids, past_key_values=None, *, cancel_event=None):
        pytest.fail("A pre-cancelled request must not start model forward execution.")

    monkeypatch.setattr(runtime, "forward", unexpected_forward)
    assert list(runtime.iter_generate(
        [1, 3], max_new_tokens=4, temperature=0, eos_token_ids=(), cancel_event=cancel_event
    )) == []
    assert runtime.last_generation["completion_tokens"] == 0


def test_native_iterator_stops_before_next_token_forward_when_cancelled(monkeypatch) -> None:
    from threading import Event

    torch = pytest.importorskip("torch")
    from axiom.core.native_engine import NativeLlamaRuntime

    config = NativeLlamaConfig.from_mapping(_config())
    runtime = NativeLlamaRuntime(config, _tiny_weights(torch), torch, torch.device("cpu"))
    cancel_event = Event()
    original_forward = runtime.forward
    forward_calls = 0

    def counted_forward(input_ids, past_key_values=None, *, cancel_event=None):
        nonlocal forward_calls
        forward_calls += 1
        return original_forward(input_ids, past_key_values, cancel_event=cancel_event)

    monkeypatch.setattr(runtime, "forward", counted_forward)
    iterator = runtime.iter_generate(
        [1, 3], max_new_tokens=4, temperature=0, eos_token_ids=(), cancel_event=cancel_event
    )
    first_token = next(iterator)
    assert 0 <= first_token < config.vocab_size
    assert forward_calls == 1
    cancel_event.set()
    with pytest.raises(StopIteration):
        next(iterator)
    assert forward_calls == 1
    assert runtime.last_generation["completion_tokens"] == 1


def _tiny_adapter_file(safetensors_torch, torch, root: Path, *, bad_a_shape: bool = False) -> Path:
    adapter = root / "tiny-lora"
    adapter.mkdir()
    (adapter / "adapter_config.json").write_text(json.dumps({
        "task_type": "CAUSAL_LM", "bias": "none", "r": 1,
        "lora_alpha": 2, "target_modules": ["q_proj"],
    }), encoding="utf-8")
    a_shape = (1, 7) if bad_a_shape else (1, 8)
    safetensors_torch.save_file({
        "base_model.model.model.layers.0.self_attn.q_proj.lora_A.weight": torch.ones(a_shape),
        "base_model.model.model.layers.0.self_attn.q_proj.lora_B.weight": torch.ones((8, 1)),
    }, str(adapter / "adapter_model.safetensors"))
    return adapter


def test_native_adapter_compatibility_checks_tensor_shapes_and_device_presence(tmp_path: Path) -> None:
    torch = pytest.importorskip("torch")
    safetensors_torch = pytest.importorskip("safetensors.torch")
    from axiom.core.native_engine import inspect_native_adapter_compatibility

    root = tmp_path / "trusted"
    model = root / "base"
    model.mkdir(parents=True)
    (model / "config.json").write_text(json.dumps(_config()), encoding="utf-8")
    (model / "tokenizer.json").write_text("{}", encoding="utf-8")
    safetensors_torch.save_file(_tiny_weights(torch), str(model / "model.safetensors"))
    adapter = _tiny_adapter_file(safetensors_torch, torch, root)

    report = inspect_native_adapter_compatibility(model, adapter, trusted_roots=(root.resolve(),))

    assert report["schema_version"] == 1
    assert report["structurally_compatible"] is True
    assert report["issues"] == []
    assert report["adapter"]["rank"] == 1
    assert report["adapter"]["target_modules"] == ["q_proj"]
    assert report["adapter_tensor_count"] == 2
    assert {device["name"] for device in report["devices"]} == {"CPU", "CUDA", "ROCm", "Metal/MPS"}
    cpu = next(device for device in report["devices"] if device["name"] == "CPU")
    assert cpu["available"] is True
    assert cpu["compatible"] is True


def test_native_adapter_compatibility_rejects_projection_shape_mismatch(tmp_path: Path) -> None:
    torch = pytest.importorskip("torch")
    safetensors_torch = pytest.importorskip("safetensors.torch")
    from axiom.core.native_engine import inspect_native_adapter_compatibility

    root = tmp_path / "trusted"
    model = root / "base"
    model.mkdir(parents=True)
    (model / "config.json").write_text(json.dumps(_config()), encoding="utf-8")
    (model / "tokenizer.json").write_text("{}", encoding="utf-8")
    safetensors_torch.save_file(_tiny_weights(torch), str(model / "model.safetensors"))
    adapter = _tiny_adapter_file(safetensors_torch, torch, root, bad_a_shape=True)

    report = inspect_native_adapter_compatibility(model, adapter, trusted_roots=(root.resolve(),))

    assert report["structurally_compatible"] is False
    assert any("LoRA A tensor shape" in issue for issue in report["issues"])
    assert next(device for device in report["devices"] if device["name"] == "CPU")["compatible"] is False


def test_native_adapter_delta_is_applied_in_axiom_linear_path() -> None:
    torch = pytest.importorskip("torch")
    from axiom.core.native_engine import NativeLlamaRuntime

    config = NativeLlamaConfig.from_mapping(_config())
    weights = _tiny_weights(torch)
    module = "model.layers.0.self_attn.q_proj"
    a = torch.ones((1, 8), dtype=torch.float32)
    b = torch.ones((8, 1), dtype=torch.float32)
    runtime = NativeLlamaRuntime(
        config,
        weights,
        torch,
        torch.device("cpu"),
        adapter={module: {"A": a, "B": b}},
        adapter_scaling={module: 2.0},
    )
    sample = torch.ones((1, 1, 8), dtype=torch.float32)
    actual = runtime._linear(sample, module)
    base = torch.nn.functional.linear(sample, weights[module + ".weight"])
    expected = base + torch.nn.functional.linear(torch.nn.functional.linear(sample, a), b) * 2.0
    assert torch.allclose(actual, expected)


def test_tiny_safetensors_checkpoint_generates_through_axiom_native_loop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    torch = pytest.importorskip("torch")
    pytest.importorskip("tokenizers")
    safetensors_torch = pytest.importorskip("safetensors.torch")
    from tokenizers import AddedToken, Tokenizer, models, pre_tokenizers
    from axiom.core.engine import generate_local, generate_local_stream

    model_root = tmp_path / "models"
    model_dir = model_root / "tiny-llama"
    model_dir.mkdir(parents=True)
    monkeypatch.setenv("AXIOM_MODEL_ROOTS", str(model_root))
    (model_dir / "config.json").write_text(json.dumps(_config()), encoding="utf-8")
    (model_dir / "tokenizer_config.json").write_text(json.dumps({"add_bos_token": True}), encoding="utf-8")
    tokenizer = Tokenizer(models.WordLevel(
        {"[UNK]": 0, "<s>": 1, "</s>": 2, "hello": 3, "world": 4, "token5": 5, "token6": 6, "token7": 7},
        unk_token="[UNK]",
    ))
    tokenizer.pre_tokenizer = pre_tokenizers.WhitespaceSplit()
    tokenizer.add_special_tokens([
        AddedToken("<s>", special=True),
        AddedToken("</s>", special=True),
        AddedToken("[UNK]", special=True),
    ])
    tokenizer.save(str(model_dir / "tokenizer.json"))
    safetensors_torch.save_file(_tiny_weights(torch), str(model_dir / "model.safetensors"))

    result = generate_local(str(model_dir), "hello world", max_new_tokens=2, temperature=0)

    assert result["engine"] == "axiom-native-engine"
    assert result["execution_backend"] == "pytorch-native-axiom"
    assert result["transformers_generation_used"] is False
    assert result["ollama_used"] is False
    assert result["checkpoint_format"] == "safetensors"
    assert result["prompt_tokens"] == 3
    assert result["completion_tokens"] == 2
    assert result["decoder"] == "axiom-autoregressive-kv-cache"

    events = list(generate_local_stream(str(model_dir), "hello world", max_new_tokens=2, temperature=0))
    assert events[-1]["type"] == "complete"
    assert events[-1]["result"]["response"] == result["response"]
    assert all(event["type"] == "token" for event in events[:-1])
    assert len(events[:-1]) == events[-1]["result"]["completion_tokens"]
    assert isinstance(result["response"], str)
