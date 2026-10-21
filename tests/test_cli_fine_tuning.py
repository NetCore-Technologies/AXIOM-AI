from __future__ import annotations

from typer.testing import CliRunner

from axiom.cli.main import app


def test_train_help_exposes_real_fine_tuning_commands():
    runner = CliRunner()
    help_result = runner.invoke(app, ["--no-banner", "train", "--help"])
    assert help_result.exit_code == 0, help_result.output
    assert "run" in help_result.output
    assert "jobs" in help_result.output
    assert "status" in help_result.output


def test_train_run_help_is_actionable():
    result = CliRunner().invoke(app, ["train", "run", "--help"])
    assert result.exit_code == 0, result.output
    assert "--model-path" in result.output
    assert "--dataset" in result.output
    assert "--output-dir" in result.output
