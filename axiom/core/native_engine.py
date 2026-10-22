"""AXIOM-native Llama/Mistral inference.

AXIOM implements the transformer forward pass, RMSNorm, RoPE, grouped-query
attention, KV cache, LoRA application and autoregressive decoding. PyTorch is
used for tensor primitives; Transformers' loader/generate and Ollama are not
used by this module. Only local tokenizer.json and floating-point safetensors
checkpoints are accepted; unsupported formats are rejected, not delegated.
"""
from __future__ import annotations
from contextlib import ExitStack
from dataclasses import dataclass
import json, math, re
from pathlib import Path
from typing import Any, Mapping

_MAX_CONFIG_BYTES = 1_048_576
_MAX_TOKENIZER_BYTES = 64 * 1024 * 1024
_MAX_INDEX_BYTES = 64 * 1024 * 1024
_MAX_WEIGHT_SHARDS = 512
_SUPPORTED_MODEL_TYPES = {"llama", "mistral"}

class NativeEngineError(ValueError):
    """An unsupported, unsafe, or invalid native-engine checkpoint."""

class NativeDependencyError(RuntimeError):
    """A required runtime dependency for the native engine is unavailable."""

@dataclass(frozen=True)
class NativeLlamaConfig:
    model_type: str
    hidden_size: int
    intermediate_size: int
    num_hidden_layers: int
    num_attention_heads: int
    num_key_value_heads: int
    vocab_size: int
    max_position_embeddings: int
    rms_norm_eps: float
    rope_theta: float
    bos_token_id: int | None
    eos_token_ids: tuple[int, ...]
    tie_word_embeddings: bool
    sliding_window: int | None

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "NativeLlamaConfig":
        model_type = value.get("model_type")
        if model_type not in _SUPPORTED_MODEL_TYPES:
            raise NativeEngineError("AXIOM Native Engine supports llama and mistral model_type only; there is no Transformers/Ollama fallback.")
        architectures = value.get("architectures", [])
        if architectures and not any(isinstance(x, str) and x in {"LlamaForCausalLM", "MistralForCausalLM"} for x in architectures):
            raise NativeEngineError("Checkpoint architecture is not a supported Llama/Mistral causal-LM class.")
        rope = value.get("rope_scaling")
        if rope:
            if not isinstance(rope, dict) or rope.get("rope_type", rope.get("type", "default")) != "default" or rope.get("factor", 1.0) != 1.0:
                raise NativeEngineError("This RoPE scaling configuration is not implemented by AXIOM Native Engine.")
        try:
            hidden = int(value["hidden_size"])
            intermediate = int(value["intermediate_size"])
            layers = int(value["num_hidden_layers"])
            heads = int(value["num_attention_heads"])
            kv_heads = int(value.get("num_key_value_heads", heads))
            vocab = int(value["vocab_size"])
            max_positions = int(value.get("max_position_embeddings", 4096))
            rms_eps = float(value.get("rms_norm_eps", 1e-6))
            theta = float(value.get("rope_theta", 10000.0))
        except (KeyError, TypeError, ValueError, OverflowError):
            raise NativeEngineError("Local config.json is missing valid native Llama model dimensions.") from None
        if not (1 <= hidden <= 32768 and 1 <= intermediate <= 131072):
            raise NativeEngineError("Checkpoint hidden/intermediate dimensions exceed native safety limits.")
        if not (1 <= layers <= 256 and 1 <= heads <= 256):
            raise NativeEngineError("Checkpoint layer/head counts exceed native safety limits.")
        if hidden % heads or (hidden // heads) % 2:
            raise NativeEngineError("hidden_size must be divisible into even-sized attention heads.")
        if not (1 <= kv_heads <= heads) or heads % kv_heads:
            raise NativeEngineError("num_key_value_heads must divide num_attention_heads.")
        if not (1 <= vocab <= 1_000_000 and 1 <= max_positions <= 1_000_000):
            raise NativeEngineError("Checkpoint vocabulary/context dimensions exceed native safety limits.")
        if not math.isfinite(rms_eps) or rms_eps <= 0 or not math.isfinite(theta) or theta <= 0:
            raise NativeEngineError("Checkpoint normalization/RoPE settings are invalid.")
        sliding = value.get("sliding_window") if model_type == "mistral" else None
        if sliding is not None and (isinstance(sliding, bool) or not isinstance(sliding, int) or sliding < 1):
            raise NativeEngineError("Mistral sliding_window must be a positive integer.")
        bos0, eos0 = value.get("bos_token_id"), value.get("eos_token_id")
        bos = bos0 if isinstance(bos0, int) and not isinstance(bos0, bool) else None
        eos = (eos0,) if isinstance(eos0, int) and not isinstance(eos0, bool) else tuple(eos0) if isinstance(eos0, list) and all(isinstance(x, int) and not isinstance(x, bool) for x in eos0) else ()
        if any(x < 0 or x >= vocab for x in (*eos, *((bos,) if bos is not None else ()))):
            raise NativeEngineError("Configured BOS/EOS token ID is outside vocab_size.")
        return cls(model_type, hidden, intermediate, layers, heads, kv_heads, vocab, max_positions, rms_eps, theta, bos, eos, value.get("tie_word_embeddings") is True, sliding)

def _within_trusted_roots(path: Path, trusted_roots: tuple[Path, ...]) -> bool:
    for root in trusted_roots:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def _resolve_trusted_file(path: Path, trusted_roots: tuple[Path, ...], label: str) -> Path:
    """Resolve a model asset and allow symlinks only when the final target remains trusted."""
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError):
        raise NativeEngineError(f"{label} must be an existing local file.") from None
    if not resolved.is_file() or not _within_trusted_roots(resolved, trusted_roots):
        raise NativeEngineError(f"{label} resolves outside the configured trusted model roots.")
    return resolved

