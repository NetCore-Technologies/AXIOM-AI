from __future__ import annotations

import json
import zipfile
from io import BytesIO
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from axiom.api.diagnostics import router


def test_workspace_diagnostics_api_is_read_only_and_reports_project(tmp_path: Path, monkeypatch):
    (tmp_path / "axiom.yaml").write_text("project:\n  name: api-test\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    app = FastAPI()
    app.include_router(router)
    response = TestClient(app).get("/api/diagnostics/workspace")
    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == 1
    assert payload["workspace"]["is_project"] is True
    assert not (tmp_path / ".axiom").exists()


def test_support_bundle_endpoint_returns_zip_with_no_config_values(tmp_path: Path, monkeypatch):
    (tmp_path / "axiom.yaml").write_text("project:\n  name: api-test\napi_key: DONT_EXPORT_ME\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    app = FastAPI()
    app.include_router(router)
    response = TestClient(app).get("/api/diagnostics/support-bundle")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/zip")
    assert response.headers["cache-control"] == "no-store"
    with zipfile.ZipFile(BytesIO(response.content)) as archive:
        assert set(archive.namelist()) == {"README.txt", "diagnostics.json", "environment.json"}
        content = b"".join(archive.read(name) for name in archive.namelist())
    assert b"DONT_EXPORT_ME" not in content


def test_roadmap_audit_endpoint_returns_live_source_statuses(tmp_path: Path):
    roadmap = tmp_path / "ROADMAP.md"
    rows = [
        "# Roadmap",
        "<!-- AXIOM-ROADMAP-UPDATE:START -->",
        "### 01 · Platform foundation",
    ]
    for number in range(1, 121):
        status = "Implemented; tests passing" if number <= 29 else "In progress; validation pending" if number <= 51 else "Planned"
        rows.append(f"- [R{number:03d} · {status}] Example deliverable {number}.")
    rows.append("<!-- AXIOM-ROADMAP-UPDATE:END -->")
    roadmap.write_text("\n".join(rows) + "\n", encoding="utf-8")

    app = FastAPI()
    app.include_router(router)
    response = TestClient(app).get("/api/diagnostics/roadmap", params={"path": str(roadmap)})
    assert response.status_code == 200
    payload = response.json()
    assert payload["integrity"]["ok"] is True
    assert payload["total"] == 120
    assert payload["counts"] == {"implemented": 29, "in_progress": 22, "planned": 69, "unknown": 0}
    assert payload["items"][0]["id"] == "R001"
    assert payload["items"][-1]["id"] == "R120"


def test_roadmap_audit_endpoint_rejects_symbolic_link(tmp_path: Path):
    real = tmp_path / "ROADMAP.md"
    real.write_text("not a roadmap", encoding="utf-8")
    link = tmp_path / "linked.md"
    try:
        link.symlink_to(real)
    except OSError:
        import pytest
        pytest.skip("symlink creation unavailable")
    app = FastAPI()
    app.include_router(router)
    response = TestClient(app).get("/api/diagnostics/roadmap", params={"path": str(link)})
    assert response.status_code == 400
