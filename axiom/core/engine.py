"""AXIOM's direct local causal-LM engine.

The runtime is implemented in AXIOM and uses Transformers only to load supported
local model architectures. It does not require Ollama and never downloads model
weights or executes repository-provided model code.
"""
from __future__ import annotations

import gc
import importlib.metadata
import importlib.util
import json
import logging
import os
import re
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_MAX_PROMPT_CHARS = 12_000
_MAX_NEW_TOKENS = 2_048
_MAX_INPUT_TOKENS = 8_192
_MAX_CONFIG_BYTES = 1_048_576
_LOG = logging.getLogger(__name__)
_ENGINE_LOCK = threading.RLock()
_LOADED_RUNTIME: dict[str, Any] | None = None
_LOADED_ARCHITECTURE: str | None = None
_MODEL_ROOT_ENV = "AXIOM_MODEL_ROOTS"
_DEFAULT_MODEL_ROOT_SUFFIXES = (
    Path("models"),
    Path("runs"),
    Path("outputs"),
)


class AxiomEngineError(RuntimeError):
    """Raised when the AXIOM local model engine cannot run a request."""


def _version_key(value: str) -> tuple[int, int, int]:
    parts = [int(part) for part in re.findall(r"\d+", value)[:3]]
    return tuple((parts + [0, 0, 0])[:3])


def runtime_status() -> dict[str, Any]:
    packages: dict[str, bool] = {}
    versions: dict[str, str | None] = {}
    minimum_versions = {"torch": "2.2.0", "transformers": "5.0.0"}
    problems: list[str] = []
    for name in ("torch", "transformers", "peft"):
        try:
            packages[name] = importlib.util.find_spec(name) is not None
        except (ImportError, ModuleNotFoundError, ValueError):
            packages[name] = False
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
        if name in minimum_versions:
            if not packages[name]:
                problems.append(f"{name} is not installed")
            elif versions[name] is not None and _version_key(versions[name]) < _version_key(minimum_versions[name]):
                problems.append(f"{name} {versions[name]} is too old (need >= {minimum_versions[name]})")
    ready = not problems
    return {
        "engine": "axiom-local-engine",
        "ready": ready,
        "packages": packages,
        "versions": versions,
        "minimum_versions": minimum_versions,
        "problems": problems,
        "loaded": _LOADED_RUNTIME is not None,
        "architecture": _LOADED_ARCHITECTURE,
        "model_loading": "local_files_only",
        "remote_code": False,
        "setup_note": (
            "AXIOM Engine is ready for local Transformers causal-LM checkpoints."
            if ready else
            "AXIOM Engine setup required: " + "; ".join(problems)
            + ". Install or upgrade local dependencies with: python -m pip install -e '.[training]'"
        ),
        "scope_note": (
            "AXIOM owns the runtime and training orchestration; pretrained weights remain a separate local input. "
            "Compatibility depends on the checkpoint architecture supported by the installed Transformers version."
        ),
        "checked_at": datetime.now(UTC).isoformat(),
    }


def _allowed_model_roots() -> tuple[Path, ...]:
    """Return canonical roots from trusted defaults and AXIOM_MODEL_ROOTS.

    Set AXIOM_MODEL_ROOTS to one or more trusted directories separated by the
    platform path separator to permit models stored outside the defaults.
    """
    home = Path.home()
    defaults = (
        Path.cwd() / "models",
        Path.cwd() / "runs",
        Path.cwd() / "outputs",
        home / "models",
        home / "Documents" / "models",
        home / "Documents" / "AXIOM-AI" / "models",
        home / "Documents" / "AXIOM-AI" / "runs",
        home / ".cache" / "huggingface" / "hub",
        home / ".local" / "share" / "axiom" / "models",
        home / ".local" / "share" / "axiom" / "fine-tuning",
    )
    configured = os.environ.get(_MODEL_ROOT_ENV, "").strip()
    custom_roots = tuple(Path(item).expanduser() for item in configured.split(os.pathsep) if item.strip())
    roots: list[Path] = []
    seen: set[str] = set()
    for candidate in (*defaults, *custom_roots):
        try:
            canonical = candidate.resolve(strict=True)
        except (OSError, RuntimeError):
            if candidate in custom_roots:
                raise ValueError("AXIOM_MODEL_ROOTS entries must be existing local directories.") from None
            continue
        if not canonical.is_dir():
            if candidate in custom_roots:
                raise ValueError("AXIOM_MODEL_ROOTS entries must be existing local directories.")
            continue
        key = str(canonical)
        if key not in seen:
            seen.add(key)
            roots.append(canonical)
    return tuple(roots)


