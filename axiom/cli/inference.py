"""CLI commands for actual local model inference through Ollama."""
from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from axiom.core.inference import InferenceRuntimeError, run_local_inference, runtime_status

infer_app = typer.Typer(help="Run bounded local inference through Ollama.", no_args_is_help=True)
console = Console()


def _fail(message: str) -> None:
    console.print(f"[red]Error:[/red] {message}")
    raise typer.Exit(code=1)


@infer_app.command("status")
def infer_status(json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON.")) -> None:
    """Check whether the local Ollama API responds and list loaded model names."""
    report = runtime_status()
    if json_output:
        console.print_json(json.dumps(report, ensure_ascii=False))
        return
    table = Table(title="Local inference runtime")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("Backend", "Ollama")
    table.add_row("Endpoint", report["endpoint"])
    table.add_row("Executable on PATH", "yes" if report["runtime_installed"] else "no")
    table.add_row("API status", str(report["status"]).upper())
    table.add_row("Local models", str(len(report["models"])))
    console.print(table)
    for name in report["models"]:
        console.print(f"  • {name}")
    if report["error"]:
        console.print(f"[yellow]{report['error']}[/yellow]")
        raise typer.Exit(code=1)


@infer_app.command("models")
def infer_models(json_output: bool = typer.Option(False, "--json", help="Print model names as JSON.")) -> None:
    """List models registered with the local Ollama service."""
    report = runtime_status()
    if report["status"] != "online":
        _fail(report["error"] or "The local Ollama runtime is offline.")
    if json_output:
        console.print_json(json.dumps({"models": report["models"]}, ensure_ascii=False))
        return
    if not report["models"]:
        console.print("No local Ollama models found. Pull one, for example: ollama pull qwen2.5:0.5b")
        return
    for name in report["models"]:
        console.print(name)


@infer_app.command("run")
def infer_run(
    model: str = typer.Argument(..., help="Name of an already-downloaded local Ollama model."),
    prompt: str | None = typer.Option(None, "--prompt", help="Prompt text (up to 12,000 characters)."),
    prompt_file: Path | None = typer.Option(None, "--prompt-file", exists=True, dir_okay=False, readable=True, help="Read the prompt from a local UTF-8 text file."),
    num_predict: int = typer.Option(256, "--num-predict", min=1, max=2_048, help="Maximum generated tokens (1–2048)."),
    temperature: float = typer.Option(0.7, min=0, max=2, help="Sampling temperature (0–2)."),
    json_output: bool = typer.Option(False, "--json", help="Print the complete result as JSON."),
) -> None:
    """Run real text generation on the local Ollama runtime; no cloud API is used."""
    if (prompt is None) == (prompt_file is None):
        _fail("Supply exactly one of --prompt or --prompt-file.")
    if prompt_file is not None:
        try:
            if prompt_file.stat().st_size > 48_000:
                _fail("Prompt file is too large; maximum UTF-8 file size is 48 KB.")
            prompt = prompt_file.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            _fail(f"Could not read prompt file ({type(exc).__name__}).")
    assert prompt is not None
    try:
        result = run_local_inference(model, prompt, num_predict=num_predict, temperature=temperature)
    except (ValueError, InferenceRuntimeError) as exc:
        _fail(str(exc))
    if json_output:
        console.print_json(json.dumps(result, ensure_ascii=False))
        return
    metrics = []
    if result["eval_count"] is not None:
        metrics.append(f"{result['eval_count']} generated tokens")
    if result["total_duration_ms"] is not None:
        metrics.append(f"{result['total_duration_ms']} ms total runtime")
    console.print(Panel(result["response"] or "(The model returned an empty response.)", title=f"{result['model']} · local inference"))
    if metrics:
        console.print(" · ".join(metrics))
