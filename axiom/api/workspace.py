from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from axiom.core.hardware import detect_hardware
from axiom.models.registry import ModelRegistry
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
    root = (Path.cwd() / "data").resolve()
    candidate = root if not path else (root / path).resolve()
    if candidate != root and root not in candidate.parents:
        raise HTTPException(status_code=400, detail="Dataset path must stay inside the data directory")
    if not candidate.exists():
        return {"datasets": []}
    datasets = (
        [{"path": str(item.relative_to(root)), "size_bytes": item.stat().st_size}
         for item in candidate.rglob("*.jsonl") if item.is_file()]
        if candidate.is_dir()
        else [{"path": str(candidate.relative_to(root)), "size_bytes": candidate.stat().st_size}]
    )
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
