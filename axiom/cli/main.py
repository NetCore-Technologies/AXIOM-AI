from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from axiom.core.project import create_project
from axiom.datasets.cleaner import clean_jsonl
from axiom.datasets.inspector import inspect_dataset
from axiom.models.inspector import inspect_model
from axiom.models.registry import Model, ModelRegistry
from axiom.core.hardware import detect_hardware, estimate_model_fit

app = typer.Typer(
    name="axiom",
    help="Build, train, evaluate, and deploy AI models.",
)

model_app = typer.Typer(help="Manage AI models.")
dataset_app = typer.Typer(help="Inspect and manage datasets.")
system_app = typer.Typer(help="Inspect system hardware and capabilities.")

app.add_typer(model_app, name="model")
app.add_typer(dataset_app, name="dataset")
app.add_typer(system_app, name="system")

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
    except (FileExistsError, ValueError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)

    console.print(
        Panel.fit(
            f"[bold green]✓ AXIOM project created[/bold green]\n\n"
            f"[cyan]{root}[/cyan]\n\n"
            "Next steps:\n"
            f"  cd {name}\n"
            "  axiom model list",
            title="AXIOM",
        )
    )


@system_app.command("info")
def system_info():
    """Show detected hardware and AI runtime capability."""
    hardware = detect_hardware()

    gpu = hardware.gpu_name or "Not detected"
    vram = (
        f"{hardware.vram_gb:.2f} GB"
        if hardware.vram_gb is not None
        else "N/A"
    )

    console.print(
        Panel.fit(
            f"[bold cyan]AXIOM HARDWARE[/bold cyan]\n\n"
            f"OS:              {hardware.os_name}\n"
            f"Architecture:    {hardware.architecture}\n"
            f"CPU cores:       {hardware.cpu_cores}\n"
            f"RAM:             {hardware.ram_gb:.2f} GB\n"
            f"GPU:             {gpu}\n"
            f"VRAM:            {vram}\n"
            f"CUDA available:  {'✓' if hardware.cuda_available else '✗'}",
            title="AXIOM",
        )
    )

    if hardware.vram_gb is not None:
        table = Table(title="Model Fit Estimates")
        table.add_column("Model")
        table.add_column("FP16 / Q4")

        for billions in (1, 3, 7, 8, 14, 32, 70):
            table.add_row(
                f"{billions}B",
                estimate_model_fit(billions, hardware),
            )

        console.print(table)


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


@model_app.command("inspect")
def model_inspect(path: str):
    """Inspect a local AI model directory."""
    try:
        result = inspect_model(path)
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)

    parameters = (
        f"{result.parameter_count / 1_000_000_000:.2f}B"
        if result.parameter_count
        else "Unknown"
    )

    size_gb = result.weight_size_bytes / (1024 ** 3)

    vram = (
        f"{result.estimated_vram_gb:.2f} GB"
        if result.estimated_vram_gb is not None
        else "Unknown"
    )

    console.print(
        Panel.fit(
            f"[bold cyan]AXIOM MODEL INSPECTION[/bold cyan]\n\n"
            f"Path:           {result.path}\n"
            f"Architecture:   {result.architecture or 'Unknown'}\n"
            f"Model type:     {result.model_type or 'Unknown'}\n"
            f"Format:         {result.model_format}\n"
            f"Parameters:     {parameters}\n"
            f"Weight size:    {size_gb:.2f} GB\n"
            f"Estimated VRAM: {vram}\n\n"
            f"Config:         {'✓' if result.has_config else '✗'}\n"
            f"Tokenizer:      {'✓' if result.has_tokenizer else '✗'}\n"
            f"Safetensors:    {'✓' if result.has_safetensors else '✗'}\n"
            f"GGUF:           {'✓' if result.has_gguf else '✗'}\n"
            f"PyTorch:        {'✓' if result.has_pytorch_weights else '✗'}\n\n"
            f"Capabilities:   {', '.join(result.capabilities)}\n\n"
            f"Status:         {result.status}",
            title="AXIOM",
        )
    )


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
            f"File: {result.path}\n"
            f"Format: {result.format}\n\n"
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


@dataset_app.command("clean")
def dataset_clean(
    path: str,
    output: str | None = None,
):
    """Clean a JSONL dataset without modifying the original."""
    source = Path(path)

    if not source.exists():
        console.print(f"[red]Error:[/red] Dataset not found: {source}")
        raise typer.Exit(code=1)

    if not source.is_file():
        console.print(f"[red]Error:[/red] Not a file: {source}")
        raise typer.Exit(code=1)

    if source.suffix.lower() != ".jsonl":
        console.print(
            "[red]Error:[/red] Cleaning currently supports .jsonl files."
        )
        raise typer.Exit(code=1)

    destination = (
        Path(output)
        if output
        else source.with_name(f"{source.stem}.cleaned.jsonl")
    )

    try:
        result = clean_jsonl(source, destination)
    except OSError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)

    console.print(
        Panel.fit(
            f"[bold cyan]AXIOM DATASET CLEANING[/bold cyan]\n\n"
            f"Source:             {result.source}\n"
            f"Output:             {result.output}\n\n"
            f"Input rows:         {result.total_lines:,}\n"
            f"Kept:               {result.kept:,}\n"
            f"Invalid removed:    {result.removed_invalid:,}\n"
            f"Empty removed:      {result.removed_empty:,}\n"
            f"Duplicates removed: {result.removed_duplicates:,}\n"
            f"Schema removed:     {result.removed_schema:,}",
            title="AXIOM",
        )
    )


if __name__ == "__main__":
    app()
