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
    assert tuple(next_logits.shape) == (1, config.vocab_size)
    assert tuple(next_cache[0][0].shape) == (1, config.num_key_value_heads, 4, 4)


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
    from axiom.core.engine import generate_local

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
    assert isinstance(result["response"], str)