def _read_json_object(
    path: Path,
    max_bytes: int,
    label: str,
    trusted_roots: tuple[Path, ...] | None = None,
) -> dict[str, Any]:
    roots = trusted_roots or (path.parent.resolve(),)
    safe_path = _resolve_trusted_file(path, roots, label)
    try:
        if safe_path.stat().st_size > max_bytes:
            raise NativeEngineError(f"{label} exceeds its size limit.")
        payload = json.loads(safe_path.read_text(encoding="utf-8"))
    except NativeEngineError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise NativeEngineError(f"{label} could not be read as valid UTF-8 JSON.") from None
    if not isinstance(payload, dict):
        raise NativeEngineError(f"{label} must contain a JSON object.")
    return payload

def _resolve_safetensor_files(
    model_dir: Path,
    trusted_roots: tuple[Path, ...] | None = None,
) -> tuple[list[Path], dict[str, str]]:
    trusted_roots = trusted_roots or (model_dir.resolve(),)
    index_path, single_path = model_dir / "model.safetensors.index.json", model_dir / "model.safetensors"
    if index_path.is_file():
        index = _read_json_object(index_path, _MAX_INDEX_BYTES, "Safetensors shard index", trusted_roots)
        weight_map = index.get("weight_map")
        if not isinstance(weight_map, dict) or not weight_map:
            raise NativeEngineError("Safetensors index must contain a non-empty weight_map object.")
        shards: set[str] = set()
        normalized: dict[str, str] = {}
        for tensor_name, filename in weight_map.items():
            if not isinstance(tensor_name, str) or not tensor_name or not isinstance(filename, str):
                raise NativeEngineError("Safetensors index contains an invalid tensor mapping.")
            shard = Path(filename)
            if shard.name != filename or "/" in filename or "\\" in filename or filename in {"", ".", ".."} or shard.suffix != ".safetensors":
                raise NativeEngineError("Safetensors index contains an unsafe or unsupported shard path.")
            shards.add(filename)
            normalized[tensor_name] = filename
        if len(shards) > _MAX_WEIGHT_SHARDS:
            raise NativeEngineError("Checkpoint has more than 512 safetensors shards.")
        files = [model_dir / name for name in sorted(shards)]
        for path in files:
            _resolve_trusted_file(path, trusted_roots, "Safetensors shard")
        return files, normalized
    if single_path.is_file():
        _resolve_trusted_file(single_path, trusted_roots, "Safetensors checkpoint")
        return [single_path], {}
    if (model_dir / "pytorch_model.bin").exists() or any(model_dir.glob("pytorch_model-*.bin")):
        raise NativeEngineError("Pickle-based .bin weights are unsupported; use safetensors. AXIOM will not load arbitrary pickle payloads.")
    raise NativeEngineError("No model.safetensors or model.safetensors.index.json was found in the model directory.")

