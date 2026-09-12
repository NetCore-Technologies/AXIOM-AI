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


def _estimate_parameters(config: dict) -> tuple[int | None, str]:
    direct_keys = (
        "num_parameters",
        "parameter_count",
        "n_parameters",
    )

    for key in direct_keys:
        value = config.get(key)

        if isinstance(value, int) and value > 0:
            return value, "model metadata"

    hidden = config.get("hidden_size")
    layers = config.get("num_hidden_layers")
    vocab = config.get("vocab_size")
    intermediate = config.get("intermediate_size")

    if all(
        isinstance(value, int) and value > 0
        for value in (hidden, layers, vocab, intermediate)
    ):
        estimate = int(
            layers
            * (
                4 * hidden * intermediate
                + 4 * hidden * hidden
            )
            + vocab * hidden
        )
        return estimate, "architecture estimate"

    return None, "unknown"


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

    parameters, parameter_source = _estimate_parameters(config)

    context_length = _find_number(
        config,
        (
            "max_position_embeddings",
            "max_sequence_length",
            "seq_length",
            "model_max_length",
        ),
    )

    precision = str(config.get("torch_dtype") or "Unknown")

    quantization = config.get("quantization_config")

    if isinstance(quantization, dict):
        bits = quantization.get("bits")
        method = (
            quantization.get("quant_method")
            or quantization.get("method")
            or "quantized"
        )

        if bits:
            precision = f"{method} {bits}-bit"
        else:
            precision = str(method)

    if any(name.lower().endswith(".gguf") for name in files):
        if precision == "Unknown":
            precision = "quantized / GGUF"

    elif any(name.lower().endswith(".safetensors") for name in files):
        if precision == "Unknown":
            precision = "safetensors"

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
