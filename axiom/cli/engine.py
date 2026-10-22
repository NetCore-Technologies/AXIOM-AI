"""CLI commands for AXIOM's direct local model engine."""
from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from axiom.core.engine import AxiomEngineError, discover_local_engine_assets, generate_local, runtime_status

engine_app = typer.Typer(help="Run causal language models directly through AXIOM's local engine.", no_args_is_help=True)
console = Console()


def _fail(message: str) -> None:
    console.print(f"[red]Error:[/red] {message}")
    raise typer.Exit(code=1)


@engine_app.command("discover")
def engine_discover(
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
) -> None:
    """Discover native-compatible local models and LoRA adapters below trusted roots."""
    report = discover_local_engine_assets()
    if json_output:
        typer.echo(json.dumps(report, indent=2, ensure_ascii=False))
        return

    models = report["models"]
    adapters = report["adapters"]
    if models:
        table = Table(title=f"Native models ({len(models)})")
        table.add_column("Name", style="cyan")
        table.add_column("Type")
        table.add_column("Architecture")
        table.add_column("Checkpoint")
        table.add_column("Path")
        for model in models:
            table.add_row(
                model["name"], model["model_type"], model["architecture"],
                model["weight_format"], model["path"],
            )
        console.print(table)
    else:
        console.print("[yellow]No compatible native models found under trusted roots.[/yellow]")

    if adapters:
        table = Table(title=f"LoRA adapters ({len(adapters)})")
        table.add_column("Name", style="cyan")
        table.add_column("Format")
        table.add_column("Path")
        for adapter in adapters:
            table.add_row(adapter["name"], adapter["weight_format"], adapter["path"])
        console.print(table)
    elif not models:
        console.print("No native-compatible LoRA adapters found.")

    if report["truncated"]:
        console.print("[yellow]The inventory reached its result cap. Narrow AXIOM_MODEL_ROOTS to inspect a smaller set.[/yellow]")
    console.print(report["scope_note"])


@engine_app.command("status")
def engine_status(json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON.")) -> None:
    """Check AXIOM Engine dependencies and loaded-model state."""
    report = runtime_status()
    if json_output:
        typer.echo(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        table = Table(title="AXIOM Engine")
        table.add_column("Dependency / setting", style="cyan")
        table.add_column("Value")
        table.add_row("Ready", "yes" if report["ready"] else "no")
        table.add_row("Model loaded", "yes" if report["loaded"] else "no")
        table.add_row("Architecture", str(report["architecture"] or "not loaded"))
        for name, installed in report["packages"].items():
            table.add_row(name, f"{'available' if installed else 'not installed'} ({report['versions'].get(name) or 'unknown version'})")
        table.add_row("Model downloads", "disabled")
        table.add_row("Remote model code", "disabled")
        console.print(table)
        if not report["ready"]:
            console.print(f"[yellow]{report['setup_note']}[/yellow]")
    if not report["ready"]:
        raise typer.Exit(code=1)


@engine_app.command("run")
def engine_run(
    model_path: Path = typer.Option(..., "--model-path", exists=True, file_okay=False, dir_okay=True, help="Existing local Llama/Mistral safetensors model directory."),
    prompt: str | None = typer.Option(None, "--prompt", help="Prompt text; mutually exclusive with --prompt-file."),
    prompt_file: Path | None = typer.Option(None, "--prompt-file", exists=True, file_okay=True, dir_okay=False, help="Read the prompt from a local UTF-8 text file."),
    adapter_path: Path | None = typer.Option(None, "--adapter-path", exists=True, file_okay=False, dir_okay=True, help="Optional local native-compatible LoRA adapter directory."),
    max_new_tokens: int = typer.Option(256, "--max-new-tokens", min=1, max=2048, help="Maximum generated tokens (1–2048)."),
    temperature: float = typer.Option(0.7, "--temperature", min=0, max=2, help="Sampling temperature; 0 disables sampling."),
    json_output: bool = typer.Option(False, "--json", help="Print response and metrics as JSON."),
) -> None:
    """Generate text locally without requiring Ollama or downloading model weights."""
    if (prompt is None) == (prompt_file is None):
        _fail("Provide exactly one of --prompt or --prompt-file.")
    if prompt_file is not None:
        try:
            with prompt_file.open("r", encoding="utf-8") as handle:
                prompt_value = handle.read(12_001)
        except (OSError, UnicodeError):
            _fail("Prompt file could not be read as UTF-8 text.")
        if len(prompt_value) > 12_000:
            _fail("Prompt file exceeds AXIOM Engine's 12,000-character limit.")
    else:
        prompt_value = prompt or ""
    try:
        result = generate_local(
            str(model_path),
            prompt_value,
            adapter_path=str(adapter_path) if adapter_path is not None else None,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
        )
    except (ValueError, AxiomEngineError) as exc:
        _fail(str(exc))
    if json_output:
        typer.echo(json.dumps(result, ensure_ascii=False, indent=2))
        return
    console.print(Panel.fit(
        f"Engine: AXIOM Native Engine\nModel: {result['model']}\nArchitecture: {result['architecture']}\n"
        f"Generated tokens: {result['completion_tokens']}\nElapsed: {result['elapsed_ms']} ms",
        title="AXIOM ENGINE",
    ))
    console.print(result["response"], markup=False)


__all__ = ["engine_app"]