def _safetensor_keys(files: list[Path], trusted_roots: tuple[Path, ...]) -> dict[str, str]:
    try:
        from safetensors import safe_open
    except (ImportError, OSError):
        raise NativeDependencyError("AXIOM Native Engine requires safetensors. Install the native-inference extra.") from None
    result: dict[str, str] = {}
    for path in files:
        try:
            with safe_open(str(_resolve_trusted_file(path, trusted_roots, "Safetensors shard")), framework="pt", device="cpu") as handle:
                keys = list(handle.keys())
        except Exception:
            raise NativeEngineError(f"Safetensors shard {path.name!r} could not be inspected safely.") from None
        for key in keys:
            if key in result:
                raise NativeEngineError(f"Tensor {key!r} is duplicated across safetensors shards.")
            result[key] = path.name
    return result

class NativeLlamaRuntime:
    """AXIOM-owned implementation of Llama/Mistral forward and decode steps."""

    def __init__(self, config: NativeLlamaConfig, weights: dict[str, Any], torch_module: Any, device: Any, *, adapter: dict[str, dict[str, Any]] | None = None, adapter_scaling: dict[str, float] | None = None) -> None:
        self.config, self.weights, self.torch, self.device = config, weights, torch_module, device
        self.adapter, self.adapter_scaling = adapter or {}, adapter_scaling or {}
        self.dtype = weights["model.embed_tokens.weight"].dtype
        self.name = "axiom-native-pytorch-llama"
        self.last_generation: dict[str, Any] = {}

    @staticmethod
    def _required_weight_names(c: NativeLlamaConfig) -> list[str]:
        names = ["model.embed_tokens.weight"]
        for i in range(c.num_hidden_layers):
            p = f"model.layers.{i}."
            names.extend(p + x for x in (
                "self_attn.q_proj.weight", "self_attn.k_proj.weight", "self_attn.v_proj.weight", "self_attn.o_proj.weight",
                "mlp.gate_proj.weight", "mlp.up_proj.weight", "mlp.down_proj.weight", "input_layernorm.weight", "post_attention_layernorm.weight",
            ))
        names.append("model.norm.weight")
        if not c.tie_word_embeddings:
            names.append("lm_head.weight")
        return names

    @classmethod
    def from_directory(cls, model_dir: Path, torch_module: Any, device: Any, *, adapter_dir: Path | None = None, trusted_roots: tuple[Path, ...] | None = None) -> "NativeLlamaRuntime":
        roots = trusted_roots or (model_dir.resolve(),)
        config = NativeLlamaConfig.from_mapping(_read_json_object(model_dir / "config.json", _MAX_CONFIG_BYTES, "Model config.json", roots))
        tokenizer_path = _resolve_trusted_file(model_dir / "tokenizer.json", roots, "Tokenizer file")
        if tokenizer_path.stat().st_size > _MAX_TOKENIZER_BYTES:
            raise NativeEngineError("AXIOM Native Engine requires a local tokenizer.json of at most 64 MiB.")
        files, indexed_map = _resolve_safetensor_files(model_dir, roots)
        discovered = _safetensor_keys(files, roots)
        weight_map = indexed_map or discovered
        if indexed_map and set(discovered) != set(indexed_map):
            raise NativeEngineError("Safetensors index and actual shard contents do not agree.")
        required = cls._required_weight_names(config)
        missing = [name for name in required if name not in weight_map]
        if missing:
            raise NativeEngineError("Checkpoint is missing native Llama weights: " + ", ".join(missing[:5]) + ".")
        try:
            from safetensors import safe_open
        except (ImportError, OSError):
            raise NativeDependencyError("AXIOM Native Engine requires safetensors; install the native-inference extra.") from None
        weights: dict[str, Any] = {}
        try:
            with ExitStack() as stack:
                handles = {p.name: stack.enter_context(safe_open(str(_resolve_trusted_file(p, roots, "Safetensors shard")), framework="pt", device="cpu")) for p in files}
                embedding = handles[weight_map["model.embed_tokens.weight"]].get_tensor("model.embed_tokens.weight")
                dtype = embedding.dtype
                weights["model.embed_tokens.weight"] = embedding.to(device=device, dtype=dtype)
                load_names = [name for name in required if name != "model.embed_tokens.weight"]
                if "lm_head.weight" in weight_map and "lm_head.weight" not in load_names:
                    load_names.append("lm_head.weight")
                for i in range(config.num_hidden_layers):
                    p = f"model.layers.{i}."
                    for module in ("self_attn.q_proj", "self_attn.k_proj", "self_attn.v_proj", "self_attn.o_proj", "mlp.gate_proj", "mlp.up_proj", "mlp.down_proj"):
                        bias = p + module + ".bias"
                        if bias in weight_map:
                            load_names.append(bias)
                for name in load_names:
                    tensor = handles[weight_map[name]].get_tensor(name)
                    if tensor.dtype not in (torch_module.float16, torch_module.bfloat16, torch_module.float32):
                        raise NativeEngineError(f"Unsupported weight dtype for tensor {name!r}.")
                    weights[name] = tensor.to(device=device, dtype=dtype)
        except NativeEngineError:
            raise
        except Exception:
            raise NativeEngineError("Checkpoint weights could not be loaded from local safetensors files.") from None
        hdim = config.hidden_size // config.num_attention_heads
        expected = {"model.embed_tokens.weight": (config.vocab_size, config.hidden_size), "model.norm.weight": (config.hidden_size,)}
        for i in range(config.num_hidden_layers):
            p = f"model.layers.{i}."
            expected.update({
                p + "self_attn.q_proj.weight": (config.num_attention_heads * hdim, config.hidden_size),
                p + "self_attn.k_proj.weight": (config.num_key_value_heads * hdim, config.hidden_size),
                p + "self_attn.v_proj.weight": (config.num_key_value_heads * hdim, config.hidden_size),
                p + "self_attn.o_proj.weight": (config.hidden_size, config.hidden_size),
                p + "mlp.gate_proj.weight": (config.intermediate_size, config.hidden_size),
                p + "mlp.up_proj.weight": (config.intermediate_size, config.hidden_size),
                p + "mlp.down_proj.weight": (config.hidden_size, config.intermediate_size),
                p + "input_layernorm.weight": (config.hidden_size,),
                p + "post_attention_layernorm.weight": (config.hidden_size,),
            })
        if "lm_head.weight" in weight_map:
            expected["lm_head.weight"] = (config.vocab_size, config.hidden_size)
        for name, shape in expected.items():
            if name not in weights or tuple(weights[name].shape) != shape:
                raise NativeEngineError(f"Checkpoint tensor {name!r} has a shape inconsistent with config.json.")
        if "lm_head.weight" not in weights:
            if not config.tie_word_embeddings:
                raise NativeEngineError("Checkpoint has no lm_head.weight and does not declare tied embeddings.")
            weights["lm_head.weight"] = weights["model.embed_tokens.weight"]
        adapters: dict[str, dict[str, Any]] = {}
        scaling: dict[str, float] = {}
        if adapter_dir is not None:
            adapters, scaling = cls._load_lora_adapter(adapter_dir, config, torch_module, device, dtype, roots)
            for path, pair in adapters.items():
                base = weights.get(path + ".weight")
                if base is None or pair["A"].shape[1] != base.shape[1] or pair["B"].shape != (base.shape[0], pair["A"].shape[0]):
                    raise NativeEngineError(f"LoRA weight shapes do not match base module {path!r}.")
        return cls(config, weights, torch_module, device, adapter=adapters, adapter_scaling=scaling)

    @classmethod
    def _load_lora_adapter(cls, adapter_dir: Path, config: NativeLlamaConfig, torch_module: Any, device: Any, dtype: Any, trusted_roots: tuple[Path, ...]) -> tuple[dict[str, dict[str, Any]], dict[str, float]]:
        c = _read_json_object(adapter_dir / "adapter_config.json", _MAX_CONFIG_BYTES, "LoRA adapter config", trusted_roots)
        for flag in ("use_dora", "use_qalora", "use_rslora"):
            if c.get(flag) is True:
                raise NativeEngineError(f"LoRA option {flag} is not supported by AXIOM Native Engine.")
        if c.get("bias", "none") != "none" or c.get("modules_to_save") or c.get("rank_pattern") or c.get("alpha_pattern") or c.get("fan_in_fan_out") is True:
            raise NativeEngineError("LoRA adapter uses bias, modules_to_save, per-module rank/alpha, or fan_in_fan_out which are not supported.")
        targets = c.get("target_modules")
        target_set = {targets} if isinstance(targets, str) else set(targets) if isinstance(targets, list) and all(isinstance(x, str) for x in targets) else set()
        rank, alpha = c.get("r"), c.get("lora_alpha")
        if not target_set or isinstance(rank, bool) or not isinstance(rank, int) or not 1 <= rank <= 4096:
            raise NativeEngineError("LoRA adapter target_modules or rank is invalid.")
        if isinstance(alpha, bool) or not isinstance(alpha, (int, float)) or not math.isfinite(float(alpha)) or alpha <= 0:
            raise NativeEngineError("LoRA adapter lora_alpha is invalid.")
        if c.get("task_type") not in (None, "CAUSAL_LM"):
            raise NativeEngineError("Only CAUSAL_LM LoRA adapters are supported.")
        path = adapter_dir / "adapter_model.safetensors"
        if not path.is_file():
            raise NativeEngineError("LoRA adapter requires adapter_model.safetensors; pickle adapter files are unsupported.")
        safe_adapter_path = _resolve_trusted_file(path, trusted_roots, "LoRA safetensors checkpoint")
        try:
            from safetensors import safe_open
            with safe_open(str(safe_adapter_path), framework="pt", device="cpu") as handle:
                adapters: dict[str, dict[str, Any]] = {}
                for key in handle.keys():
                    match = re.fullmatch(r"(.+)\.lora_([AB])(?:\.default)?\.weight", key)
                    if not match:
                        raise NativeEngineError(f"Unsupported LoRA tensor key {key!r}.")
                    module_path, side = match.group(1), match.group(2)
                    if module_path.startswith("base_model.model."):
                        module_path = module_path[len("base_model.model."):]
                    elif module_path.startswith("base_model."):
                        module_path = module_path[len("base_model."):]
                    if module_path.split(".")[-1] not in target_set:
                        raise NativeEngineError("LoRA weight targets a module not listed in adapter_config.json.")
                    adapters.setdefault(module_path, {})[side] = handle.get_tensor(key).to(device=device, dtype=dtype)
        except NativeEngineError:
            raise
        except Exception:
            raise NativeEngineError("LoRA weights could not be read from local safetensors.") from None
        scaling: dict[str, float] = {}
        for module_path, pair in adapters.items():
            if "A" not in pair or "B" not in pair:
                raise NativeEngineError("Each LoRA module requires both lora_A and lora_B.")
            a, b = pair["A"], pair["B"]
            if a.ndim != 2 or b.ndim != 2 or a.shape[0] != rank or b.shape[1] != rank:
                raise NativeEngineError(f"LoRA rank is inconsistent for {module_path!r}.")
            scaling[module_path] = float(alpha) / rank
        return adapters, scaling

    def _linear(self, hidden: Any, module: str) -> Any:
        functional = self.torch.nn.functional
        weight = self.weights.get(module + ".weight")
        if weight is None:
            raise NativeEngineError(f"Missing projection weights for {module!r}.")
        result = functional.linear(hidden, weight, self.weights.get(module + ".bias"))
        adapter = self.adapter.get(module)
        if adapter:
            result = result + functional.linear(functional.linear(hidden, adapter["A"]), adapter["B"]) * self.adapter_scaling[module]
        return result

    def _rms_norm(self, hidden: Any, weight: Any) -> Any:
        variance = hidden.float().pow(2).mean(dim=-1, keepdim=True)
        return hidden * self.torch.rsqrt(variance + self.config.rms_norm_eps).to(dtype=hidden.dtype) * weight

    def _apply_rope(self, values: Any, positions: Any) -> Any:
        torch, dim = self.torch, values.shape[-1]
        inv_freq = 1.0 / (self.config.rope_theta ** (torch.arange(0, dim, 2, device=self.device, dtype=torch.float32) / dim))
        frequencies = torch.einsum("i,j->ij", positions.to(dtype=torch.float32), inv_freq)
        embedding = torch.cat((frequencies, frequencies), dim=-1)
        cos, sin = embedding.cos().to(dtype=values.dtype)[None, None, :, :], embedding.sin().to(dtype=values.dtype)[None, None, :, :]
        half = dim // 2
        return values * cos + torch.cat((-values[..., half:], values[..., :half]), dim=-1) * sin

    def forward(self, input_ids: Any, past_key_values: Any = None) -> tuple[Any, tuple[Any, ...]]:
        torch, c = self.torch, self.config
        if input_ids.ndim != 2 or input_ids.shape[0] != 1:
            raise NativeEngineError("AXIOM Native Engine currently accepts one prompt sequence per request.")
        seq_len = input_ids.shape[1]
        past_len = 0 if past_key_values is None else int(past_key_values[0][0].shape[-2])
        if past_len + seq_len > self.config.max_position_embeddings:
            raise NativeEngineError("Generation would exceed the checkpoint's configured maximum context length.")
        hidden = torch.nn.functional.embedding(input_ids, self.weights["model.embed_tokens.weight"])
        positions = torch.arange(past_len, past_len + seq_len, device=self.device)
        cache, head_dim = [], c.hidden_size // c.num_attention_heads
        repeat_factor = c.num_attention_heads // c.num_key_value_heads
        for i in range(c.num_hidden_layers):
            p = f"model.layers.{i}."
            residual = hidden
            normed = self._rms_norm(hidden, self.weights[p + "input_layernorm.weight"])
            q, k, v = (self._linear(normed, p + "self_attn." + name) for name in ("q_proj", "k_proj", "v_proj"))
            q = self._apply_rope(q.view(1, seq_len, c.num_attention_heads, head_dim).transpose(1, 2), positions)
            k = self._apply_rope(k.view(1, seq_len, c.num_key_value_heads, head_dim).transpose(1, 2), positions)
            v = v.view(1, seq_len, c.num_key_value_heads, head_dim).transpose(1, 2)
            if past_key_values is not None:
                old_k, old_v = past_key_values[i]
                k, v = torch.cat((old_k, k), dim=-2), torch.cat((old_v, v), dim=-2)
            cache.append((k, v))
            ak = k.repeat_interleave(repeat_factor, dim=1) if repeat_factor > 1 else k
            av = v.repeat_interleave(repeat_factor, dim=1) if repeat_factor > 1 else v
            scores = torch.matmul(q, ak.transpose(-2, -1)) / math.sqrt(head_dim)
            keys = torch.arange(ak.shape[-2], device=self.device)
            causal = keys[None, :] > positions[:, None]
            if c.sliding_window:
                causal = causal | (keys[None, :] <= positions[:, None] - c.sliding_window)
            scores = scores.masked_fill(causal[None, None, :, :], float("-inf"))
            probabilities = torch.softmax(scores.float(), dim=-1).to(dtype=q.dtype)
            attended = torch.matmul(probabilities, av).transpose(1, 2).contiguous().view(1, seq_len, c.hidden_size)
            hidden = residual + self._linear(attended, p + "self_attn.o_proj")
            residual = hidden
            normed = self._rms_norm(hidden, self.weights[p + "post_attention_layernorm.weight"])
            gate, up = self._linear(normed, p + "mlp.gate_proj"), self._linear(normed, p + "mlp.up_proj")
            hidden = residual + self._linear(torch.nn.functional.silu(gate) * up, p + "mlp.down_proj")
        hidden = self._rms_norm(hidden, self.weights["model.norm.weight"])
        return self._linear(hidden[:, -1:, :], "lm_head")[:, -1, :], tuple(cache)

    def generate(self, prompt_token_ids: list[int], *, max_new_tokens: int, temperature: float, top_p: float = 0.9, eos_token_ids: tuple[int, ...] | None = None) -> list[int]:
        if not prompt_token_ids:
            raise NativeEngineError("Tokenizer returned no IDs for the prompt.")
        if isinstance(max_new_tokens, bool) or not isinstance(max_new_tokens, int) or not 1 <= max_new_tokens <= 2048:
            raise NativeEngineError("Native generation token limit must be between 1 and 2048.")
        if not math.isfinite(float(temperature)) or not 0 <= float(temperature) <= 2:
            raise NativeEngineError("Native generation temperature must be between 0 and 2.")
        if not math.isfinite(float(top_p)) or not 0 < float(top_p) <= 1:
            raise NativeEngineError("Native generation top_p must be greater than 0 and at most 1.")
        torch = self.torch
        eos = set(self.config.eos_token_ids if eos_token_ids is None else eos_token_ids)
        tokens = torch.tensor([prompt_token_ids], device=self.device, dtype=torch.long)
        generated = []
        logits, cache = self.forward(tokens)
        for _ in range(max_new_tokens):
            if temperature == 0:
                next_token = torch.argmax(logits, dim=-1)
            else:
                scores = logits.float() / float(temperature)
                if top_p < 1:
                    sorted_scores, sorted_ids = torch.sort(scores, descending=True, dim=-1)
                    cumulative = torch.softmax(sorted_scores, dim=-1).cumsum(dim=-1)
                    remove = cumulative > top_p
                    remove[..., 1:] = remove[..., :-1].clone()
                    remove[..., 0] = False
                    sorted_scores = sorted_scores.masked_fill(remove, float("-inf"))
                    scores = torch.full_like(scores, float("-inf")).scatter(dim=-1, index=sorted_ids, src=sorted_scores)
                next_token = torch.multinomial(torch.softmax(scores, dim=-1), num_samples=1).squeeze(-1)
            token_id = int(next_token.item())
            if token_id < 0 or token_id >= self.config.vocab_size:
                raise NativeEngineError("Native decoder produced a token ID outside vocab_size.")
            if token_id in eos:
                break
            generated.append(token_id)
            logits, cache = self.forward(next_token.view(1, 1), cache)
        self.last_generation = {"prompt_tokens": len(prompt_token_ids), "completion_tokens": len(generated), "cache_layers": len(cache), "decoder": "axiom-autoregressive-kv-cache"}
        return generated

