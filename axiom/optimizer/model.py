from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from axiom.api.model_paths import validate_model_path, validate_output_path
from axiom.optimizer.agent_profiles import AgentProfile
from axiom.optimizer.system import SystemInfo


@dataclass(frozen=True)
class ModelInfo:
    source: str
    local_path: str
    parameter_billions: float
    estimated_fp16_gb: float
    files: int
    weights: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "local_path": self.local_path,
            "parameter_billions": round(self.parameter_billions, 3),
            "estimated_fp16_gb": round(self.estimated_fp16_gb, 2),
            "files": self.files,
            "weights": self.weights,
        }


RUNTIME_KEEP_NAMES = {
    "config.json",
    "generation_config.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "preprocessor_config.json",
    "processor_config.json",
    "chat_template.json",
    "added_tokens.json",
    "merges.txt",
    "vocab.json",
    "spiece.model",
    "tokenizer.model",
}

RUNTIME_EXTENSIONS = {
    ".safetensors",
    ".bin",
    ".gguf",
    ".json",
    ".model",
    ".txt",
}


def _trusted_files(root: Path) -> tuple[Path, ...]:
    resolved_root = root.resolve()
    files: list[Path] = []
    for path in root.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        resolved_path = path.resolve(strict=True)
        try:
            resolved_path.relative_to(resolved_root)
        except ValueError as exc:
            raise ValueError(
                f"model path escapes the trusted model root: {path}"
            ) from exc
        files.append(path)
    return tuple(files)


def _copy_without_following_symlinks(source: Path, destination: Path) -> None:
    source_fd = os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        destination_fd = os.open(
            destination,
            os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        try:
            with (
                os.fdopen(source_fd, "rb") as source_handle,
                os.fdopen(destination_fd, "wb") as destination_handle,
            ):
                source_fd = destination_fd = -1
                shutil.copyfileobj(source_handle, destination_handle)
        finally:
            if destination_fd >= 0:
                os.close(destination_fd)
    finally:
        if source_fd >= 0:
            os.close(source_fd)


def _config(path: Path) -> dict[str, Any]:
    for name in ("config.json", "model_config.json"):
        cfg = path / name
        if cfg.is_symlink():
            raise ValueError(
                f"model configuration contains an unsupported symlink: {cfg}"
            )
        # codeql[py/path-injection]
        if cfg.exists():
            try:
                # codeql[py/path-injection]
                value = json.loads(cfg.read_text(encoding="utf-8"))
                if isinstance(value, dict):
                    return value
            except (OSError, ValueError):
                import logging as _axiom_logging

                _axiom_logging.getLogger(__name__).debug(
                    "intentionally ignored exception", exc_info=True
                )
    return {}


def inspect_model(source: str) -> ModelInfo:
    path = validate_model_path(source)

    # codeql[py/path-injection]
    if not path.exists():
        return ModelInfo(
            source=source,
            local_path="",
            parameter_billions=0.0,
            estimated_fp16_gb=0.0,
            files=0,
            weights=[],
        )

    # codeql[py/path-injection]
    root = path if path.is_dir() else path.parent
    cfg = _config(root)

    params = cfg.get("num_parameters")
    if params is None:
        hidden = int(cfg.get("hidden_size") or 4096)
        layers = int(cfg.get("num_hidden_layers") or 32)
        params_b = max(
            1.0,
            hidden * hidden * layers * 12 / 1_000_000_000,
        )
    else:
        params_b = float(params) / 1_000_000_000

    weights = [
        str(p.relative_to(root))
        # codeql[py/path-injection]
        for p in _trusted_files(root)
        if p.is_file() and p.suffix.lower() in {".safetensors", ".bin", ".gguf"}
    ]

    # codeql[py/path-injection]
    count = len(_trusted_files(root))

    return ModelInfo(
        source=source,
        local_path=str(root),
        parameter_billions=params_b,
        estimated_fp16_gb=params_b * 2.0,
        files=count,
        weights=weights,
    )


def choose_quantization(
    model: ModelInfo,
    system: SystemInfo,
    profile: AgentProfile,
) -> str:
    usable = system.vram_gb if system.gpu_available else system.ram_gb * 0.55

    if usable <= 0:
        return profile.preferred_quantization

    # Conservative memory budget.
    if model.estimated_fp16_gb <= usable * 0.75:
        return "int8"

    if model.estimated_fp16_gb <= usable * 1.35:
        return "int4"

    return "int4"


def create_runtime_bundle(
    source: str,
    destination: str,
) -> dict[str, Any]:
    src = validate_model_path(source)
    dst = validate_output_path(destination)

    # codeql[py/path-injection]
    if not src.exists():
        raise FileNotFoundError(source)

    # codeql[py/path-injection]
    dst_root = dst.resolve()
    dst.mkdir(parents=True, exist_ok=True)

    root = src if src.is_dir() else src.parent
    root = root.resolve()

    copied: list[str] = []
    skipped: list[str] = []

    for item in root.rglob("*"):
        if item.is_symlink():
            raise ValueError(
                f"runtime bundle source contains an unsupported symlink: {item}"
            )
        if not item.is_file():
            continue

        resolved_item = item.resolve(strict=True)
        try:
            resolved_item.relative_to(root)
        except ValueError as exc:
            raise ValueError(
                f"runtime bundle source escapes the trusted model root: {item}"
            ) from exc

        rel = item.relative_to(root)
        name = item.name.lower()
        suffix = item.suffix.lower()

        # Keep inference-critical files and model weights.
        keep = name in RUNTIME_KEEP_NAMES or suffix in {".safetensors", ".bin", ".gguf"}

        # Drop obvious repository-only material such as docs/training/
        # source/test files from the runtime bundle.
        if not keep:
            skipped.append(str(rel))
            continue

        target = dst / rel
        resolved_target = target.resolve(strict=False)
        try:
            resolved_target.relative_to(dst_root)
        except ValueError as exc:
            raise ValueError(
                f"runtime bundle destination escapes the trusted output root: {target}"
            ) from exc
        if target.is_symlink():
            raise ValueError(
                f"runtime bundle destination contains an unsupported symlink: {target}"
            )

        target.parent.mkdir(parents=True, exist_ok=True)
        _copy_without_following_symlinks(item, target)
        copied.append(str(rel))

    return {
        "source": str(root),
        "destination": str(dst),
        "copied": copied,
        "skipped_non_runtime": skipped,
    }


def write_runtime_profile(
    bundle: str,
    profile: AgentProfile,
    quantization: str,
    system: SystemInfo,
) -> Path:
    path = Path(validate_output_path(bundle)) / "axiom-runtime.json"
    resolved_path = path.resolve(strict=False)
    try:
        resolved_path.relative_to(Path(validate_output_path(bundle)).resolve())
    except ValueError as exc:
        raise ValueError(
            "runtime profile path escapes the trusted output root"
        ) from exc
    if path.is_symlink():
        raise ValueError("runtime profile destination cannot be a symlink")

    data = {
        "agent_profile": profile.key,
        "agent_profile_number": profile.number,
        "agent_name": profile.name,
        "context_tokens": profile.context_tokens,
        "temperature": profile.temperature,
        "quantization_target": quantization,
        "system": system.to_dict(),
        "target_tokens_per_second": 10.0,
        "throughput_status": "benchmark_required",
        "note": (
            "AXIOM will only report 10 tok/s as achieved after a real "
            "benchmark confirms it on this device."
        ),
    }

    path.write_text(
        json.dumps(data, indent=2),
        encoding="utf-8",
    )

    return path
