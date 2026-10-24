"""CLI commands for AXIOM's direct local model engine."""
from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from axiom.core.engine import AxiomEngineError, discover_local_engine_assets, generate_local, generate_local_stream, runtime_status
from axiom.core import model_studio

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
        table.add_row("Recommended device", str(report.get("recommended_device") or "none available"))
        for device in report.get("devices", []):
            value = "available" if device.get("available") else "unavailable"
            if device.get("memory_total_gib") is not None:
                value += f" ({device.get('memory_free_gib') or 0} GiB free / {device['memory_total_gib']} GiB total)"
            table.add_row(f"Device: {device.get('name', device.get('id', 'unknown'))}", value)
        table.add_row("Native model pull", "public Hugging Face safetensors via `axiom engine pull`")
        table.add_row("Remote model code", "disabled")
        console.print(table)
        if not report["ready"]:
            console.print(f"[yellow]{report['setup_note']}[/yellow]")
    if not report["ready"]:
        raise typer.Exit(code=1)


@engine_app.command("pull")
def engine_pull(
    repo_id: str = typer.Argument(..., help="Public Hugging Face repository ID, e.g. Qwen/Qwen2.5-0.5B-Instruct."),
    json_output: bool = typer.Option(False, "--json", help="Print the install result as machine-readable JSON."),
) -> None:
    """Pull compatible public Llama/Mistral/Qwen2 safetensors directly for AXIOM Native Engine."""
    try:
        result = model_studio.pull_native_model(
            repo_id,
            on_log=lambda message: console.print(message),
            on_progress=lambda current, total: console.print(
                "\rDownloaded " + f"{current:,}" + (f" / {total:,} bytes" if total else " bytes"),
                end="",
            ),
        )
    except (ValueError, model_studio.ModelStudioError) as exc:
        _fail(str(exc))
    if json_output:
        console.print()
        typer.echo(json.dumps(result, indent=2, ensure_ascii=False))
        return
    console.print("\n[green]Installed for AXIOM Native Engine:[/green] " + result["path"])
    console.print("[dim]Run it with:[/dim] axiom engine run --model-path " + repr(result["path"]) + " --prompt \"Hello.\"")

@engine_app.command("run")
def engine_run(
    model_path: Path = typer.Option(..., "--model-path", exists=True, file_okay=False, dir_okay=True, help="Existing local Llama/Mistral/Qwen2 safetensors model directory."),
    prompt: str | None = typer.Option(None, "--prompt", help="Prompt text; mutually exclusive with --prompt-file."),
    prompt_file: Path | None = typer.Option(None, "--prompt-file", exists=True, file_okay=True, dir_okay=False, help="Read the prompt from a local UTF-8 text file."),
    adapter_path: Path | None = typer.Option(None, "--adapter-path", exists=True, file_okay=False, dir_okay=True, help="Optional local native-compatible LoRA adapter directory."),
    device: str = typer.Option("auto", "--device", help="Execution backend: auto, cpu, cuda, rocm, mps, or xpu."),
    memory_mode: str = typer.Option("auto", "--memory-mode", help="Memory policy: auto (fit to observed resources), full, layer_streaming (CPU-resident layers), or disk_streaming (read one safetensors layer at a time; lowest RAM/VRAM, slowest)."),
    max_new_tokens: int = typer.Option(256, "--max-new-tokens", min=1, max=2048, help="Maximum generated tokens (1–2048)."),
    temperature: float = typer.Option(0.7, "--temperature", min=0, max=2, help="Sampling temperature; 0 disables sampling."),
    stop_sequences: list[str] = typer.Option([], "--stop-sequence", help="Stop when this exact text is generated; repeat the option for multiple stop strings."),
    json_output: bool = typer.Option(False, "--json", help="Print response and metrics as JSON."),
    stream_output: bool = typer.Option(False, "--stream", help="Show decoded output updates while the model generates."),
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
    if json_output and stream_output:
        _fail("--stream cannot be combined with --json; JSON mode emits one complete result.")
    try:
        adapter_value = str(adapter_path) if adapter_path is not None else None
        if stream_output:
            result = None
            events = generate_local_stream(
                str(model_path),
                prompt_value,
                adapter_path=adapter_value,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                stop_sequences=stop_sequences,
                device_preference=device,
                memory_mode=memory_mode,
            )
            try:
                with Live(console=console, refresh_per_second=12, transient=False) as live:
                    for event in events:
                        if event.get("type") == "token":
                            visible = event.get("response") or "(Waiting for printable output…)"
                            live.update(Panel(Text(str(visible), overflow="fold"), title="AXIOM ENGINE · LIVE OUTPUT"))
                        elif event.get("type") == "complete" and isinstance(event.get("result"), dict):
                            result = event["result"]
                            visible = result.get("response") or "(The model returned an empty response.)"
                            live.update(Panel(Text(str(visible), overflow="fold"), title="AXIOM ENGINE · COMPLETE"))
            finally:
                close = getattr(events, "close", None)
                if callable(close):
                    close()
            if result is None:
                _fail("Native generation ended before a completion event was produced.")
        else:
            result = generate_local(
                str(model_path),
                prompt_value,
                adapter_path=adapter_value,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                stop_sequences=stop_sequences,
                device_preference=device,
                memory_mode=memory_mode,
            )
    except (ValueError, AxiomEngineError) as exc:
        _fail(str(exc))
    if json_output:
        typer.echo(json.dumps(result, ensure_ascii=False, indent=2))
        return
    device_selection = result.get("device_selection") if isinstance(result.get("device_selection"), dict) else {}
    actual_device = device_selection.get("selected", result.get("device", "unknown"))
    device_reason = device_selection.get("reason", "")
    console.print(Panel.fit(
        f"Engine: AXIOM Native Engine\nModel: {result['model']}\nArchitecture: {result['architecture']}\n"
        f"Execution device: {actual_device}\nMemory mode: {result.get('memory_mode', memory_mode)}\n"
        f"{device_reason + chr(10) if device_reason else ''}"
        f"Generated tokens: {result['completion_tokens']}\nFinish reason: {result.get('stop_reason', 'unknown')}\nElapsed: {result['elapsed_ms']} ms",
        title="AXIOM ENGINE",
    ))
    if not stream_output:
        console.print(result["response"], markup=False)


__all__ = ["engine_app"]
