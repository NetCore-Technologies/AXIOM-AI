from __future__ import annotations

import zipfile
from pathlib import Path

from typer.testing import CliRunner
import typer

from axiom.cli.support_bundle import register


def test_support_bundle_cli_creates_private_archive_and_refuses_overwrite(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "axiom.yaml").write_text("project:\n  name: demo\n", encoding="utf-8")
    output = tmp_path / "bundle.zip"
    app = typer.Typer()
    @app.command("stub")
    def stub() -> None:
        pass
    register(app)
    runner = CliRunner()

    result = runner.invoke(app, ["support-bundle", "--workspace", str(project), "--output", str(output)])
    assert result.exit_code == 0, result.output
    assert output.is_file()
    assert output.stat().st_mode & 0o077 == 0
    with zipfile.ZipFile(output) as archive:
        assert "diagnostics.json" in archive.namelist()

    again = runner.invoke(app, ["support-bundle", "--workspace", str(project), "--output", str(output)])
    assert again.exit_code != 0
    assert "already exists" in again.output


def test_support_bundle_cli_rejects_symlink_output(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    target = tmp_path / "target.zip"
    target.write_bytes(b"do not replace")
    output = tmp_path / "bundle.zip"
    try:
        output.symlink_to(target)
    except OSError:
        return
    app = typer.Typer()
    @app.command("stub")
    def stub() -> None:
        pass
    register(app)
    result = CliRunner().invoke(app, ["support-bundle", "--workspace", str(project), "--output", str(output)])
    assert result.exit_code != 0
    assert target.read_bytes() == b"do not replace"
