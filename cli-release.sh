#!/usr/bin/env bash
set -euo pipefail

cd /workspaces/Optimization-Project-Name-TBD

VERSION="0.2.0-beta.4"
TAG="v${VERSION}"
PY_VERSION="0.2.0b4"

echo "============================================================"
echo " AXIOM CLI EXPANSION"
echo " Release: ${TAG}"
echo "============================================================"

echo
echo "===== SYNC MAIN ====="
git diff --quiet || { echo "Tracked changes exist."; exit 1; }
git diff --cached --quiet || { echo "Staged changes exist."; exit 1; }

git fetch origin
git rebase origin/main

echo
echo "===== GPG ====="
git config --local user.name "Manit Arora"
git config --local user.email "manit6752025@gmail.com"
git config --local user.signingkey BA75335BF0BC7084
git config --local gpg.program gpg
git config --local commit.gpgSign true

export GPG_TTY="$(tty 2>/dev/null || true)"
gpg-connect-agent updatestartuptty /bye >/dev/null 2>&1 || true

echo
echo "===== VERSION ====="

python3 - <<'PY'
from pathlib import Path
import re

# pyproject.toml
p = Path("pyproject.toml")
s = p.read_text()

m = re.search(
    r'(\[project\][\s\S]*?\nversion\s*=\s*["\'])[^"\']+(["\'])',
    s,
    re.M,
)

if not m:
    raise SystemExit("Could not find project version in pyproject.toml")

s = s[:m.start(0)] + m.group(1) + "0.2.0b4" + m.group(2) + s[m.end(0):]
p.write_text(s)

# axiom/version.py
p = Path("axiom/version.py")

if p.exists():
    s = p.read_text()
    s2, count = re.subn(
        r'(__version__\s*=\s*["\'])[^"\']+(["\'])',
        r'\g<1>0.2.0-beta.4\2',
        s,
        count=1,
    )

    if count:
        p.write_text(s2)

print("pyproject.toml -> 0.2.0b4")
print("axiom/version.py -> 0.2.0-beta.4")
PY

echo
echo "===== CLI EXTENSION ====="

mkdir -p axiom/cli

cat > axiom/cli/extended.py <<'PY'
"""Additional AXIOM CLI commands."""

from __future__ import annotations

import importlib.metadata
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

AXIOM_VERSION = "0.2.0-beta.4"
console = Console()


def package_version() -> str:
    try:
        return importlib.metadata.version("axiom-ai")
    except importlib.metadata.PackageNotFoundError:
        return "development"


def git_output(*args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout.strip()
    except OSError:
        return ""


def human_size(size: int) -> str:
    value = float(size)

    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(value)} B"
            return f"{value:.2f} {unit}"
        value /= 1024

    return f"{size} B"


