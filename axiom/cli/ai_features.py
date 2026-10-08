from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from axiom.api.huggingface import search_models
from axiom.api.optimization import plan_optimization
from axiom.api.policy_audit import audit_model

ai_app = typer.Typer(help="AI optimization, Hugging Face, and model auditing.")

console = Console()


@ai_app.command("plan")
def plan(
    model: str = typer.Option(..., "--model"),
    agent_type: str = typer.Option("general-agent", "--type"),
    use_case: str = typer.Option("assistant", "--use-case"),
    privacy: str = typer.Option("local", "--privacy"),
    latency: str = typer.Option("low", "--latency"),
    target_tps: float = typer.Option(10.0, "--target-tps"),
    seq_len: int = typer.Option(2048, "--seq-len"),
    quantization: str = typer.Option("auto", "--quantization"),
):
    """Build a hardware-aware model optimization plan."""
    result = plan_optimization(
        model=model,
        agent_type=agent_type,
        use_case=use_case,
        privacy=privacy,
        latency=latency,
        target_tokens_per_second=target_tps,
        sequence_length=seq_len,
        quantization=quantization,
    )

    table = Table(title="AXIOM Agent Model Plan")
    table.add_column("Setting")
    table.add_column("Value")

    table.add_row("Model", result.model)
    table.add_row("Agent", result.agent_type)
    table.add_row("Use case", result.use_case)
    table.add_row("Privacy", result.privacy)
    table.add_row("Latency", result.latency)
    table.add_row("Target", f"{result.target_tokens_per_second:g} tok/s")
    table.add_row("Parameters", f"{result.estimated_parameters_b:.2f}B")
    table.add_row("Memory", f"{result.estimated_memory_gb:.2f} GB")
    table.add_row("Format", result.recommended_format)
    table.add_row("Quantization", result.recommended_quantization)
    table.add_row("Sequence", str(result.sequence_length))
    table.add_row("Memory fit", "PASS" if result.fits_estimate else "TIGHT")

    console.print(table)

    for note in result.notes:
        console.print(f"- {note}")


@ai_app.command("hf-search")
def hf_search(
    query: str,
    limit: int = typer.Option(10, "--limit"),
):
    """Search Hugging Face models."""
    results = search_models(query, limit)

    if results and "error" in results[0]:
        raise typer.BadParameter(results[0]["error"])

    table = Table(title=f"Hugging Face: {query}")
    table.add_column("Model")
    table.add_column("Downloads")
    table.add_column("Likes")
    table.add_column("Task")

    for result in results:
        table.add_row(
            str(result.get("id") or ""),
            str(result.get("downloads") or "-"),
            str(result.get("likes") or "-"),
            str(result.get("pipeline_tag") or "-"),
        )

    console.print(table)


@ai_app.command("policy-audit")
def policy_audit(model_path: str):
    """Audit policy/safety indicators without modifying the model."""
    try:
        result = audit_model(model_path)
    except FileNotFoundError:
        raise typer.BadParameter(f"Model path does not exist: {model_path}")

    console.print(Panel(json.dumps(result, indent=2), title="AXIOM Model Policy Audit"))
    console.print(
        "[yellow]Audit only:[/yellow] AXIOM does not remove or bypass model safety controls."
    )
