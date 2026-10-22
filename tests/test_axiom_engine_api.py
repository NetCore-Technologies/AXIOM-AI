from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from axiom.api import engine as engine_api


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(engine_api.router)
    return TestClient(app)


def test_engine_request_accepts_absolute_paths_only_inside_explicit_roots(tmp_path, monkeypatch) -> None:
    root = tmp_path / "models"
    model = root / "tiny-model"
    model.mkdir(parents=True)
    monkeypatch.setenv("AXIOM_MODEL_ROOTS", str(root))

    request = engine_api.GenerateRequest(model_path=str(model), prompt="hello")

    assert request.model_path == str(model.resolve())


def test_engine_request_rejects_absolute_path_outside_configured_roots(tmp_path, monkeypatch) -> None:
    root = tmp_path / "models"
    root.mkdir()
    outside = tmp_path / "private"
    outside.mkdir()
    monkeypatch.setenv("AXIOM_MODEL_ROOTS", str(root))

    with pytest.raises(ValidationError, match="allowed model directory"):
        engine_api.GenerateRequest(model_path=str(outside), prompt="hello")


def test_engine_request_rejects_symlink_escape(tmp_path, monkeypatch) -> None:
    root = tmp_path / "models"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    escape = root / "escape"
    try:
        escape.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"Directory symlinks are unavailable on this platform: {exc}")
    monkeypatch.setenv("AXIOM_MODEL_ROOTS", str(root))

    with pytest.raises(ValidationError, match="symlink escapes"):
        engine_api.GenerateRequest(model_path=str(escape), prompt="hello")


def test_engine_unload_endpoint_calls_lifecycle_handler(monkeypatch) -> None:
    expected = {
        "schema_version": 1,
        "unloaded": True,
        "loaded": False,
        "scope_note": "Model unloaded for test.",
    }
    monkeypatch.setattr(engine_api, "unload_local_model", lambda: expected)

    response = _client().post("/api/engine/unload")

    assert response.status_code == 200
    assert response.json() == expected
