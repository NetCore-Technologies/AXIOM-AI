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
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from axiom.daemon import local_summary
from axiom.version import __version__

AXIOM_VERSION = __version__
console = Console()

PROJECT_PATHS = (
    "axiom.yaml",
    "README.md",
    "data",
    "models",
    "experiments",
    "evaluations",
    "outputs",
)


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


def project_detected(root: Path) -> bool:
    """Return whether the current directory has an AXIOM config file."""
    return (root / "axiom.yaml").is_file()


def missing_project_paths(root: Path) -> list[str]:
    """Return standard project paths that are absent from ``root``."""
    return [path for path in PROJECT_PATHS if not (root / path).exists()]


def next_commands(root: Path) -> tuple[str, ...]:
    """Choose safe, local next commands for the current directory state."""
    if not project_detected(root):
        return (
            "axiom init my-ai",
            "cd my-ai",
            "axiom guide",
        )

    if missing_project_paths(root):
        return (
            "axiom config validate",
            "axiom project validate",
            "axiom status",
        )

    return (
        "axiom config validate",
        "axiom status",
        "axiom model list",
    )


def print_next_commands(commands: tuple[str, ...]) -> None:
    console.print("Next commands:")

    for index, command in enumerate(commands, start=1):
        console.print(f"  {index}. [cyan]{command}[/cyan]")


