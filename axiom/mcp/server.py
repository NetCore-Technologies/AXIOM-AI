from __future__ import annotations

import os
from pathlib import Path

from mcp.server import MCPServer

from axiom.core.hardware import detect_hardware
from axiom.datasets.cleaner import clean_jsonl
from axiom.datasets.inspector import inspect_dataset
from axiom.models.inspector import inspect_model
from axiom.models.registry import ModelRegistry
from axiom.runtime.supercompress import compress_context, redacted_base_url
from axiom.training.planner import create_training_plan
from axiom.version import __version__

mcp = MCPServer(
    f"AXIOM v{__version__}",
    instructions=(
        "AXIOM is an AI engineering platform. "
        "Use AXIOM tools to inspect models, inspect and clean datasets, "
        "inspect hardware, create training plans, and check optional "
        "AI runtime integrations."
    ),
)


@mcp.tool()
def axiom_info() -> dict:
    """Return AXIOM release information."""
    return {
        "name": "AXIOM",
        "version": __version__,
        "release_channel": "beta",
        "status": "experimental",
        "capabilities": [
            "models",
            "datasets",
            "hardware",
            "training_planning",
            "supercompress",
            "mcp",
            "agent_integrations",
        ],
    }


@mcp.tool()
def axiom_model_list() -> list[dict]:
    """List models registered with AXIOM."""
    registry = ModelRegistry(create=False)

    return [model.to_dict() for model in registry.list()]


@mcp.tool()
def axiom_model_info(path: str) -> dict:
    """Inspect a local AI model directory."""
    if not isinstance(path, str) or not path.strip():
        raise ValueError("Model path cannot be empty.")

    result = inspect_model(path)

    return {
        "path": str(result.path),
        "architecture": result.architecture,
        "model_type": result.model_type,
        "parameters": result.parameter_count,
        "format": result.model_format,
        "weight_size_bytes": result.weight_size_bytes,
        "has_config": result.has_config,
        "has_tokenizer": result.has_tokenizer,
        "has_safetensors": result.has_safetensors,
        "has_gguf": result.has_gguf,
        "has_pytorch_weights": result.has_pytorch_weights,
        "capabilities": result.capabilities,
        "estimated_vram_gb": result.estimated_vram_gb,
        "status": result.status,
    }


@mcp.tool()
def axiom_dataset_inspect(path: str) -> dict:
    """Inspect an AXIOM-supported dataset."""
    if not isinstance(path, str) or not path.strip():
        raise ValueError("Dataset path cannot be empty.")

    result = inspect_dataset(path)

    return {
        "path": str(result.path),
        "format": result.format,
        "samples": result.samples,
        "valid": result.valid,
        "invalid": result.invalid,
        "empty": result.empty,
        "duplicates": result.duplicates,
        "estimated_tokens": result.estimated_tokens,
        "fields": result.fields,
    }


@mcp.tool()
def axiom_dataset_clean(
    path: str,
    output: str | None = None,
) -> dict:
    """Clean a JSONL dataset without modifying the original."""
    if not isinstance(path, str) or not path.strip():
        raise ValueError("Dataset path cannot be empty.")
    if output is not None and (not isinstance(output, str) or not output.strip()):
        raise ValueError("Output path cannot be empty.")

    source = Path(path)

    if not source.is_file():
        raise ValueError(f"Dataset not found: {source}")
    if source.suffix.lower() != ".jsonl":
        raise ValueError("Cleaning currently supports .jsonl files.")

    destination = (
        Path(output) if output else source.with_name(f"{source.stem}.cleaned.jsonl")
    )

    result = clean_jsonl(
        source,
        destination,
    )

    return {
        "source": str(result.source),
        "output": str(result.output),
        "total_lines": result.total_lines,
        "kept": result.kept,
        "removed_invalid": result.removed_invalid,
        "removed_empty": result.removed_empty,
        "removed_duplicates": result.removed_duplicates,
        "removed_schema": result.removed_schema,
    }


@mcp.tool()
def axiom_system_info() -> dict:
    """Return detected system hardware."""
    hardware = detect_hardware()

    return {
        "os": hardware.os_name,
        "architecture": hardware.architecture,
        "cpu_cores": hardware.cpu_cores,
        "ram_gb": hardware.ram_gb,
        "gpu": hardware.gpu_name,
        "vram_gb": hardware.vram_gb,
        "cuda_available": hardware.cuda_available,
    }


@mcp.tool()
def axiom_training_plan(
    parameters_billions: float,
    method: str = "auto",
) -> dict:
    """Generate a hardware-aware training plan."""
    if not isinstance(method, str) or not method.strip():
        raise ValueError("Training method cannot be empty.")

    hardware = detect_hardware()

    plan = create_training_plan(
        parameter_billions=parameters_billions,
        hardware=hardware,
        method=method.strip().lower(),
    )

    return {
        "method": plan.method,
        "precision": plan.precision,
        "lora_rank": plan.lora_rank,
        "batch_size": plan.batch_size,
        "gradient_accumulation": plan.gradient_accumulation,
        "sequence_length": plan.sequence_length,
        "learning_rate": plan.learning_rate,
        "estimated_vram_gb": plan.estimated_vram_gb,
        "fits_hardware": plan.fits_hardware,
        "reason": plan.reason,
    }


@mcp.tool()
def axiom_supercompress_status() -> dict:
    """Check whether SuperCompress is configured."""

    return {
        "configured": bool(os.getenv("SUPERCOMPRESS_API_KEY")),
        "endpoint": redacted_base_url(),
    }


@mcp.tool()
def axiom_supercompress(
    context: str,
    query: str,
    budget_ratio: float = 0.35,
    ccr: bool = False,
) -> dict:
    """Compress context through SuperCompress before inference."""
    result = compress_context(
        context,
        query,
        budget_ratio=budget_ratio,
        ccr=ccr,
    )

    return {
        "compressed_text": result.compressed_text,
        "original_tokens": result.original_tokens,
        "kept_tokens": result.kept_tokens,
        "tokens_saved": result.tokens_saved,
        "savings_pct": result.savings_pct,
        "compression_risk": result.compression_risk,
        "policy_name": result.policy_name,
        "mode": result.mode,
    }


if __name__ == "__main__":
    mcp.run()
