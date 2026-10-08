"""Trusted filesystem boundaries for model inspection and optimization."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

_MODEL_ROOT_NAMES = ("models", ".axiom/models")
_OUTPUT_ROOT_NAMES = ("optimized", ".axiom/optimized")


def _trusted_roots(names: Iterable[str]) -> tuple[Path, ...]:
    base = Path.cwd().resolve()
    return tuple((base / name).resolve() for name in names)


def _validated(candidate: str | os.PathLike[str], roots: Iterable[Path]) -> Path:
    raw = os.fspath(candidate)
    if "\x00" in raw:
        raise ValueError("path contains a NUL byte")
    # The input is normalized and then constrained to a fixed trusted root.
    resolved = Path(os.path.realpath(os.path.abspath(raw)))  # codeql[py/path-injection]
    for root in roots:
        trusted = Path(os.path.realpath(os.fspath(root)))  # codeql[py/path-injection]
        try:
            resolved.relative_to(trusted)
            return resolved
        except ValueError:
            continue
    raise ValueError("path is outside an AXIOM trusted filesystem boundary")


def validate_model_path(candidate: str | os.PathLike[str]) -> Path:
    """Return a resolved model path confined to an approved model root."""
    return _validated(candidate, _trusted_roots(_MODEL_ROOT_NAMES))


def validate_output_path(candidate: str | os.PathLike[str]) -> Path:
    """Return a resolved output path confined to an approved optimization root."""
    return _validated(candidate, _trusted_roots(_OUTPUT_ROOT_NAMES))


def validate_child_path(root: str | os.PathLike[str], child: str | os.PathLike[str]) -> Path:
    """Return a child path that remains below an already-trusted root."""
    trusted_root = Path(os.path.realpath(os.path.abspath(os.fspath(root))))
    candidate = trusted_root / os.fspath(child)
    resolved = Path(os.path.realpath(os.path.abspath(os.fspath(candidate))))  # codeql[py/path-injection]
    try:
        resolved.relative_to(trusted_root)
    except ValueError as exc:
        raise ValueError("child path escapes its trusted root") from exc
    return resolved