def register(app, model_app, dataset_app) -> None:

    @app.command("doctor")
    def doctor() -> None:
        """Check common AXIOM development requirements."""
        typer.echo(f"AXIOM Doctor — {AXIOM_VERSION}")
        typer.echo("")

        checks = [
            ("Python", shutil.which("python3") or shutil.which("python")),
            ("Git", shutil.which("git")),
            ("Node.js", shutil.which("node")),
            ("npm", shutil.which("npm")),
        ]

        warnings = 0

        for name, executable in checks:
            if executable:
                typer.echo(f"[OK]   {name}: {executable}")
            else:
                typer.echo(f"[WARN] {name}: not found")
                warnings += 1

        installed = package_version()

        if installed == "development":
            typer.echo("[WARN] AXIOM package metadata not installed")
            warnings += 1
        else:
            typer.echo(f"[OK]   AXIOM package: {installed}")

        typer.echo("")
        typer.echo(f"Doctor complete: {warnings} warning(s)")

    @app.command("info")
    def info() -> None:
        """Show AXIOM and environment information."""
        cwd = Path.cwd()

        console.print(
            Panel.fit(
                f"[bold cyan]AXIOM[/bold cyan] v{AXIOM_VERSION}\n\n"
                f"Package: {package_version()}\n"
                f"Python: {platform.python_version()}\n"
                f"Platform: {platform.platform()}\n"
                f"Executable: {sys.executable}\n"
                f"Working directory: {cwd}\n"
                f"Project config: "
                f"{'found' if (cwd / 'axiom.yaml').exists() else 'not found'}\n"
                f"Git branch: "
                f"{git_output('branch', '--show-current') or 'n/a'}",
                title="AXIOM INFO",
            )
        )

    @app.command("status")
    def status() -> None:
        """Show AXIOM project and Git status."""
        cwd = Path.cwd()
        dirty = bool(git_output("status", "--porcelain"))

        table = Table(title="AXIOM STATUS")
        table.add_column("Item")
        table.add_column("Value")

        table.add_row("Version", AXIOM_VERSION)
        table.add_row(
            "Project config",
            "found" if (cwd / "axiom.yaml").exists() else "not found",
        )
        table.add_row(
            "Git branch",
            git_output("branch", "--show-current") or "n/a",
        )
        table.add_row(
            "Git commit",
            git_output("rev-parse", "--short", "HEAD") or "n/a",
        )
        table.add_row("Working tree", "modified" if dirty else "clean")

        console.print(table)

    @model_app.command("inspect")
    def model_inspect(
        path: str = typer.Argument(..., help="Local model file or directory"),
    ) -> None:
        """Inspect a local model path."""
        target = Path(path)

        if not target.exists():
            console.print(
                f"[red]Error:[/red] model path not found: {target}"
            )
            raise typer.Exit(code=1)

        if target.is_file():
            size = human_size(target.stat().st_size)
            console.print(
                Panel.fit(
                    f"[bold cyan]AXIOM MODEL[/bold cyan]\n\n"
                    f"Path: {target}\n"
                    f"Size: {size}",
                    title="AXIOM",
                )
            )
            return

        files = [p for p in target.rglob("*") if p.is_file()]
        total = sum(p.stat().st_size for p in files)

        console.print(
            Panel.fit(
                f"[bold cyan]AXIOM MODEL[/bold cyan]\n\n"
                f"Path: {target}\n"
                f"Files: {len(files)}\n"
                f"Total size: {human_size(total)}",
                title="AXIOM",
            )
        )

    @model_app.command("search")
    def model_search(
        query: str = typer.Argument(..., help="Search text"),
        path: str = typer.Option(
            "models",
            "--path",
            help="Local models directory",
        ),
    ) -> None:
        """Search local model files and directories."""
        root = Path(path)

        if not root.exists():
            console.print(
                f"[yellow]No model directory:[/yellow] {root}"
            )
            return

        matches = [
            item
            for item in root.rglob("*")
            if query.lower() in str(item).lower()
        ]

        if not matches:
            console.print("[yellow]No matches found.[/yellow]")
            return

        table = Table(title="AXIOM MODEL SEARCH")
        table.add_column("Path")
        table.add_column("Type")
        table.add_column("Size")

        for item in matches:
            table.add_row(
                str(item),
                "file" if item.is_file() else "directory",
                human_size(item.stat().st_size)
                if item.is_file()
                else "-",
            )

        console.print(table)

    @dataset_app.command("validate")
    def dataset_validate(
        path: str = typer.Argument(..., help="JSONL dataset"),
    ) -> None:
        """Validate JSONL records and detect duplicates."""
        dataset = Path(path)

        if not dataset.is_file():
            console.print(
                f"[red]Error:[/red] dataset not found: {dataset}"
            )
            raise typer.Exit(code=1)

        total = 0
        valid = 0
        invalid = 0
        duplicates = 0
        seen: set[str] = set()

        with dataset.open("r", encoding="utf-8") as handle:
            for line_no, raw in enumerate(handle, start=1):
                if not raw.strip():
                    continue

                total += 1

                try:
                    record = json.loads(raw)

                    if not isinstance(record, dict):
                        raise ValueError(
                            "record is not a JSON object"
                        )

                    normalized = json.dumps(
                        record,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    )

                    if normalized in seen:
                        duplicates += 1
                    else:
                        seen.add(normalized)

                    valid += 1

                except Exception as exc:
                    invalid += 1
                    console.print(
                        f"[red]INVALID[/red] line "
                        f"{line_no}: {exc}"
                    )

        table = Table(title="AXIOM DATASET VALIDATION")
        table.add_column("Metric")
        table.add_column("Value", justify="right")

        table.add_row("Records", str(total))
        table.add_row("Valid", str(valid))
        table.add_row("Invalid", str(invalid))
        table.add_row("Duplicates", str(duplicates))

        console.print(table)

        if invalid:
            raise typer.Exit(code=1)

    @dataset_app.command("stats")
    def dataset_stats(
        path: str = typer.Argument(..., help="JSONL dataset"),
    ) -> None:
        """Show basic JSONL dataset statistics."""
        dataset = Path(path)

        if not dataset.is_file():
            console.print(
                f"[red]Error:[/red] dataset not found: {dataset}"
            )
            raise typer.Exit(code=1)

        records = 0
        fields: set[str] = set()
        estimated_tokens = 0

        with dataset.open("r", encoding="utf-8") as handle:
            for raw in handle:
                if not raw.strip():
                    continue

                try:
                    record = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                if isinstance(record, dict):
                    records += 1
                    fields.update(str(key) for key in record)
                    estimated_tokens += max(1, len(raw.split()) * 2)

        console.print(
            Panel.fit(
                f"[bold cyan]AXIOM DATASET STATS[/bold cyan]\n\n"
                f"Records: {records}\n"
                f"Fields: {', '.join(sorted(fields)) or 'None'}\n"
                f"Estimated tokens: {estimated_tokens}",
                title="AXIOM",
            )
        )

    project_app = typer.Typer(
        help="Inspect and validate AXIOM projects."
    )
    app.add_typer(project_app, name="project")

    @project_app.command("info")
    def project_info() -> None:
        """Show current AXIOM project information."""
        root = Path.cwd()

        console.print(
            Panel.fit(
                f"[bold cyan]AXIOM PROJECT[/bold cyan]\n\n"
                f"Path: {root}\n"
                f"Config: "
                f"{'found' if (root / 'axiom.yaml').exists() else 'missing'}\n"
                f"README: "
                f"{'found' if (root / 'README.md').exists() else 'missing'}",
                title="AXIOM",
            )
        )

    @project_app.command("validate")
    def project_validate() -> None:
        """Validate the standard AXIOM project structure."""
        root = Path.cwd()

        required = [
            "axiom.yaml",
            "README.md",
            "data",
            "models",
            "experiments",
            "evaluations",
            "outputs",
        ]

        missing = [
            item
            for item in required
            if not (root / item).exists()
        ]

        if missing:
            console.print("[red]Project validation failed.[/red]")

            for item in missing:
                console.print(f"  [red]×[/red] {item}")

            raise typer.Exit(code=1)

        console.print(
            "[green]✓ AXIOM project structure is valid.[/green]"
        )

    config_app = typer.Typer(
        help="Inspect AXIOM project configuration."
    )
    app.add_typer(config_app, name="config")

    @config_app.command("show")
    def config_show(
        path: str = typer.Option(
            "axiom.yaml",
            "--path",
        ),
    ) -> None:
        """Print the AXIOM project configuration."""
        config = Path(path)

        if not config.is_file():
            console.print(
                f"[red]Error:[/red] config not found: {config}"
            )
            raise typer.Exit(code=1)

        typer.echo(
            config.read_text(encoding="utf-8")
        )

    @config_app.command("validate")
    def config_validate(
        path: str = typer.Option(
            "axiom.yaml",
            "--path",
        ),
    ) -> None:
        """Validate that axiom.yaml exists and is readable."""
        config = Path(path)

        if not config.is_file():
            console.print(
                f"[red]Error:[/red] config not found: {config}"
            )
            raise typer.Exit(code=1)

        if not config.read_text(encoding="utf-8").strip():
            console.print(
                "[red]Error:[/red] axiom.yaml is empty"
            )
            raise typer.Exit(code=1)

        console.print(
            "[green]✓ axiom.yaml is readable and non-empty.[/green]"
        )