def _path_is_within_root(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _resolve_model_directory(value: str, label: str) -> Path:
    """Resolve a model/adapter directory only when it stays under a trusted root."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required.")
    if any(character in value for character in ("\\x00", "\\r", "\\n")):
        raise ValueError(f"{label} contains invalid control characters.")

    roots = _allowed_model_roots()
    if not roots:
        raise ValueError(
            "No allowed model directories were found. Create a model directory under ~/models "
            "or set AXIOM_MODEL_ROOTS to trusted local directories."
        )
    try:
        candidate = Path(value).expanduser()
        lexical_path = candidate if candidate.is_absolute() else Path(os.path.abspath(candidate))
    except (OSError, RuntimeError, ValueError):
        raise ValueError(f"{label} must be within an allowed local model directory.") from None

    if not any(_path_is_within_root(lexical_path, root) for root in roots):
        raise ValueError(
            f"{label} must be within an allowed model directory. Set AXIOM_MODEL_ROOTS to add a trusted directory."
        )
    try:
        path = candidate.resolve(strict=True)
    except (OSError, RuntimeError):
        raise ValueError(f"{label} must be an existing local directory.") from None
    if not path.is_dir() or not any(_path_is_within_root(path, root) for root in roots):
        raise ValueError(
            f"{label} must resolve to an existing directory inside an allowed model root; symlink escapes are not allowed."
        )
    return path


def resolve_local_model_directory(value: str, label: str = "Model") -> str:
    """Validate an API-supplied path and return its canonical allowed location."""
    return str(_resolve_model_directory(value, label))


def _inspect_model_config(model_dir: Path) -> dict[str, Any]:
    config_path = model_dir / "config.json"
    try:
        if not config_path.is_file() or config_path.stat().st_size > _MAX_CONFIG_BYTES:
            raise ValueError("Base model directory must contain a config.json no larger than 1 MiB.")
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise ValueError("Local model config.json could not be read as valid UTF-8 JSON.") from None
    if not isinstance(config, dict) or not isinstance(config.get("model_type"), str):
        raise ValueError("Local model config.json must contain a model_type string.")
    architectures = config.get("architectures", [])
    architecture = architectures[0] if isinstance(architectures, list) and architectures and isinstance(architectures[0], str) else config["model_type"]
    return {"config": config, "model_type": config["model_type"], "architecture": architecture}


def validate_generation(prompt: str, max_new_tokens: int, temperature: float) -> tuple[str, int, float]:
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Prompt must contain at least one non-whitespace character.")
    if len(prompt) > _MAX_PROMPT_CHARS:
        raise ValueError(f"Prompt exceeds the {_MAX_PROMPT_CHARS:,}-character limit.")
    if isinstance(max_new_tokens, bool) or not isinstance(max_new_tokens, int) or not 1 <= max_new_tokens <= _MAX_NEW_TOKENS:
        raise ValueError(f"Maximum generated tokens must be between 1 and {_MAX_NEW_TOKENS}.")
    if isinstance(temperature, bool) or not isinstance(temperature, (int, float)) or not 0 <= float(temperature) <= 2:
        raise ValueError("Temperature must be between 0 and 2.")
    return prompt, max_new_tokens, float(temperature)


def _load_local_model(model_path: str, adapter_path: str | None):
    global _LOADED_RUNTIME, _LOADED_ARCHITECTURE
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except (ImportError, OSError):
        raise AxiomEngineError("AXIOM Engine dependencies are unavailable. Install with: python -m pip install -e '.[training]'") from None

    base_dir = _resolve_model_directory(model_path, "Base model")
    inspected = _inspect_model_config(base_dir)
    resolved_adapter: str | None = None
    if adapter_path and adapter_path.strip():
        adapter_dir = _resolve_model_directory(adapter_path, "LoRA adapter")
        if not (adapter_dir / "adapter_config.json").is_file():
            raise ValueError("LoRA adapter directory must contain adapter_config.json.")
        if not any((adapter_dir / name).is_file() for name in ("adapter_model.safetensors", "adapter_model.bin")):
            raise ValueError("LoRA adapter directory must contain adapter_model.safetensors or adapter_model.bin.")
        resolved_adapter = str(adapter_dir)

    key = (str(base_dir), resolved_adapter)
    inspected["model_directory_name"] = base_dir.name
    inspected["adapter_directory_name"] = Path(resolved_adapter).name if resolved_adapter else None
    if _LOADED_RUNTIME is not None and _LOADED_RUNTIME["key"] == key:
        return (
            _LOADED_RUNTIME["model"],
            _LOADED_RUNTIME["tokenizer"],
            _LOADED_RUNTIME["torch"],
            _LOADED_RUNTIME["device"],
            inspected,
        )

    # Reclaim the previous model before loading another checkpoint. Retaining
    # two large language models can exhaust system RAM or accelerator memory.
    previous_runtime = _LOADED_RUNTIME
    _LOADED_RUNTIME = None
    _LOADED_ARCHITECTURE = None
    if previous_runtime is not None:
        previous_torch = previous_runtime.get("torch")
        del previous_runtime
        gc.collect()
        try:
            if previous_torch is not None and previous_torch.cuda.is_available():
                previous_torch.cuda.empty_cache()
        except (RuntimeError, AttributeError):
            _LOG.debug("GPU cache cleanup was unavailable while replacing the loaded model.", exc_info=True)

    try:
        tokenizer = AutoTokenizer.from_pretrained(
            str(base_dir), local_files_only=True, trust_remote_code=False
        )
        if torch.cuda.is_available():
            dtype = torch.float16
            device = torch.device("cuda")
        else:
            dtype = torch.float32
            mps = getattr(getattr(torch, "backends", None), "mps", None)
            device = torch.device("mps") if mps is not None and mps.is_available() else torch.device("cpu")
        model = AutoModelForCausalLM.from_pretrained(
            str(base_dir),
            local_files_only=True,
            trust_remote_code=False,
            dtype=dtype,
            low_cpu_mem_usage=True,
        )
        model.to(device)
        if resolved_adapter:
            try:
                from peft import PeftModel
            except (ImportError, OSError):
                raise AxiomEngineError("Loading a LoRA adapter requires PEFT. Install with: python -m pip install -e '.[training]'") from None
            model = PeftModel.from_pretrained(
                model, resolved_adapter, local_files_only=True, is_trainable=False
            )
        model.eval()
    except (ValueError, AxiomEngineError):
        raise
    except Exception as exc:
        detail = str(exc).replace("\r", " ").replace("\n", " ").strip()[:300]
        raise AxiomEngineError(
            "AXIOM Engine could not load this local checkpoint or adapter. Confirm that the weights, tokenizer, "
            "architecture, and installed dependencies are compatible." + (f" Detail: {detail}" if detail else "")
        ) from None

    _LOADED_RUNTIME = {
        "key": key,
        "model": model,
        "tokenizer": tokenizer,
        "torch": torch,
        "device": device,
    }
    _LOADED_ARCHITECTURE = inspected["architecture"]
    return model, tokenizer, torch, device, inspected



def unload_local_model() -> dict[str, Any]:
    """Release the loaded local model and best-effort accelerator cache."""
    global _LOADED_RUNTIME, _LOADED_ARCHITECTURE
    with _ENGINE_LOCK:
        previous_runtime = _LOADED_RUNTIME
        was_loaded = previous_runtime is not None
        _LOADED_RUNTIME = None
        _LOADED_ARCHITECTURE = None
        if previous_runtime is not None:
            previous_torch = previous_runtime.get("torch")
            del previous_runtime
            gc.collect()
            try:
                if previous_torch is not None and previous_torch.cuda.is_available():
                    previous_torch.cuda.empty_cache()
            except (RuntimeError, AttributeError):
                _LOG.debug("GPU cache cleanup was unavailable while unloading the model.", exc_info=True)
        else:
            gc.collect()
        return {
            "schema_version": 1,
            "unloaded": was_loaded,
            "loaded": False,
            "scope_note": "The loaded model and tokenizer references were released by AXIOM. Framework or OS-level allocators may retain some reserved memory.",
        }


def generate_local(
    model_path: str,
    prompt: str,
    *,
    adapter_path: str | None = None,
    max_new_tokens: int = 256,
    temperature: float = 0.7,
) -> dict[str, Any]:
    prompt, max_new_tokens, temperature = validate_generation(prompt, max_new_tokens, temperature)
    with _ENGINE_LOCK:
        model, tokenizer, torch, device, inspected = _load_local_model(model_path, adapter_path)
        context_cap = inspected["config"].get("max_position_embeddings") or inspected["config"].get("n_positions") or 4096
        try:
            context_cap = max(128, min(int(context_cap), _MAX_INPUT_TOKENS + _MAX_NEW_TOKENS))
        except (ValueError, TypeError, OverflowError):
            context_cap = 4096
        input_limit = max(1, min(_MAX_INPUT_TOKENS, context_cap - max_new_tokens))
        encoded = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=input_limit)
        input_ids = encoded["input_ids"].to(device)
        attention_mask = encoded.get("attention_mask")
        if attention_mask is not None:
            attention_mask = attention_mask.to(device)
        kwargs: dict[str, Any] = {
            "input_ids": input_ids,
            "max_new_tokens": min(max_new_tokens, max(1, context_cap - input_ids.shape[-1])),
            "do_sample": temperature > 0,
            "pad_token_id": tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id,
        }
        if attention_mask is not None:
            kwargs["attention_mask"] = attention_mask
        if temperature > 0:
            kwargs["temperature"] = temperature
            kwargs["top_p"] = 0.9
        started = time.perf_counter()
        try:
            with torch.inference_mode():
                output_ids = model.generate(**kwargs)
        except Exception as exc:
            detail = str(exc).replace("\r", " ").replace("\n", " ").strip()[:300]
            raise AxiomEngineError(
                "AXIOM Engine generation failed. The prompt/context may exceed available memory or this model's limits."
                + (f" Detail: {detail}" if detail else "")
            ) from None
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        input_token_count = int(input_ids.shape[-1])
        continuation = output_ids[0, input_token_count:]
        response = tokenizer.decode(continuation, skip_special_tokens=True)
        response = response[:100_000]
        return {
            "engine": "axiom-local-engine",
            "model": inspected["model_directory_name"] or "local-model",
            "architecture": inspected["architecture"],
            "adapter": inspected["adapter_directory_name"],
            "response": response,
            "prompt_tokens": input_token_count,
            "completion_tokens": int(continuation.shape[-1]),
            "elapsed_ms": elapsed_ms,
            "generated_at": datetime.now(UTC).isoformat(),
            "local_only": True,
        }
