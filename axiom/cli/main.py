from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from axiom.core.project import create_project
from axiom.models.registry import Model, ModelRegistry
from axiom.datasets.inspector import inspect_dataset


app = typer.Typer(
    name="axiom",
    help="Build, train, evaluate, and deploy AI models."
)

model_app = typer.Typer(help="Manage AI models.")
app.add_typer(model_app, name="model")

console = Console()


@app.command()
def version():
    """Show AXIOM version."""
    console.print("[bold cyan]AXIOM[/bold cyan] v0.1.0")


@app.command()
def init(name: str):
    """Create a new AXIOM AI project."""
    try:
        root = create_project(name, Path.cwd())
    except FileExistsError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)

    console.print(
        Panel.fit(
            f"[bold green]✓ AXIOM project created[/bold green]\n\n"
            f"[cyan]{root}[/cyan]\n\n"
            f"Next steps:\n"
            f"  cd {name}\n"
            f"  axiom model list",
            title="AXIOM",
        )
    )


@model_app.command("list")
def model_list():
    """List registered models."""
    registry = ModelRegistry()
    models = registry.list()

    if not models:
        console.print("[yellow]No models registered.[/yellow]")
        return

    table = Table(title="AXIOM Models")

    table.add_column("Name")
    table.add_column("Source")
    table.add_column("Format")
    table.add_column("Parameters")
    table.add_column("Quantization")

    for model in models:
        table.add_row(
            model.name,
            model.source,
            model.format,
            model.parameters or "-",
            model.quantization or "-",
        )

    console.print(table)


dataset_app = typer.Typer(help="Inspect and manage datasets.")
app.add_typer(dataset_app, name="dataset")


@dataset_app.command("inspect")
def dataset_inspect(path: str):
    """Inspect a dataset and report its quality."""
    try:
        result = inspect_dataset(path)
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)

    console.print(
        Panel.fit(
            f"[bold cyan]AXIOM DATASET INSPECTION[/bold cyan]\n\n"
            f"File: [white]{result.path}[/white]\n"
            f"Format: [white]{result.format}[/white]\n\n"
            f"Samples:          {result.samples:,}\n"
            f"Valid:            {result.valid:,}\n"
            f"Invalid:          {result.invalid:,}\n"
            f"Empty:            {result.empty:,}\n"
            f"Duplicates:       {result.duplicates:,}\n"
            f"Estimated tokens: {result.estimated_tokens:,}\n\n"
            f"Fields: {', '.join(result.fields) if result.fields else '-'}",
            title="AXIOM",
        )
    )


@model_app.command("add")
def model_add(
    name: str,
    source: str,
    format: str = "unknown",
    parameters: str | None = None,
    quantization: str | None = None,
):
    """Register a model with AXIOM."""
    registry = ModelRegistry()

    try:
        registry.add(
            Model(
                name=name,
                source=source,
                format=format,
                parameters=parameters,
                quantization=quantization,
            )
        )
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)

    console.print(
        f"[green]✓[/green] Registered model: [cyan]{name}[/cyan]"
    )


if __name__ == "__main__":
    app()