PY

# Register the extension exactly once.
python3 - <<'PY'
from pathlib import Path

p = Path("axiom/cli/main.py")
s = p.read_text()

if "from axiom.cli.extended import register" not in s:
    marker = 'app.add_typer(train_app, name="train")'

    if marker not in s:
        raise SystemExit(
            "Could not find train_app registration."
        )

    insertion = '''
app.add_typer(train_app, name="train")

# Extended AXIOM CLI
from axiom.cli.extended import register as register_extended_cli
register_extended_cli(app, model_app, dataset_app)
'''

    s = s.replace(marker, insertion, 1)

    p.write_text(s)
PY

echo
echo "===== CLI TESTS ====="

mkdir -p tests

cat > tests/test_cli_extended.py <<'PY'
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
PY

echo
echo "===== INSTALL ====="
python3 -m pip install -e .

echo
echo "===== CLI HELP ====="
axiom --help

echo
echo "===== CLI SMOKE TESTS ====="
axiom version
axiom info
axiom status
axiom doctor
axiom model --help
axiom dataset --help
axiom project --help
axiom config --help

echo
echo "===== PYTEST ====="
python3 -m pytest -q

if [[ -f package.json ]]; then
  echo
  echo "===== NPM LINT ====="
  npm run lint

  echo
  echo "===== NPM BUILD ====="
  npm run build
