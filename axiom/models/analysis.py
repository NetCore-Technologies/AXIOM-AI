from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ModelAnalysis:
    repo_id: str
    architecture: str
    model_type: str
    parameter_count: int | None
    parameter_source: str
    context_length: int | None
    precision: str
    weight_size_gb: float | None
    file_count: int
    files: list[str]


def _find_number(config: dict, keys: tuple[str, ...]) -> int | None:
    for key in keys:
        value = config.get(key)
        if isinstance(value, int):
            return value
    return None


def _estimate_parameters(config: dict) -> int | None:
    direct = _find_number(
        config,
        ("num_parameters", "parameter_count", "n_parameters"),
    )

    if direct:
        return direct

    hidden = config.get("hidden_size")
    layers = config.get("num_hidden_layers")
    vocab = config.get("vocab_size")
    intermediate = config.get("intermediate_size")

    if all(isinstance(v, int) for v in (hidden, layers, vocab, intermediate)):
        return int(
            layers
            * (
                4 * hidden * intermediate
                + 4 * hidden * hidden
            )
            + vocab * hidden
        )

    return None


def analyze_config(
    repo_id: str,
    config: dict,
    files: list[str],
    weight_size_bytes: int | None = None,
) -> ModelAnalysis:

    architectures = config.get("architectures")

    architecture = (
        str(architectures[0])
        if isinstance(architectures, list) and architectures
        else "Unknown"
    )

    model_type = str(config.get("model_type") or "Unknown")

    direct_parameters = _find_number(
        config,
        ("num_parameters", "parameter_count", "n_parameters"),
    )

    parameters = direct_parameters or _estimate_parameters(config)

    parameter_source = (
        "model metadata"
        if direct_parameters
        else "architecture estimate"
        if parameters
        else "unknown"
    )

    context_length = _find_number(
        config,
        (
            "max_position_embeddings",
            "max_sequence_length",
            "seq_length",
            "model_max_length",
        ),
    )

    precision = "Unknown"

    torch_dtype = config.get("torch_dtype")

    if isinstance(torch_dtype, str):
        precision = torch_dtype

    if any(name.lower().endswith(".gguf") for name in files):
        precision = "quantized / GGUF"

    elif any(name.lower().endswith(".safetensors") for name in files):
        if precision == "Unknown":
            precision = "safetensors (dtype from config unavailable)"

    weight_size_gb = (
        round(weight_size_bytes / (1024 ** 3), 2)
        if weight_size_bytes is not None
        else None
    )

    return ModelAnalysis(
        repo_id=repo_id,
        architecture=architecture,
        model_type=model_type,
        parameter_count=parameters,
        parameter_source=parameter_source,
        context_length=context_length,
        precision=precision,
        weight_size_gb=weight_size_gb,
        file_count=len(files),
        files=files,
    )


def disk_info(path: str = ".") -> tuple[int, int]:
    usage = shutil.disk_usage(path)
    return usage.free, usage.total
