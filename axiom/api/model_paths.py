from __future__ import annotations

import os
from pathlib import Path


class UnsafeModelPath(ValueError):
    """Raised when a model path escapes an approved AXIOM root."""


def allowed_model_roots() -> tuple[str, ...]:
    values: list[str] = []

    configured = os.environ.get("AXIOM_MODEL_ROOTS", "")
    for raw in configured.split(os.pathsep):
        raw = raw.strip()
        if raw:
            values.append(os.path.realpath(os.path.expanduser(raw)))

    values.append(os.path.realpath(os.path.join(os.getcwd(), ".axiom", "models")))
    values.append(os.path.realpath(os.getcwd()))

    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)

    return tuple(result)


def validate_model_path(value: str) -> Path:
    if not value or len(value) > 4096:
        raise UnsafeModelPath("Invalid model path.")

    candidate = os.path.realpath(os.path.expanduser(value))

    for root in allowed_model_roots():
        try:
            common = os.path.commonpath((root, candidate))
        except ValueError as exc:
            raise UnsafeModelPath("Invalid model path.") from exc

        if common == root:
            return Path(candidate)

    raise UnsafeModelPath(
        "Model path is outside an approved AXIOM model root. "
        "Set AXIOM_MODEL_ROOTS to allow another model directory."
    )
