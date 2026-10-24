from __future__ import annotations

from typer.testing import CliRunner

from axiom.cli.main import app


def test_infer_status_json_is_a_registered_cli_command(monkeypatch):
    fake = {
        "backend": "ollama", "endpoint": "http://127.0.0.1:11434", "runtime_installed": True,
        "status": "online", "models": ["qwen2.5:0.5b"], "error": None,
        "checked_at": "2026-10-21T00:00:00+00:00",
    }
    monkeypatch.setattr("axiom.cli.inference.service_status", lambda: fake)
    result = CliRunner().invoke(app, ["--no-banner", "infer", "status", "--json"])
    assert result.exit_code == 0, result.output
    assert '"status": "online"' in result.output
    assert "qwen2.5:0.5b" in result.output


def test_infer_service_commands_are_registered():
    runner = CliRunner()
    result = runner.invoke(app, ["--no-banner", "infer", "service", "--help"])
    assert result.exit_code == 0, result.output
    assert "start" in result.output and "stop" in result.output and "status" in result.output


def test_infer_pull_command_is_registered():
    result = CliRunner().invoke(app, ["--no-banner", "infer", "pull", "--help"])
    assert result.exit_code == 0, result.output
    assert "Ollama model tag" in result.output


def test_infer_model_operation_commands_are_registered():
    runner = CliRunner()
    inspect = runner.invoke(app, ["--no-banner", "infer", "inspect", "--help"])
    unload = runner.invoke(app, ["--no-banner", "infer", "unload", "--help"])
    assert inspect.exit_code == 0, inspect.output
    assert unload.exit_code == 0, unload.output
    assert "metadata" in inspect.output.lower()
    assert "without deleting" in unload.output.lower()


def test_infer_loaded_model_inventory_command_is_registered():
    result = CliRunner().invoke(app, ["--no-banner", "infer", "ps", "--help"])
    assert result.exit_code == 0, result.output
    assert "loaded" in result.output.lower() and "memory" in result.output.lower()