fi

echo
echo "===== FINAL CHECK ====="
git diff --check

echo
echo "===== CHANGES ====="
git status --short
git diff --stat

echo
echo "===== STAGE ====="
git add \
  axiom/cli/main.py \
  axiom/cli/extended.py \
  axiom/version.py \
  pyproject.toml \
  tests/test_cli_extended.py \
  "docs/releases/${TAG}.md" 2>/dev/null || true

mkdir -p docs/releases

cat > "docs/releases/${TAG}.md" <<EOF
# AXIOM ${TAG}

## CLI expansion

AXIOM ${TAG} expands the command-line engineering experience while preserving the existing AXIOM CLI workflows.

### New commands

\`\`\`text
axiom doctor
axiom info
axiom status

axiom model inspect <path>
axiom model search <query>

axiom dataset validate <path>
axiom dataset stats <path>

axiom project info
axiom project validate

axiom config show
axiom config validate
\`\`\`

## Existing workflows

Existing model, dataset, training, Hugging Face, SuperCompress, integration and MCP commands remain part of the CLI.

## Version

- Display version: ${VERSION}
- Python package version: ${PY_VERSION}

## Beta

This is a beta release under active development.
EOF

git add "docs/releases/${TAG}.md"

git diff --cached --check

echo
echo "===== STAGED ====="
git diff --cached --name-status

echo
echo "===== SIGNED COMMIT ====="

GIT_AUTHOR_NAME="Manit Arora" \
GIT_AUTHOR_EMAIL="manit6752025@gmail.com" \
GIT_COMMITTER_NAME="Manit Arora" \
GIT_COMMITTER_EMAIL="manit6752025@gmail.com" \
git commit -S \
  -m "feat: expand AXIOM CLI for ${TAG}"

git log -1 --show-signature --format=fuller

echo
echo "===== PUSH MAIN ====="
git push origin main

echo
echo "===== SIGNED RELEASE TAG ====="

if git ls-remote --exit-code --tags origin "refs/tags/${TAG}" >/dev/null 2>&1; then
  echo "ERROR: ${TAG} already exists remotely."
  exit 1
fi

GIT_COMMITTER_NAME="Manit Arora" \
GIT_COMMITTER_EMAIL="manit6752025@gmail.com" \
git tag -s -u "BA75335BF0BC7084" \
  "${TAG}" \
  -m "AXIOM ${TAG} — CLI expansion and engineering update"

git tag -v "${TAG}"

echo
echo "===== PUSH TAG ====="
git push origin "${TAG}"

echo
echo "============================================================"
echo " AXIOM ${TAG} RELEASE STARTED"
echo "============================================================"

gh run list \
  --repo NetCore-Technologies/AXIOM-AI \
  --workflow="AXIOM Release" \
  --limit 5 || true

echo
echo "Release:"
echo "https://github.com/NetCore-Technologies/AXIOM-AI/releases/tag/${TAG}"
