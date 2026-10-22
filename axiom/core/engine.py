"""AXIOM-owned native Llama/Mistral inference engine.

PyTorch supplies device tensor kernels; AXIOM implements the supported model
forward pass, attention/cache path, LoRA application, and token-by-token decode.
Local weights and tokenizer assets are required. The native path does not call
Transformers model generation or an Ollama service.
"""
from __future__ import annotations

import gc
from functools import lru_cache
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


class AxiomEngineError(RuntimeError):
    """Raised when the AXIOM local model engine cannot run a request."""


def _version_key(value: str) -> tuple[int, int, int]:
    parts = [int(part) for part in re.findall(r"\d+", value)[:3]]
    return tuple((parts + [0, 0, 0])[:3])


def runtime_status() -> dict[str, Any]:
    packages: dict[str, bool] = {}
    versions: dict[str, str | None] = {}
    minimum_versions = {"torch": "2.2.0", "tokenizers": "0.19.0", "safetensors": "0.4.0"}
    problems: list[str] = []
    for name in ("torch", "tokenizers", "safetensors"):
        try:
            packages[name] = importlib.util.find_spec(name) is not None
        except (ImportError, ModuleNotFoundError, ValueError):
            packages[name] = False
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
        if not packages[name]:
            problems.append(f"{name} is not installed")
        elif versions[name] is not None and _version_key(versions[name]) < _version_key(minimum_versions[name]):
            problems.append(f"{name} {versions[name]} is too old (need >= {minimum_versions[name]})")
    ready = not problems
    return {
        "engine": "axiom-native-pytorch-llama",
        "ready": ready,
        "packages": packages,
        "versions": versions,
        "minimum_versions": minimum_versions,
        "problems": problems,
        "loaded": _LOADED_RUNTIME is not None,
        "architecture": _LOADED_ARCHITECTURE,
        "model_loading": "local_safetensors_only",
        "execution_backend": "pytorch-native-axiom",
        "transformers_generation_used": False,
        "ollama_used": False,
        "remote_code": False,
        "supported_model_types": ["llama", "mistral"],
        "supported_weights": ["safetensors"],
        "setup_note": (
            "AXIOM Native Engine is ready for supported local Llama/Mistral safetensors checkpoints."
            if ready else
            "AXIOM Native Engine setup required: " + "; ".join(problems)
            + ". Install with: python -m pip install -e '.[native-inference]'"
        ),
        "scope_note": (
            "AXIOM implements its own Llama/Mistral forward pass, RMSNorm, RoPE, grouped-query attention, KV cache, "
            "LoRA application and token-by-token decoder using PyTorch tensor operations. It does not call "
            "Transformers model.generate or an Ollama server. Checkpoint acquisition and model training are separate."
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


@lru_cache(maxsize=8)
def _trusted_file_entry(path: str, root_text: str) -> bool:
    try:
        resolved = os.path.realpath(path)
        return os.path.isfile(resolved) and os.path.commonpath((resolved, root_text)) == root_text
    except (OSError, ValueError):
        return False


def _trusted_directory_index(
    root_strings: tuple[str, ...],
    freshness_bucket: int,
) -> tuple[tuple[str, bool, bool, bool], ...]:
    """Index model directories by walking only configured trusted roots.

    Request strings are compared to this filesystem-derived index; they are
    never fed into Path, open, stat, resolve, or another filesystem operation.
    The time bucket expires the index every 30 seconds so newly installed models
    become selectable without an API restart.
    """
    del freshness_bucket
    entries: dict[str, tuple[str, bool, bool, bool]] = {}
    max_dirs_per_root = 50_000
    max_depth = 12
    for root_text in root_strings:
        visited = 0
        for directory, subdirs, filenames in os.walk(root_text, topdown=True, followlinks=False):
            visited += 1
            if visited > max_dirs_per_root:
                break
            try:
                relative = os.path.relpath(directory, root_text)
                depth = 0 if relative == os.curdir else len(Path(relative).parts)
            except (OSError, ValueError):
                subdirs[:] = []
                continue
            blocked_subdirs: list[str] = []
            allowed_subdirs: list[str] = []
            for name in subdirs:
                child = os.path.join(directory, name)
                if os.path.islink(child):
                    blocked_subdirs.append(child)
                else:
                    allowed_subdirs.append(name)
            subdirs[:] = allowed_subdirs if depth < max_depth else []
            for blocked in blocked_subdirs:
                key = os.path.normcase(os.path.normpath(blocked))
                entries[key] = (blocked, False, False, True)

            if depth > max_depth:
                continue
            model_config = "config.json" in filenames
            adapter_config = "adapter_config.json" in filenames
            if not model_config and not adapter_config:
                continue
            marker_names = (("config.json",) if model_config else ()) + (("adapter_config.json",) if adapter_config else ())
            # HF cache metadata may be symlinked to blobs. Only accept targets
            # whose canonical path remains below this root.
            if any(not _trusted_file_entry(os.path.join(directory, marker), root_text) for marker in marker_names):
                continue
            try:
                canonical = os.path.realpath(directory)
                if os.path.commonpath((canonical, root_text)) != root_text:
                    continue
            except (OSError, ValueError):
                continue
            key = os.path.normcase(os.path.normpath(canonical))
            entries[key] = (canonical, model_config, adapter_config, False)
    return tuple(entries[key] for key in sorted(entries))


def _resolve_model_directory(value: str, label: str) -> Path:
    """Resolve a request by matching it to an inventoried trusted model folder."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required.")
    if len(value) > 4096 or any(character in value for character in ("\\x00", "\\r", "\\n")):
        raise ValueError(f"{label} contains invalid control characters or exceeds the path limit.")

    roots = _allowed_model_roots()
    if not roots:
        raise ValueError(
            "No allowed model directories were found. Create a model directory under ~/models "
            "or set AXIOM_MODEL_ROOTS to trusted local directories."
        )

    # Normalization here is lexical only. All filesystem reads are performed
    # against paths obtained independently from a walk of trusted roots.
    requested_key = os.path.normcase(os.path.normpath(os.path.expanduser(value.strip())))
    root_strings = tuple(str(root) for root in roots)
    freshness_bucket = int(time.monotonic() // 30)
    entries = _trusted_directory_index(root_strings, freshness_bucket)
    for discovered, is_model, is_adapter, is_symlink in entries:
        key = os.path.normcase(os.path.normpath(discovered))
        if key != requested_key:
            continue
        if is_symlink:
            raise ValueError(f"{label} cannot be a symlink; trusted-root escapes are not allowed.")
        lowered = label.casefold()
        if lowered == "base model" and not is_model:
            continue
        if lowered == "lora adapter" and not is_adapter:
            continue
        # The returned path is from the trusted directory inventory, never
        # constructed from the request-supplied path.
        return Path(discovered)
    raise ValueError(
        f"{label} must match an existing checkpoint directory discovered under a trusted model root. "
        "Set AXIOM_MODEL_ROOTS to add a trusted location and retry."
    )

def resolve_local_model_directory(value: str, label: str = "Model") -> str:
    """Validate an API-supplied path and return its canonical allowed location."""
    return str(_resolve_model_directory(value, label))


def discover_local_engine_assets() -> dict[str, Any]:
    """List metadata for native-compatible local folders without loading model weights."""
    roots = _allowed_model_roots()
    if not roots:
        return {
            "schema_version": 1,
            "models": [],
            "adapters": [],
            "truncated": False,
            "scope_note": "No trusted model roots exist yet. Create ~/models or configure AXIOM_MODEL_ROOTS.",
        }

    root_strings = tuple(str(root) for root in roots)
    entries = _trusted_directory_index(root_strings, int(time.monotonic() // 30))
    models: list[dict[str, Any]] = []
    adapters: list[dict[str, Any]] = []
    max_results = 500
    for discovered, is_model, is_adapter, is_symlink in entries:
        if is_symlink:
            continue
        directory = Path(discovered)
        if is_model and len(models) < max_results:
            try:
                inspected = _inspect_model_config(directory)
                from axiom.core.native_engine import NativeLlamaConfig, NativeEngineError

                native_config = NativeLlamaConfig.from_mapping(inspected["config"])
                tokenizer_ok = any(_trusted_file_entry(str(directory / "tokenizer.json"), str(root)) for root in roots)
                single_weights = any(_trusted_file_entry(str(directory / "model.safetensors"), str(root)) for root in roots)
                indexed_weights = any(_trusted_file_entry(str(directory / "model.safetensors.index.json"), str(root)) for root in roots)
                if not tokenizer_ok:
                    continue
                if not (single_weights or indexed_weights):
                    continue
                models.append({
                    "path": discovered,
                    "name": directory.name,
                    "model_type": native_config.model_type,
                    "architecture": inspected["architecture"],
                    "weight_format": "safetensors" if single_weights else "sharded safetensors",
                    "ready_for_native_attempt": True,
                })
            except (ValueError, OSError, RuntimeError):
                # Incompatible or incomplete folders are not offered as runnable models.
                continue
        if is_adapter and len(adapters) < max_results:
            adapter_config = directory / "adapter_config.json"
            adapter_weights = directory / "adapter_model.safetensors"
            config_trusted = any(_trusted_file_entry(str(adapter_config), str(root)) for root in roots)
            weights_trusted = any(_trusted_file_entry(str(adapter_weights), str(root)) for root in roots)
            if config_trusted and weights_trusted:
                adapters.append({
                    "path": discovered,
                    "name": directory.name,
                    "weight_format": "safetensors LoRA",
                })
        if len(models) >= max_results and len(adapters) >= max_results:
            break

    models.sort(key=lambda item: (item["name"].casefold(), item["path"]))
    adapters.sort(key=lambda item: (item["name"].casefold(), item["path"]))
    return {
        "schema_version": 1,
        "models": models,
        "adapters": adapters,
        "truncated": len(models) >= max_results or len(adapters) >= max_results,
        "scope_note": (
            "Metadata-only discovery under trusted local roots. Weight tensors are not loaded or fully validated "
            "until an inference request runs. AXIOM does not download models during discovery."
        ),
    }




def _inspect_model_config(model_dir: Path) -> dict[str, Any]:
    config_path = model_dir / "config.json"
    try:
        resolved_config = config_path.resolve(strict=True)
        if (
            not resolved_config.is_file()
            or resolved_config.stat().st_size > _MAX_CONFIG_BYTES
            or not any(_path_is_within_root(resolved_config, root) for root in _allowed_model_roots())
        ):
            raise ValueError("Base model directory must contain a config.json inside a trusted root and no larger than 1 MiB.")
        config = json.loads(resolved_config.read_text(encoding="utf-8"))
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
    except (ImportError, OSError):
        raise AxiomEngineError(
            "AXIOM Native Engine requires PyTorch. Install with: python -m pip install -e '.[native-inference]'"
        ) from None

    base_dir = _resolve_model_directory(model_path, "Base model")
    inspected = _inspect_model_config(base_dir)
    resolved_adapter: Path | None = None
    if adapter_path and adapter_path.strip():
        adapter_dir = _resolve_model_directory(adapter_path, "LoRA adapter")
        if not (adapter_dir / "adapter_config.json").is_file() or not (adapter_dir / "adapter_model.safetensors").is_file():
            raise ValueError(
                "Native LoRA adapter must contain adapter_config.json and adapter_model.safetensors; "
                "pickle-based adapter weights are not supported."
            )
        resolved_adapter = adapter_dir

    key = (str(base_dir), str(resolved_adapter) if resolved_adapter else None)
    if _LOADED_RUNTIME is not None and _LOADED_RUNTIME["key"] == key:
        return (
            _LOADED_RUNTIME["model"],
            _LOADED_RUNTIME["tokenizer"],
            _LOADED_RUNTIME["torch"],
            _LOADED_RUNTIME["device"],
            _LOADED_RUNTIME["details"],
        )

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
            _LOG.debug("GPU cache cleanup was unavailable while replacing the loaded native model.", exc_info=True)

    if torch.cuda.is_available():
        device = torch.device("cuda")
    else:
        mps = getattr(getattr(torch, "backends", None), "mps", None)
        device = torch.device("mps") if mps is not None and mps.is_available() else torch.device("cpu")

    from axiom.core.native_engine import NativeDependencyError, NativeEngineError, load_native_runtime
    try:
        model, tokenizer, native_details = load_native_runtime(
            base_dir, torch, device, adapter_dir=resolved_adapter, trusted_roots=_allowed_model_roots()
        )
    except NativeDependencyError as exc:
        raise AxiomEngineError(str(exc)) from None
    except NativeEngineError as exc:
        raise ValueError(str(exc)) from None
    except (OSError, RuntimeError):
        _LOG.debug("Native checkpoint load failed.", exc_info=True)
        raise AxiomEngineError(
            "AXIOM Native Engine could not allocate or load this checkpoint. "
            "Confirm supported safetensors weights and available memory."
        ) from None

    details = {
        **inspected,
        **native_details,
        "config": {"max_position_embeddings": model.config.max_position_embeddings},
    }
    _LOADED_RUNTIME = {
        "key": key,
        "model": model,
        "tokenizer": tokenizer,
        "torch": torch,
        "device": device,
        "details": details,
    }
    _LOADED_ARCHITECTURE = native_details["architecture"]
    return model, tokenizer, torch, device, details

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
        model, tokenizer, torch, device, details = _load_local_model(model_path, adapter_path)
        context_cap = max(2, min(model.config.max_position_embeddings, _MAX_INPUT_TOKENS + max_new_tokens))
        effective_max_new_tokens = min(max_new_tokens, context_cap - 1)
        input_limit = max(1, min(_MAX_INPUT_TOKENS, context_cap - effective_max_new_tokens))
        try:
            encoded = tokenizer.encode(prompt, add_special_tokens=False)
            prompt_ids = list(encoded.ids)
        except Exception:
            raise ValueError("Prompt could not be tokenized by the local tokenizer.json.") from None
        if not prompt_ids:
            raise ValueError("Prompt tokenization returned no tokens.")
        bos_id = model.config.bos_token_id
        if details.get("add_bos_token") and bos_id is not None and prompt_ids[0] != bos_id:
            prompt_ids.insert(0, bos_id)
        if len(prompt_ids) > input_limit:
            prompt_ids = prompt_ids[-input_limit:]
            if details.get("add_bos_token") and bos_id is not None and prompt_ids:
                prompt_ids[0] = bos_id
        effective_max_new_tokens = min(effective_max_new_tokens, max(1, context_cap - len(prompt_ids)))
        started = time.perf_counter()
        try:
            with torch.inference_mode():
                generated_ids = model.generate(
                    prompt_ids,
                    max_new_tokens=effective_max_new_tokens,
                    temperature=temperature,
                    top_p=0.9,
                    eos_token_ids=model.config.eos_token_ids,
                )
            response = tokenizer.decode(generated_ids, skip_special_tokens=True)[:100_000]
        except ValueError:
            raise
        except Exception:
            _LOG.debug("AXIOM Native Engine token generation failed.", exc_info=True)
            raise AxiomEngineError(
                "AXIOM Native Engine generation failed. The prompt/context may exceed memory, "
                "or the checkpoint may be incompatible with the implemented architecture."
            ) from None
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        return {
            "engine": "axiom-native-engine",
            "execution_backend": "pytorch-native-axiom",
            "transformers_generation_used": False,
            "ollama_used": False,
            "model": details["model_directory_name"] or "local-model",
            "architecture": details["architecture"],
            "model_type": details["model_type"],
            "adapter": details["adapter_directory_name"],
            "device": str(device),
            "checkpoint_format": "safetensors",
            "decoder": model.last_generation.get("decoder", "axiom-autoregressive-kv-cache"),
            "response": response,
            "prompt_tokens": model.last_generation.get("prompt_tokens", len(prompt_ids)),
            "completion_tokens": model.last_generation.get("completion_tokens", len(generated_ids)),
            "elapsed_ms": elapsed_ms,
            "generated_at": datetime.now(UTC).isoformat(),
            "local_only": True,
        }
