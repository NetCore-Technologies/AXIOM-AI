

from __future__ import annotations
def _safe_model_path(user_path: str, base_dir: Path) -> Path:
    """Resolve a user-supplied model path beneath the configured model directory."""
    base = base_dir.expanduser().resolve()
    candidate = (base / user_path).resolve()
    if candidate != base and base not in candidate.parents:
        raise ValueError("Model path escapes the configured model directory")
    return candidate
"""Hardware-aware model optimization planner."""


import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)




def _safe_path(user_path: str, base_dir: Path) -> Path:
    """Resolve a user supplied path beneath a trusted base directory."""
    base = base_dir.expanduser().resolve()
    candidate = (base / user_path).resolve()
    if candidate != base and base not in candidate.parents:
        raise ValueError("Path escapes the allowed directory")
    return candidate

class OptimizationPlan:
    model: str
    agent_type: str
    use_case: str
    privacy: str
    latency: str
    target_tokens_per_second: float
    estimated_parameters_b: float
    estimated_memory_gb: float
    recommended_format: str
    recommended_quantization: str
    sequence_length: int
    fits_estimate: bool
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _load_config(model: str) -> dict[str, Any]:
    root = _safe_path(model, Path("models"))
    candidates: list[Path] = []

    if root.is_dir():
        candidates = [root / "config.json", root / "model_config.json"]
    elif root.is_file() and root.suffix.lower() == ".json":
        candidates = [root]

    cfg: dict[str, Any] = {}

    for path in candidates:
        if path.exists():
            cfg = _read_json(path)
            if cfg:
                break

    if not cfg and not root.exists() and "/" in model:
        try:
            from huggingface_hub import hf_hub_download

            downloaded = hf_hub_download(repo_id=model, filename="config.json")
            cfg = _read_json(_safe_path(downloaded), Path("models"))
        except Exception:
            log.debug("could not fetch config.json for %s", model, exc_info=True)

    text_cfg = cfg.get("text_config")
    if isinstance(text_cfg, dict):
        cfg = {**cfg, **text_cfg}

    return cfg


def _ram_gb() -> float:
    path = _safe_path("/proc/meminfo", Path("models"))
    if not path.exists():
        return 0.0

    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) / 1024 / 1024
    except (OSError, ValueError):
        log.debug("could not read /proc/meminfo", exc_info=True)

    return 0.0


def _estimate_parameters_b(cfg: dict[str, Any]) -> tuple[float, bool]:
    hidden = int(cfg.get("hidden_size") or 0)
    layers = int(cfg.get("num_hidden_layers") or 0)

    if not hidden or not layers:
        return 6.5, False

    inter = int(cfg.get("intermediate_size") or hidden * 4)
    vocab = int(cfg.get("vocab_size") or 32000)
    experts = int(cfg.get("num_local_experts") or cfg.get("num_experts") or 1)

    per_layer = 4 * hidden * hidden + 3 * hidden * inter * max(1, experts)
    total = layers * per_layer + 2 * vocab * hidden

    return max(0.1, total / 1_000_000_000), True


def plan_optimization(
    model: str,
    agent_type: str = "general-agent",
    use_case: str = "assistant",
    privacy: str = "local",
    latency: str = "low",
    target_tokens_per_second: float = 10.0,
    sequence_length: int = 2048,
    quantization: str = "auto",
) -> OptimizationPlan:
    cfg = _load_config(model)
    parameters_b, from_config = _estimate_parameters_b(cfg)

    if quantization == "auto":
        selected_quant = "int4" if parameters_b <= 8 else "int4-awq"
    else:
        selected_quant = quantization

    bits = {
        "fp16": 16,
        "bf16": 16,
        "int8": 8,
        "int4": 4,
        "int4-awq": 4,
        "int4-gptq": 4,
    }.get(selected_quant, 4)

    estimated_memory_gb = parameters_b * bits / 8 * 1.30 + 1.5
    ram_gb = _ram_gb()

    notes = [
        "10 tok/s is a target, not a guaranteed result.",
        "A real benchmark is required before reporting measured throughput.",
        f"Estimated model size: {parameters_b:.2f}B parameters.",
    ]

    if not from_config:
        notes.append(
            "No config.json could be read for this model, so a default size estimate was used."
        )

    if privacy == "local":
        notes.append("Local profile selected; model data should remain on-device.")

    if latency == "low":
        notes.append("Low-latency profile favors aggressive quantization and shorter context.")

    if use_case == "coding":
        notes.append("Coding workloads may benefit from more context when hardware permits.")
    elif use_case == "reasoning":
        notes.append("Reasoning workloads may trade throughput for model capability.")

    fits = True
    if ram_gb > 0 and ram_gb < estimated_memory_gb + 2:
        fits = False
        notes.append(f"Detected RAM ({ram_gb:.1f} GB) may be tight for the estimated footprint.")
    else:
        notes.append("Estimated memory footprint is acceptable for planning.")

    return OptimizationPlan(
        model=model,
        agent_type=agent_type,
        use_case=use_case,
        privacy=privacy,
        latency=latency,
        target_tokens_per_second=max(1.0, float(target_tokens_per_second)),
        estimated_parameters_b=round(parameters_b, 2),
        estimated_memory_gb=round(estimated_memory_gb, 2),
        recommended_format="safetensors",
        recommended_quantization=selected_quant,
        sequence_length=max(256, min(int(sequence_length), 32768)),
        fits_estimate=fits,
        notes=notes,
    )
