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
from axiom.core.diagnostics import diagnose_workspace
from axiom.cli.support_bundle import register as register_support_bundle_cli
from axiom.cli.roadmap import roadmap_app as roadmap_cli_app
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
    def doctor(
        json_output: bool = typer.Option(False, "--json", help="Emit stable machine-readable diagnostics."),
        workspace: str | None = typer.Option(None, "--workspace", help="Workspace directory to inspect."),
    ) -> None:
        """Inspect the current workspace, Python dependencies, and common tools."""
        try:
            report = diagnose_workspace(workspace)
        except (OSError, ValueError):
            message = {"schema_version": 1, "status": "error", "message": "Workspace could not be resolved safely."}
            typer.echo(json.dumps(message, sort_keys=True) if json_output else "Error: workspace could not be resolved safely.", err=not json_output)
            raise typer.Exit(code=2)
        tool_checks = [
            {"name": name, "available": bool(shutil.which(command)), "path": shutil.which(command)}
            for name, command in (("Python", "python3"), ("Python fallback", "python"), ("Git", "git"), ("Node.js", "node"), ("npm", "npm"))
        ]
        payload = {"schema_version": 1, "version": AXIOM_VERSION, "workspace": report, "tools": tool_checks}
        if json_output:
            typer.echo(json.dumps(payload, indent=2, sort_keys=True))
            if report["summary"]["failed"]:
                raise typer.Exit(code=1)
            return

        typer.echo(f"AXIOM Doctor — {AXIOM_VERSION}")
        typer.echo(f"Workspace: {report['workspace']['name']}")
        for check in report["checks"]:
            marker = "OK" if check["status"] == "pass" else "FAIL" if check["status"] == "fail" else "WARN" if check["status"] == "warn" else "INFO"
            typer.echo(f"[{marker:<4}] {check['title']}: {check['detail']}")
            if check["remediation"]:
                typer.echo(f"       Next: {check['remediation']}")
        for item in tool_checks:
            marker = "OK" if item["available"] else "WARN"
            typer.echo(f"[{marker:<4}] Tool {item['name']}: {item['path'] or 'not found'}")
        summary = report["summary"]
        typer.echo(f"Doctor complete: {summary['passed']} passed, {summary['warnings']} warning(s), {summary['failed']} failed")
        if summary["failed"]:
            raise typer.Exit(code=1)

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
    def status(
        json_output: bool = typer.Option(False, "--json", help="Emit stable machine-readable status."),
        workspace: str | None = typer.Option(None, "--workspace", help="Workspace directory to inspect."),
    ) -> None:
        """Show workspace health and local Git status without running jobs."""
        try:
            report = diagnose_workspace(workspace)
        except (OSError, ValueError):
            message = {"schema_version": 1, "status": "error", "message": "Workspace could not be resolved safely."}
            typer.echo(json.dumps(message, sort_keys=True) if json_output else "Error: workspace could not be resolved safely.", err=not json_output)
            raise typer.Exit(code=2)
        dirty = bool(git_output("status", "--porcelain"))
        payload = {
            "schema_version": 1,
            "version": AXIOM_VERSION,
            "workspace": report["workspace"],
            "health": {"status": report["status"], "summary": report["summary"]},
            "git": {
                "branch": git_output("branch", "--show-current") or None,
                "commit": git_output("rev-parse", "--short", "HEAD") or None,
                "dirty": dirty,
            },
        }
        if json_output:
            typer.echo(json.dumps(payload, indent=2, sort_keys=True))
            return

        table = Table(title="AXIOM STATUS")
        table.add_column("Item")
        table.add_column("Value")
        table.add_row("Version", AXIOM_VERSION)
        table.add_row("Workspace", report["workspace"]["name"])
        table.add_row("Project config", "found" if report["workspace"]["project_config_present"] else "not found")
        table.add_row("Workspace health", report["status"].upper())
        table.add_row("Checks", f"{report['summary']['passed']} passed / {report['summary']['warnings']} warnings / {report['summary']['failed']} failed")
        table.add_row("Git branch", payload["git"]["branch"] or "n/a")
        table.add_row("Git commit", payload["git"]["commit"] or "n/a")
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
                f"Tools on PATH: {tools['available']} of {tools['total']}\n"
                f"Missing tools: {', '.join(tools['missing']) or 'none'}",
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
        path: str = typer.Option("axiom.yaml", "--path", help="Path to a local axiom.yaml file"),
        json_output: bool = typer.Option(False, "--json", help="Emit a stable machine-readable result."),
    ) -> None:
        """Validate a local YAML mapping without echoing configuration values."""
        config = Path(path)
        status = "invalid"
        message = "Configuration validation failed."
        valid = False
        if config.is_symlink():
            message = "Configuration path must not be a symbolic link."
        elif not config.is_file():
            message = "Configuration file was not found."
        else:
            try:
                if config.stat().st_size > 256 * 1024:
                    raise ValueError("configuration exceeds the 256 KiB validation limit")
                contents = config.read_text(encoding="utf-8")
                parsed = yaml.safe_load(contents)
                if not contents.strip() or not isinstance(parsed, dict):
                    raise ValueError("configuration must be a non-empty YAML mapping")
                bad_sections = [key for key in ("project", "model", "dataset", "training", "evaluation", "deployment") if key in parsed and parsed[key] is not None and not isinstance(parsed[key], dict)]
                if bad_sections:
                    raise ValueError("known configuration sections must be YAML mappings")
            except (OSError, UnicodeError, yaml.YAMLError, ValueError):
                message = "invalid axiom.yaml: invalid axiom.yaml: Configuration could not be parsed as a bounded, compatible YAML mapping; values are withheld."
            else:
                valid = True
                status = "valid"
                message = "Configuration is valid YAML and known sections have compatible types."

        result = {"schema_version": 1, "status": status, "valid": valid, "path": str(config), "message": message}
        if json_output:
            typer.echo(json.dumps(result, indent=2, sort_keys=True))
        elif valid:
            console.print(f"[green]✓ {message}[/green]")
        else:
            console.print(f"[red]Error:[/red] {message}")
        if not valid:
            raise typer.Exit(code=1)

    app.add_typer(roadmap_cli_app, name="roadmap")
    register_support_bundle_cli(app)
