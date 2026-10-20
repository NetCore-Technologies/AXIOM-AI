from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from axiom.api import agent_profiles
from axiom.core.agent_profiles import AgentProfileStore


def test_agent_profile_api_create_update_delete(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(agent_profiles, "AgentProfileStore", lambda: AgentProfileStore(tmp_path))
    app = FastAPI()
    app.include_router(agent_profiles.router)
    client = TestClient(app)

    initial = client.get("/api/agent-profiles")
    assert initial.status_code == 200
    assert initial.json()["profiles"][0]["task_capabilities"] == []
    assert "do not grant" in initial.json()["authorization_note"]

    created = client.post("/api/agent-profiles", json={"name": "Research", "task_capabilities": ["model.inspect"]})
    assert created.status_code == 201
    profile = created.json()["profile"]

    updated = client.put(f"/api/agent-profiles/{profile['id']}", json={"task_capabilities": ["dataset.profile"]})
    assert updated.status_code == 200
    assert updated.json()["profile"]["version"] == 2

    assert client.delete("/api/agent-profiles/default").status_code == 400
    assert client.delete(f"/api/agent-profiles/{profile['id']}").status_code == 200


def test_agent_profile_api_rejects_unknown_capability(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(agent_profiles, "AgentProfileStore", lambda: AgentProfileStore(tmp_path))
    app = FastAPI()
    app.include_router(agent_profiles.router)
    response = TestClient(app).post("/api/agent-profiles", json={"name": "Unsafe", "task_capabilities": ["shell.execute"]})
    assert response.status_code == 422
