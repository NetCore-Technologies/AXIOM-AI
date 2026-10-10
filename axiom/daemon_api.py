"""Read-only workspace API used by the AXIOM daemon and its web UI.

Every route is a pure inspection or planning call. Paths supplied by a client
must resolve inside the daemon's working directory; nothing here writes files.
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
from axiom.models.inspector import inspect_model
from axiom.models.registry import ModelRegistry
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
    if not raw or not raw.strip():
        raise WorkspacePathError("path is required")
    if "\x00" in raw:
        raise WorkspacePathError("path contains an invalid character")
    if len(raw) > 4096:
        raise WorkspacePathError("path is too long")
    if any(ord(char) < 32 or ord(char) == 127 for char in raw):
        raise WorkspacePathError("path contains a control character")
    base = (Path.cwd() if root is None else root).resolve()
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = base / candidate
    resolved = candidate.resolve()
    if not resolved.is_relative_to(base):
        raise WorkspacePathError("path must stay inside the working directory")
    return resolved


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix() or "."


def _walk(root: Path, max_depth: int):
    root_depth = len(root.parts)
    for current, directories, files in os.walk(root):
        directories[:] = sorted(
            name for name in directories if name not in SKIPPED_DIRECTORIES
        )
        if len(Path(current).parts) - root_depth >= max_depth:
            directories[:] = []
        yield Path(current), sorted(files)


def list_workspace_files(kind: str) -> dict[str, Any]:
    root = Path.cwd().resolve()
    found: list[dict[str, str]] = []
    if kind == "models":
        for current, files in _walk(root, 4):
            is_model = any(name in MODEL_MARKERS for name in files) or any(
                name.lower().endswith(MODEL_SUFFIXES) for name in files
            )
            if is_model and current != root:
                found.append({"path": _relative(current, root)})
            if len(found) >= MAX_LISTED_FILES:
                break
    elif kind == "datasets":
        for current, files in _walk(root, 5):
            for name in files:
                if name.lower().endswith(".jsonl"):
                    found.append({"path": _relative(current / name, root)})
            if len(found) >= MAX_LISTED_FILES:
                break
    else:
        raise ValueError("kind must be models or datasets")
    return {"kind": kind, "root": str(root), "items": found[:MAX_LISTED_FILES]}


def _jsonable(value: Any) -> Any:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {k: _jsonable(v) for k, v in dataclasses.asdict(value).items()}
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    return value


def _first(query: dict[str, list[str]], name: str, default: str = "") -> str:
    values = query.get(name)
    return values[0] if values else default


def _error(status: HTTPStatus, code: str, message: str) -> Response:
    return status, {"error": code, "message": message}


def route(path: str, query: dict[str, list[str]]) -> Response | None:
    """Return a response for a workspace API path, or None if not handled."""

    try:
        if path == "/api/models":
            registry = ModelRegistry(create=False)
            models = [model.to_dict() for model in registry.list()]
            return HTTPStatus.OK, {"name": "AXIOM", "models": models}

        if path == "/api/files":
            return HTTPStatus.OK, list_workspace_files(_first(query, "kind"))

        if path == "/api/model/inspect":
            target = resolve_in_workspace(_first(query, "path"))
            return HTTPStatus.OK, {"inspection": _jsonable(inspect_model(str(target)))}

        if path == "/api/dataset/inspect":
            target = resolve_in_workspace(_first(query, "path"))
            inspection = inspect_dataset(str(target))
            return HTTPStatus.OK, {"inspection": _jsonable(vars(inspection))}

        if path == "/api/train/plan":
            try:
                params = float(_first(query, "params"))
            except ValueError:
                return _error(
                    HTTPStatus.BAD_REQUEST, "invalid_params", "params must be a number"
                )
            if not math.isfinite(params):
                return _error(
                    HTTPStatus.BAD_REQUEST, "invalid_params", "params must be finite"
                )
            plan = create_training_plan(
                params, detect_hardware(), _first(query, "method", "auto")
            )
            return HTTPStatus.OK, {"plan": _jsonable(plan)}

        if path == "/api/ai/plan":
            model = _first(query, "model").strip()
            if not model or len(model) > 300:
                return _error(
                    HTTPStatus.BAD_REQUEST, "invalid_model", "model is required"
                )
            try:
                target_tps = float(_first(query, "target_tps", "10"))
            except ValueError:
                return _error(
                    HTTPStatus.BAD_REQUEST, "invalid_target", "target_tps must be a number"
                )
            if not math.isfinite(target_tps) or target_tps <= 0:
                return _error(
                    HTTPStatus.BAD_REQUEST, "invalid_target", "target_tps must be positive"
                )
            try:
                model = str(resolve_in_workspace(model))
            except WorkspacePathError as exc:
                return _error(HTTPStatus.BAD_REQUEST, "invalid_path", str(exc))
            result = plan_optimization(
                model=model,
                agent_type=_first(query, "agent_type", "general-agent"),
                use_case=_first(query, "use_case", "assistant"),
                privacy=_first(query, "privacy", "local"),
                latency=_first(query, "latency", "low"),
                target_tokens_per_second=target_tps,
                quantization=_first(query, "quantization", "auto"),
            )
            return HTTPStatus.OK, {"plan": _jsonable(result)}

        if path == "/api/headroom":
            return HTTPStatus.OK, {"headroom": headroom_status()}

    except WorkspacePathError as exc:
        return _error(HTTPStatus.BAD_REQUEST, "invalid_path", str(exc))
    except FileNotFoundError as exc:
        return _error(HTTPStatus.NOT_FOUND, "not_found", str(exc))
    except (ValueError, TypeError, OSError) as exc:
        return _error(HTTPStatus.UNPROCESSABLE_ENTITY, "invalid_request", str(exc))

    return None


API_PATHS: tuple[str, ...] = (
    "/api/models",
    "/api/files",
    "/api/model/inspect",
    "/api/dataset/inspect",
    "/api/train/plan",
    "/api/ai/plan",
    "/api/headroom",
)
