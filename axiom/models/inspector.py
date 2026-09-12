from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ModelInspection:
    path: Path
    architecture: str | None
    model_type: str | None
    parameter_count: int | None
    model_format: str
    weight_size_bytes: int
    has_config: bool
    has_tokenizer: bool
    has_safetensors: bool
    has_gguf: bool
    has_pytorch_weights: bool
    capabilities: list[str]
    estimated_vram_gb: float | None
    status: str


def _estimate_parameters(config: dict, weight_size_bytes: int) -> int | None:
    for key in ("num_parameters", "parameter_count", "n_parameters"):
        value = config.get(key)
        if isinstance(value, int):
            return value

    hidden = config.get("hidden_size")
    layers = config.get("num_hidden_layers")
    vocab = config.get("vocab_size")
    intermediate = config.get("intermediate_size")

    if all(isinstance(v, int) for v in (hidden, layers, vocab)):
        if isinstance(intermediate, int):
            return int(
                layers
                * (
                    4 * hidden * intermediate
                    + 4 * hidden * hidden
                )
                + vocab * hidden
            )

        if weight_size_bytes > 0:
            return int(weight_size_bytes)

    return None


def _detect_capabilities(config: dict) -> list[str]:
    model_type = str(config.get("model_type", "")).lower()
    architectures = [
        str(item).lower()
        for item in config.get("architectures", [])
        if isinstance(item, str)
    ]

    markers = (
        "causallm",
        "forcausallm",
        "lmhead",
        "gpt",
        "llama",
        "qwen",
        "mistral",
    )

    capabilities = []

    if any(
        marker in model_type
        or any(marker in architecture for architecture in architectures)
        for marker in markers
    ):
        capabilities.append("Text generation")

    if config.get("vision_config") or "vision" in model_type:
        capabilities.append("Vision")

    if "audio" in model_type or "speech" in model_type:
        capabilities.append("Audio")

    return capabilities or ["Unknown"]


def inspect_model(path: str) -> ModelInspection:
    model_path = Path(path)

    if not model_path.exists():
        raise FileNotFoundError(f"Model path not found: {model_path}")

    if not model_path.is_dir():
        raise ValueError(f"Model path is not a directory: {model_path}")

    config_path = model_path / "config.json"
    config = {}

    if config_path.is_file():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid config.json: {exc}") from exc

    files = [
        file
        for file in model_path.rglob("*")
        if file.is_file()
    ]

    safetensors = any(
        file.suffix.lower() == ".safetensors"
        or file.name.endswith(".safetensors.index.json")
        for file in files
    )

    gguf = any(file.suffix.lower() == ".gguf" for file in files)

    pytorch = any(
        file.suffix.lower() in {".bin", ".pt", ".pth"}
        for file in files
    )

    if gguf:
        model_format = "GGUF"
    elif safetensors:
        model_format = "Safetensors"
    elif pytorch:
        model_format = "PyTorch"
    else:
        model_format = "Unknown"

    weight_files = [
        file for file in files
        if file.suffix.lower() in {
            ".safetensors",
            ".gguf",
            ".bin",
            ".pt",
            ".pth",
        }
    ]

    weight_size = sum(file.stat().st_size for file in weight_files)

    tokenizer_files = {
        "tokenizer.json",
        "tokenizer.model",
        "tokenizer_config.json",
    }

    has_tokenizer = any(
        file.name in tokenizer_files
        for file in files
    )

    architectures = config.get("architectures")
    architecture = (
        str(architectures[0])
        if isinstance(architectures, list) and architectures
        else None
    )

    parameter_count = _estimate_parameters(
        config,
        weight_size,
    )

    estimated_vram_gb = None

    if parameter_count:
        estimated_vram_gb = round(
            parameter_count * 2 * 1.2 / (1024 ** 3),
            2,
        )

    if not config_path.is_file():
        status = "⚠ config.json not found"
    elif not weight_files:
        status = "⚠ model weights not found"
    else:
        status = "✓ Model structure detected"

    return ModelInspection(
        path=model_path,
        architecture=architecture,
        model_type=config.get("model_type"),
        parameter_count=parameter_count,
        model_format=model_format,
        weight_size_bytes=weight_size,
        has_config=config_path.is_file(),
        has_tokenizer=has_tokenizer,
        has_safetensors=safetensors,
        has_gguf=gguf,
        has_pytorch_weights=pytorch,
        capabilities=_detect_capabilities(config),
        estimated_vram_gb=estimated_vram_gb,
        status=status,
    )