def load_native_runtime(model_dir: Path, torch_module: Any, device: Any, *, adapter_dir: Path | None = None, trusted_roots: tuple[Path, ...] | None = None) -> tuple[NativeLlamaRuntime, Any, dict[str, Any]]:
    """Load a supported local checkpoint/tokenizer without Transformers."""
    try:
        from tokenizers import Tokenizer
    except (ImportError, OSError):
        raise NativeDependencyError("AXIOM Native Engine requires tokenizers. Install the native-inference extra.") from None
    roots = trusted_roots or (model_dir.resolve(),)
    model = NativeLlamaRuntime.from_directory(model_dir, torch_module, device, adapter_dir=adapter_dir, trusted_roots=roots)
    try:
        tokenizer = Tokenizer.from_file(str(_resolve_trusted_file(model_dir / "tokenizer.json", roots, "Tokenizer file")))
    except Exception:
        raise NativeEngineError("tokenizer.json is not compatible with AXIOM's native tokenizer adapter.") from None
    if tokenizer.get_vocab_size(with_added_tokens=True) > model.config.vocab_size:
        raise NativeEngineError("tokenizer.json vocabulary is larger than the model embedding table.")
    tokenizer_config = model_dir / "tokenizer_config.json"
    add_bos = model.config.bos_token_id is not None
    if tokenizer_config.exists():
        add_bos = _read_json_object(tokenizer_config, _MAX_CONFIG_BYTES, "Tokenizer config", roots).get("add_bos_token") is not False and add_bos
    details = {
        "model_type": model.config.model_type,
        "architecture": "LlamaForCausalLM" if model.config.model_type == "llama" else "MistralForCausalLM",
        "model_directory_name": model_dir.name,
        "adapter_directory_name": adapter_dir.name if adapter_dir else None,
        "add_bos_token": add_bos,
        "checkpoint_format": "safetensors",
        "execution_backend": "pytorch-native-axiom",
        "transformers_generation_used": False,
        "ollama_used": False,
        "dtype": str(model.dtype),
        "device": str(device),
    }
    return model, tokenizer, details
