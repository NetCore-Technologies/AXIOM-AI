from __future__ import annotations

import os
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from axiom.core.hardware import detect_hardware
from axiom.datasets.profiler import profile_jsonl_stream
from axiom.models.registry import ModelRegistry
from axiom.path_safety import (
    DEFAULT_SKIP_DIRECTORIES,
    SafePathError,
    find_existing_relative_path,
    open_regular_file,
)
from axiom.training.planner import create_training_plan

router = APIRouter(prefix="/api/workspace", tags=["workspace"])
_events: deque[dict[str, Any]] = deque(maxlen=100)
_events_lock = Lock()
_allowed_actions = {
    "dashboard.module_details",
    "models.add",
    "models.refresh",
    "datasets.import",
    "datasets.refresh",
    "training.new_plan",
    "evaluation.run",
    "runtime.connect",
    "runtime.explain_empty",
    "mcp.add_server",
    "mcp.inspect",
    "mcp.check_contract",
    "logs.filter",
    "logs.explain_empty",
    "settings.integration_note",
}


class WorkspaceAction(BaseModel):
    action: str = Field(min_length=1, max_length=64)
    detail: str | None = Field(default=None, max_length=500)


@router.post("/actions")
def record_action(request: WorkspaceAction) -> dict[str, Any]:
    if request.action not in _allowed_actions:
        raise HTTPException(status_code=400, detail="Unsupported workspace action")

    event = {
        "action": request.action,
        "detail": request.detail,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    with _events_lock:
        _events.appendleft(event)
    return {"status": "accepted", "event": event}


@router.get("/events")
def workspace_events() -> dict[str, list[dict[str, Any]]]:
    with _events_lock:
        return {"events": list(_events)}


@router.get("/models")
def workspace_models() -> dict[str, list[dict[str, Any]]]:
    return {"models": [model.to_dict() for model in ModelRegistry().list()]}


@router.get("/datasets")
def workspace_datasets(path: str | None = Query(default=None, max_length=512)) -> dict[str, Any]:
    """List JSONL datasets beneath the workspace data directory."""
    workspace_root = Path.cwd().resolve()
    data_entry = workspace_root / "data"
    if data_entry.is_symlink():
        raise HTTPException(status_code=400, detail="The data directory must not be a symlink.")
    try:
        root = data_entry.resolve(strict=True)
    except FileNotFoundError:
        return {"datasets": []}
    if not root.is_dir() or not root.is_relative_to(workspace_root):
        raise HTTPException(status_code=400, detail="Invalid data directory.")

    candidate = root
    if path:
        relative = path
        while relative.startswith("./"):
            relative = relative[2:]
        if relative == "data":
            relative = ""
        elif relative.startswith("data/"):
            relative = relative[5:]

        if relative:
            try:
                candidate = find_existing_relative_path(
                    root, relative, skip_directories=DEFAULT_SKIP_DIRECTORIES
                )
            except SafePathError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            except FileNotFoundError:
                return {"datasets": []}

    datasets: list[dict[str, Any]] = []
    if candidate.is_file():
        datasets.append({
            "path": candidate.relative_to(root).as_posix(),
            "size_bytes": candidate.stat().st_size,
        })
    elif candidate.is_dir():
        for current, directories, filenames in os.walk(candidate, followlinks=False):
            current_path = Path(current)
            directories[:] = sorted(
                name for name in directories
                if name not in DEFAULT_SKIP_DIRECTORIES
                and not (current_path / name).is_symlink()
            )
            for name in sorted(filenames):
                if not name.lower().endswith(".jsonl"):
                    continue
                item = current_path / name
                if item.is_symlink():
                    continue
                try:
                    resolved = item.resolve(strict=True)
                    if not resolved.is_relative_to(root) or not resolved.is_file():
                        continue
                    size = resolved.stat().st_size
                    relative_name = resolved.relative_to(root).as_posix()
                except (OSError, RuntimeError, ValueError):
                    continue
                datasets.append({"path": relative_name, "size_bytes": size})
                if len(datasets) >= 500:
                    break
            if len(datasets) >= 500:
                break

    return {"datasets": datasets[:500]}
@router.post("/training-plan")
def workspace_training_plan(
    parameter_billions: float = 7.0,
    method: str = "auto",
) -> dict[str, Any]:
    plan = create_training_plan(parameter_billions, detect_hardware(), method)
    return {"plan": plan.__dict__}


@router.get("/runtime")
def workspace_runtime() -> dict[str, Any]:
    hardware = detect_hardware()
    return {"status": "offline", "hardware": hardware.__dict__}

@router.get("/dataset-profile")
def workspace_dataset_profile(
    path: str = Query(..., min_length=1, max_length=512),
) -> dict[str, Any]:
    """Profile a JSONL file selected from the local data directory."""
    workspace_root = Path.cwd().resolve()
    data_entry = workspace_root / "data"
    if data_entry.is_symlink():
        raise HTTPException(status_code=400, detail="The data directory must not be a symlink.")
    try:
        root = data_entry.resolve(strict=True)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Dataset file not found.") from exc
    if not root.is_dir() or not root.is_relative_to(workspace_root):
        raise HTTPException(status_code=400, detail="Invalid data directory.")

    relative = path
    while relative.startswith("./"):
        relative = relative[2:]
    if relative.startswith("data/"):
        relative = relative[5:]

    if not relative or not relative.rpartition("/")[2].lower().endswith(".jsonl"):
        raise HTTPException(status_code=422, detail="Only .jsonl files are supported.")

    try:
        candidate = find_existing_relative_path(
            root,
            relative,
            allow_directories=False,
            skip_directories=DEFAULT_SKIP_DIRECTORIES,
        )
    except SafePathError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Dataset file not found.") from exc

    try:
        with open_regular_file(candidate) as stream:
            size = os.fstat(stream.fileno()).st_size
            report = profile_jsonl_stream(
                stream,
                file_name=candidate.name,
                file_size_bytes=size,
            )
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Dataset could not be profiled.") from exc

    return {"profile": report}
