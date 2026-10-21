from __future__ import annotations

from typer.testing import CliRunner

from axiom.cli.main import app


def test_infer_status_json_is_a_registered_cli_command(monkeypatch):
    fake = {
        "backend": "ollama", "endpoint": "http://127.0.0.1:11434", "runtime_installed": True,
        "status": "online", "models": ["qwen2.5:0.5b"], "error": None,
        "checked_at": "2026-10-21T00:00:00+00:00",
    }
    monkeypatch.setattr("axiom.cli.inference.runtime_status", lambda: fake)
    result = CliRunner().invoke(app, ["--no-banner", "infer", "status", "--json"])
    assert result.exit_code == 0, result.output
    assert '"status": "online"' in result.output
    assert "qwen2.5:0.5b" in result.output
