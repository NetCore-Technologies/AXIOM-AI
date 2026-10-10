
"""Read-only workspace API used by the AXIOM daemon and web UI.

Routes provide local inspection, profiling, and planning. Client-supplied
paths must resolve inside the daemon's working directory.
"""

from __future__ import annotations

import dataclasses
import math
import os
from http import HTTPStatus
from pathlib import Path
from typing import Any

from axiom.api.optimization import plan_optimization
from axiom.cli.headroom import status_payload as headroom_status
from axiom.core.hardware import detect_hardware
from axiom.datasets.inspector import inspect_dataset
from axiom.datasets.profiler import profile_jsonl
from axiom.models.inspector import inspect_model
from axiom.models.registry import ModelRegistry
from axiom.path_safety import SafePathError, find_existing_relative_path
from axiom.training.planner import create_training_plan

Response = tuple[HTTPStatus, dict[str, Any]]

SKIPPED_DIRECTORIES = frozenset(
    {".git", ".venv", "node_modules", "__pycache__", "dist", "build", ".axiom"}
)
MAX_LISTED_FILES = 200
MODEL_MARKERS = ("config.json",)
MODEL_SUFFIXES = (".gguf", ".safetensors")


class WorkspacePathError(ValueError):
    """Raised when a client path is missing or escapes the workspace."""


def resolve_in_workspace(raw: str, root: Path | None = None) -> Path:
    """Resolve an existing workspace entry through a trusted directory listing."""
    base = (Path.cwd() if root is None else root).resolve()
    try:
        return find_existing_relative_path(
            base,
            raw,
            skip_directories=SKIPPED_DIRECTORIES,
        )
    except SafePathError as exc:
        raise WorkspacePathError(str(exc)) from exc


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix() or "."


def _walk(root: Path, max_depth: int):
    root_depth = len(root.parts)

    for current, directories, files in os.walk(root, followlinks=False):
        # Do not traverse symlinked directories.
        current_path = Path(current)
        directories[:] = sorted(
            name
            for name in directories
            if name not in SKIPPED_DIRECTORIES
            and not (current_path / name).is_symlink()
        )

        if len(current_path.parts) - root_depth >= max_depth:
            directories[:] = []

        yield current_path, sorted(files)


def list_workspace_files(kind: str) -> dict[str, Any]:
    """List a bounded number of local model or JSONL dataset paths."""
    root = Path.cwd().resolve()
    found: list[dict[str, str]] = []

    if kind == "models":
        for current, files in _walk(root, 4):
            is_model = any(
                name in files for name in MODEL_MARKERS
            ) or any(
                name.lower().endswith(MODEL_SUFFIXES)
                for name in files
            )

            if is_model and current != root:
                found.append({"path": _relative(current, root)})

            if len(found) >= MAX_LISTED_FILES:
                break

    elif kind == "datasets":
        for current, files in _walk(root, 5):
            for name in files:
                if not name.lower().endswith(".jsonl"):
                    continue

                candidate = current / name

                # Avoid listing file symlinks.
                if candidate.is_symlink():
                    continue

                found.append(
                    {"path": _relative(candidate, root)}
                )

                if len(found) >= MAX_LISTED_FILES:
                    break

            if len(found) >= MAX_LISTED_FILES:
                break

    else:
        raise ValueError("kind must be models or datasets")

    return {
        "kind": kind,
        "root": str(root),
        "items": found[:MAX_LISTED_FILES],
    }


