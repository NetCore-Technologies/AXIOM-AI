from pathlib import Path

from typer.testing import CliRunner

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
