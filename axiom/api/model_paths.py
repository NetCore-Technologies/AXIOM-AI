"""Trusted filesystem boundaries for model-related operations."""
from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path

_MODEL_ROOT_NAMES = ("models", ".axiom/models")
_OUTPUT_ROOT_NAMES = ("optimized", ".axiom/optimized")

def _trusted_roots(names: Iterable[str]) -> tuple[Path, ...]:
    base = Path.cwd().resolve()
    return tuple((base / name).resolve() for name in names)

def allowed_model_roots() -> tuple[Path, ...]:
    return _trusted_roots(_MODEL_ROOT_NAMES)

def allowed_output_roots() -> tuple[Path, ...]:
    return _trusted_roots(_OUTPUT_ROOT_NAMES)

def _within(candidate: Path, roots: Iterable[Path]) -> bool:
    candidate = candidate.resolve()
    for root in roots:
        try:
            candidate.relative_to(root.resolve())
            return True
        except ValueError:
            pass
    return False

def validate_model_path(value: str | os.PathLike[str]) -> Path:
    candidate = Path(value).resolve()
    if not _within(candidate, allowed_model_roots()):
        raise ValueError("model path is outside an AXIOM trusted model root")
    return candidate

def validate_output_path(value: str | os.PathLike[str]) -> Path:
    candidate = Path(value).resolve()
    if not _within(candidate, allowed_output_roots()):
        raise ValueError("output path is outside an AXIOM trusted output root")
    return candidate

def validate_child_path(root: Path, child: str | os.PathLike[str]) -> Path:
    root = root.resolve()
    candidate = (root / child).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("child path escapes the trusted root") from exc
    return candidate
