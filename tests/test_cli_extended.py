from pathlib import Path

from typer.testing import CliRunner

from axiom.cli.main import app

runner = CliRunner()


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "doctor" in result.stdout


def test_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "AXIOM" in result.stdout


def test_status():
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "Working tree" in result.stdout


def test_validate_dataset(tmp_path: Path):
    dataset = tmp_path / "train.jsonl"

    dataset.write_text(
        '{"instruction":"hello","output":"world"}\n'
        '{"instruction":"hello","output":"world"}\n',
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["dataset", "validate", str(dataset)],
    )

    assert result.exit_code == 0
    assert "Duplicates" in result.stdout


def test_project_validate(tmp_path: Path, monkeypatch):
    for folder in (
        "data",
        "models",
        "experiments",
        "evaluations",
        "outputs",
    ):
        (tmp_path / folder).mkdir()

    (tmp_path / "axiom.yaml").write_text(
        "project:\n  name: test\n",
        encoding="utf-8",
    )

    (tmp_path / "README.md").write_text(
        "# AXIOM test\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        ["project", "validate"],
    )

    assert result.exit_code == 0
