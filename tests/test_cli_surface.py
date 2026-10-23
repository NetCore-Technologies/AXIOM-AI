from pathlib import Path

from typer.testing import CliRunner

import axiom.cli.main as cli_main
from axiom.cli.main import app

runner = CliRunner()


def test_help_surfaces_first_run_commands_and_guide_if_available(
    tmp_path: Path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)

    help_result = runner.invoke(app, ["--help"])

    assert help_result.exit_code == 0, help_result.stdout
    assert "init" in help_result.stdout
    assert "project" in help_result.stdout

    guide_help_result = runner.invoke(app, ["guide", "--help"])
    if "guide" not in help_result.stdout.lower():
        assert guide_help_result.exit_code != 0
        return

    assert guide_help_result.exit_code == 0, guide_help_result.stdout
    guide_result = runner.invoke(app, ["guide"])

    assert guide_result.exit_code == 0, guide_result.stdout
    assert "AXIOM" in guide_result.stdout
    assert "local" in guide_result.stdout.lower()
    assert "axiom init" in guide_result.stdout or "axiom project" in guide_result.stdout
    assert "http://" not in guide_result.stdout.lower()
    assert "https://" not in guide_result.stdout.lower()


def test_shell_completion_can_be_viewed_for_supported_shells_without_installing(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    help_result = runner.invoke(app, ["--help"])
    assert help_result.exit_code == 0, help_result.stdout
    # Click/Typer can route help text to stderr on newer releases; output
    # combines both streams and tests the public CLI surface rather than a
    # version-specific capture detail.
    assert "--install-completion" in help_result.output
    assert "--show-completion" in help_result.output

    for shell in ("bash", "zsh", "fish", "powershell"):
        result = runner.invoke(app, ["--show-completion", shell])
        assert result.exit_code == 0, f"{shell}: {result.stdout}"
        assert result.output.strip()


def test_init_creates_a_project_that_project_commands_can_use(
    tmp_path: Path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)

    init_result = runner.invoke(app, ["init", "first-project"])

    assert init_result.exit_code == 0, init_result.stdout
    project_root = tmp_path / "first-project"
    assert project_root.is_dir()
    assert (project_root / "axiom.yaml").is_file()
    assert (project_root / "README.md").is_file()
    for directory in (
        "data/raw",
        "data/processed",
        "models",
        "experiments",
        "evaluations",
        "outputs",
    ):
        assert (project_root / directory).is_dir()

    monkeypatch.chdir(project_root)

    info_result = runner.invoke(app, ["project", "info"])
    validate_result = runner.invoke(app, ["project", "validate"])

    assert info_result.exit_code == 0, info_result.stdout
    assert "Config:" in info_result.stdout
    assert "found" in info_result.stdout
    assert "README:" in info_result.stdout
    assert validate_result.exit_code == 0, validate_result.stdout
    assert "valid" in validate_result.stdout.lower()



def test_gui_port_uses_environment_default_and_explicit_flag_precedence(monkeypatch):
    monkeypatch.setenv("AXIOM_GUI_PORT", "40123")
    assert cli_main._resolve_gui_port(None) == 40123
    assert cli_main._resolve_gui_port(40234) == 40234


def test_gui_port_rejects_invalid_environment_configuration(monkeypatch):
    monkeypatch.setenv("AXIOM_GUI_PORT", "not-a-port")
    try:
        cli_main._resolve_gui_port(None)
    except ValueError as exc:
        assert "AXIOM_GUI_PORT" in str(exc)
    else:
        raise AssertionError("Invalid AXIOM_GUI_PORT must be rejected")

    monkeypatch.setenv("AXIOM_GUI_PORT", "65536")
    try:
        cli_main._resolve_gui_port(None)
    except ValueError as exc:
        assert "0 to 65535" in str(exc)
    else:
        raise AssertionError("Out-of-range AXIOM_GUI_PORT must be rejected")
