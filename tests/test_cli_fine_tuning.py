from __future__ import annotations

from typer.testing import CliRunner
from typer.main import get_command

from axiom.cli.main import app


def test_train_help_exposes_real_fine_tuning_commands():
    runner = CliRunner()
    help_result = runner.invoke(app, ["--no-banner", "train", "--help"])
    assert help_result.exit_code == 0, help_result.output
    assert "run" in help_result.output
    assert "jobs" in help_result.output
    assert "status" in help_result.output


def test_train_run_exposes_required_input_options():
    command = get_command(app).commands["train"].commands["run"]
    options = {
        option
        for parameter in command.params
        for option in getattr(parameter, "opts", ())
    }
    assert {"--model-path", "--dataset", "--output-dir"} <= options