def _jsonable(value: Any) -> Any:
    """Convert supported Python objects into JSON-compatible values."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {
            key: _jsonable(item)
            for key, item in dataclasses.asdict(value).items()
        }

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, dict):
        return {
            str(key): _jsonable(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]

    return value


def _first(
    query: dict[str, list[str]],
    name: str,
    default: str = "",
) -> str:
    values = query.get(name)
    return values[0] if values else default


def _error(
    status: HTTPStatus,
    code: str,
    message: str,
) -> Response:
    return status, {"error": code, "message": message}


def route(
    path: str,
    query: dict[str, list[str]],
) -> Response | None:
    """Return an API response, or None when the path is not handled."""

    try:
        if path == "/api/models":
            registry = ModelRegistry(create=False)
            models = [
                model.to_dict()
                for model in registry.list()
            ]
            return HTTPStatus.OK, {
                "name": "AXIOM",
                "models": models,
            }

        if path == "/api/files":
            return HTTPStatus.OK, list_workspace_files(
                _first(query, "kind")
            )

        if path == "/api/model/inspect":
            target = resolve_in_workspace(
                _first(query, "path")
            )

            if not target.exists():
                return _error(
                    HTTPStatus.NOT_FOUND,
                    "not_found",
                    "Requested model path was not found.",
                )

            if not target.is_dir():
                return _error(
                    HTTPStatus.UNPROCESSABLE_ENTITY,
                    "invalid_model_path",
                    "Model path must refer to a directory.",
                )

            return HTTPStatus.OK, {
                "inspection": _jsonable(
                    inspect_model(str(target))
                )
            }

        if path == "/api/dataset/inspect":
            target = resolve_in_workspace(
                _first(query, "path")
            )

            if not target.exists():
                return _error(
                    HTTPStatus.NOT_FOUND,
                    "not_found",
                    "Requested dataset path was not found.",
                )

            if not target.is_file():
                return _error(
                    HTTPStatus.UNPROCESSABLE_ENTITY,
                    "invalid_dataset_path",
                    "Dataset path must refer to a file.",
                )

            inspection = inspect_dataset(str(target))

            return HTTPStatus.OK, {
                "inspection": _jsonable(vars(inspection))
            }

        # NEW: bounded JSONL dataset profiling.
        if path == "/api/dataset/profile":
            target = resolve_in_workspace(
                _first(query, "path")
            )

            if target.suffix.lower() != ".jsonl":
                return _error(
                    HTTPStatus.UNPROCESSABLE_ENTITY,
                    "unsupported_format",
                    "Dataset profiling currently supports .jsonl files.",
                )

            if not target.is_file():
                return _error(
                    HTTPStatus.NOT_FOUND,
                    "not_found",
                    "Dataset file not found.",
                )

            report = profile_jsonl(target)

            return HTTPStatus.OK, {
                "profile": report,
            }

        if path == "/api/train/plan":
            try:
                params = float(_first(query, "params"))
            except ValueError:
                return _error(
                    HTTPStatus.BAD_REQUEST,
                    "invalid_params",
                    "params must be a number",
                )

            if not math.isfinite(params):
                return _error(
                    HTTPStatus.BAD_REQUEST,
                    "invalid_params",
                    "params must be finite",
                )

            plan = create_training_plan(
                params,
                detect_hardware(),
                _first(query, "method", "auto"),
            )

            return HTTPStatus.OK, {
                "plan": _jsonable(plan),
            }

        if path == "/api/ai/plan":
            model = _first(query, "model").strip()

            if not model or len(model) > 300:
                return _error(
                    HTTPStatus.BAD_REQUEST,
                    "invalid_model",
                    "model is required and must be at most 300 characters",
                )

            try:
                target_tps = float(
                    _first(query, "target_tps", "10")
                )
            except ValueError:
                return _error(
                    HTTPStatus.BAD_REQUEST,
                    "invalid_target",
                    "target_tps must be a number",
                )

            if (
                not math.isfinite(target_tps)
                or target_tps <= 0
            ):
                return _error(
                    HTTPStatus.BAD_REQUEST,
                    "invalid_target",
                    "target_tps must be positive",
                )

            try:
                model = str(resolve_in_workspace(model))
            except FileNotFoundError:
                # A remote model ID is an identifier, not a filesystem path.
                parts = model.split("/")
                valid_model_id = (
                    not model.startswith("/")
                    and "\\" not in model
                    and all(part not in ("", ".", "..") for part in parts)
                    and all(
                        char.isalnum() or char in "._-"
                        for char in model
                    )
                )
                if not valid_model_id:
                    return _error(
                        HTTPStatus.BAD_REQUEST,
                        "invalid_model",
                        "Use a valid model identifier or an existing workspace path.",
                    )
            except WorkspacePathError as exc:
                return _error(
                    HTTPStatus.BAD_REQUEST,
                    "invalid_path",
                    str(exc),
                )

            result = plan_optimization(
                model=model,
                agent_type=_first(
                    query, "agent_type", "general-agent"
                ),
                use_case=_first(
                    query, "use_case", "assistant"
                ),
                privacy=_first(query, "privacy", "local"),
                latency=_first(query, "latency", "low"),
                target_tokens_per_second=target_tps,
                quantization=_first(
                    query, "quantization", "auto"
                ),
            )

            return HTTPStatus.OK, {
                "plan": _jsonable(result),
            }

        if path == "/api/headroom":
            return HTTPStatus.OK, {
                "headroom": headroom_status(),
            }

    except WorkspacePathError as exc:
        return _error(
            HTTPStatus.BAD_REQUEST,
            "invalid_path",
            str(exc),
        )

    except FileNotFoundError:
        return _error(
            HTTPStatus.NOT_FOUND,
            "not_found",
            "Requested file or directory was not found.",
        )

    except (ValueError, TypeError, OSError) as exc:
        return _error(
            HTTPStatus.UNPROCESSABLE_ENTITY,
            "invalid_request",
            str(exc),
        )

    return None


API_PATHS: tuple[str, ...] = (
    "/api/models",
    "/api/files",
    "/api/model/inspect",
    "/api/dataset/inspect",
    "/api/dataset/profile",
    "/api/train/plan",
    "/api/ai/plan",
    "/api/headroom",
)