def register(app, model_app, dataset_app) -> None:

    @app.command("doctor")
    def doctor() -> None:
        """Inspect common local tools and AXIOM package metadata."""
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
        """Show local AXIOM and Python environment information."""
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
        """Show local AXIOM config and Git working-tree information."""
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

    @app.command("summary")
    def summary(
        json_output: bool = typer.Option(
            False,
            "--json",
            help="Print a stable machine-readable local snapshot.",
        ),
    ) -> None:
        """Summarize the current project, machine, tools, and next command."""

        payload = local_summary()
        if json_output:
            typer.echo(json.dumps(payload, indent=2, sort_keys=True))
            return

        project = payload["project"]
        hardware = payload["hardware"]
        tools = payload["tools"]
        console.print(
            Panel.fit(
                f"Directory: {payload['working_directory']}\n"
                f"Project: {'detected' if project['detected'] else 'not detected'}\n"
                f"Missing paths: {', '.join(project['missing_paths']) or 'none'}\n\n"
                f"System: {hardware['os_name']} / {hardware['architecture']}\n"
                f"CPU: {hardware['cpu_cores']} cores, RAM: {hardware['ram_gb']:.2f} GB\n"
                f"GPU: {hardware['gpu_name'] or 'not detected'}\n\n"
                f"Tools on PATH: {tools['available']} of {tools['total']}",
                title="AXIOM SUMMARY",
            )
        )
        console.print(
            f"Next: [cyan]{payload['recommended']['command']}[/cyan]\n"
            f"{payload['recommended']['reason']}"
        )

    @app.command("guide")
    def guide() -> None:
        """Explain AXIOM and suggest the next local commands."""
        root = Path.cwd()
        detected = project_detected(root)

        if detected:
            missing = missing_project_paths(root)
            project_line = "detected (axiom.yaml found)"
            structure_line = (
                "standard project paths are present"
                if not missing
                else f"missing: {', '.join(missing)}"
            )
        else:
            project_line = "not detected (axiom.yaml is missing)"
            structure_line = "create a project with the commands below"

        console.print(
            Panel.fit(
                "[bold cyan]AXIOM GUIDE[/bold cyan]\n\n"
                "AXIOM is a local-first command-line tool for organizing AI "
                "model and dataset work. It can inspect local files, check "
                "project structure, keep local model metadata, and make "
                "hardware-aware training-plan estimates. Some commands can "
                "use external services; this guide only checks the current "
                "directory.\n\n"
                f"Current directory: {root}\n"
                f"AXIOM project: {project_line}\n"
                f"Project structure: {structure_line}",
                title="AXIOM",
            )
        )
        print_next_commands(next_commands(root))

    @app.command("check")
    def check() -> None:
        """Quickly check for a local AXIOM project and its standard paths."""
        root = Path.cwd()

        if not project_detected(root):
            console.print(f"[yellow]No AXIOM project detected:[/yellow] {root}")
            console.print("Next: [cyan]axiom init my-ai[/cyan]")
            return

        missing = missing_project_paths(root)
        console.print(f"[green]✓ AXIOM project detected:[/green] {root}")

        if missing:
            console.print(
                f"[yellow]Missing standard paths:[/yellow] {', '.join(missing)}"
            )
        else:
            console.print("[green]✓ Standard project paths are present.[/green]")

        console.print("Next: [cyan]axiom config validate[/cyan]")

    @model_app.command("inspect")
    def model_inspect(
        path: str = typer.Argument(
            ...,
            help="Local model file or directory to summarize",
        ),
    ) -> None:
        """Summarize a local model file or directory."""
        target = Path(path)

        if not target.exists():
            console.print(f"[red]Error:[/red] model path not found: {target}")
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
        query: str = typer.Argument(
            ...,
            help="Text to match in local model paths",
        ),
        path: str = typer.Option(
            "models",
            "--path",
            help="Directory to search for matching local model paths",
        ),
    ) -> None:
        """Search local model paths by name."""
        root = Path(path)

        if not root.exists():
            console.print(f"[yellow]No model directory:[/yellow] {root}")
            return

        matches = [
            item for item in root.rglob("*") if query.lower() in str(item).lower()
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
                human_size(item.stat().st_size) if item.is_file() else "-",
            )

        console.print(table)

    @dataset_app.command("validate")
    def dataset_validate(
        path: str = typer.Argument(
            ...,
            help="Local JSONL dataset file",
        ),
    ) -> None:
        """Check JSONL records and report duplicate objects."""
        dataset = Path(path)

        if not dataset.is_file():
            console.print(f"[red]Error:[/red] dataset not found: {dataset}")
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
                        raise TypeError("record is not a JSON object")

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

                except Exception as exc:  # noqa: BLE001
                    invalid += 1
                    console.print(f"[red]INVALID[/red] line {line_no}: {exc}")

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
        path: str = typer.Argument(
            ...,
            help="Local JSONL dataset file",
        ),
    ) -> None:
        """Show local JSONL counts and a rough token estimate."""
        dataset = Path(path)

        if not dataset.is_file():
            console.print(f"[red]Error:[/red] dataset not found: {dataset}")
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
        help="Inspect and validate the current local AXIOM project."
    )
    app.add_typer(project_app, name="project")

    @project_app.command("info")
    def project_info() -> None:
        """Show local project markers in the current directory."""
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
        """Check expected AXIOM project paths in the current directory."""
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

        missing = [item for item in required if not (root / item).exists()]

        if missing:
            console.print("[red]Project validation failed.[/red]")

            for item in missing:
                console.print(f"  [red]×[/red] {item}")

            raise typer.Exit(code=1)

        console.print("[green]✓ AXIOM project structure is valid.[/green]")

    config_app = typer.Typer(help="Inspect local AXIOM project configuration.")
    app.add_typer(config_app, name="config")

    @config_app.command("show")
    def config_show(
        path: str = typer.Option(
            "axiom.yaml",
            "--path",
            help="Path to a local axiom.yaml file",
        ),
    ) -> None:
        """Print a local axiom.yaml file."""
        config = Path(path)

        if not config.is_file():
            console.print(f"[red]Error:[/red] config not found: {config}")
            raise typer.Exit(code=1)

        typer.echo(config.read_text(encoding="utf-8"))

    @config_app.command("validate")
    def config_validate(
        path: str = typer.Option(
            "axiom.yaml",
            "--path",
            help="Path to a local axiom.yaml file",
        ),
    ) -> None:
        """Validate a local axiom.yaml as a non-empty YAML mapping."""
        config = Path(path)

        if not config.is_file():
            console.print(f"[red]Error:[/red] config not found: {config}")
            raise typer.Exit(code=1)

        try:
            contents = config.read_text(encoding="utf-8")
            parsed = yaml.safe_load(contents)
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            console.print(f"[red]Error:[/red] invalid axiom.yaml: {exc}")
            raise typer.Exit(code=1)

        if not contents.strip():
            console.print("[red]Error:[/red] axiom.yaml is empty")
            raise typer.Exit(code=1)

        if not isinstance(parsed, dict):
            console.print("[red]Error:[/red] axiom.yaml must contain a mapping")
            raise typer.Exit(code=1)

        console.print(
            "[green]✓ axiom.yaml is valid YAML and contains a mapping.[/green]"
        )
