"""CLI commands for inspecting locally saved workflow designs."""

from __future__ import annotations

import json
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from axiom.core.workflows import WorkflowStore, validate_workflow_graph

console = Console()


def register_workflow_cli(app: typer.Typer) -> None:
    @app.command("list")
    def workflow_list(
        limit: int = typer.Option(100, min=1, max=1000, help="Maximum workflows to show."),
        json_output: bool = typer.Option(False, "--json", help="Emit workflow records as JSON."),
    ) -> None:
        """List saved, non-executable workflow designs."""
        try:
            workflows = [
                {**workflow, "execution_status": "not_executable"}
                for workflow in WorkflowStore().list(limit)
            ]
        except (OSError, ValueError) as exc:
            _error(f"Workflow history is invalid: {exc}")
        if json_output:
            console.print_json(json.dumps(workflows, ensure_ascii=False))
            return
        if not workflows:
            console.print("No saved workflows. Create one in the Control Center first.")
            return

        table = Table(title="Saved workflow designs")
        table.add_column("ID", style="cyan")
        table.add_column("Name")
        table.add_column("Revision", justify="right")
        table.add_column("Nodes", justify="right")
        table.add_column("Status")
        for workflow in workflows:
            table.add_row(
                str(workflow.get("id", ""))[:12],
                str(workflow.get("name", "Unnamed")),
                str(workflow.get("revision", 1)),
                str(len(workflow.get("nodes", []))),
                "design only",
            )
        console.print(table)

    @app.command("show")
    def workflow_show(
        workflow_id: str,
        json_output: bool = typer.Option(False, "--json", help="Emit the complete workflow record as JSON."),
    ) -> None:
        """Show a saved workflow design by its ID."""
        try:
            workflow = WorkflowStore().get(workflow_id)
        except (OSError, ValueError) as exc:
            _error(f"Workflow history is invalid: {exc}")
        if workflow is None:
            _error(f"Workflow not found: {workflow_id}")
        workflow = {**workflow, "execution_status": "not_executable"}
        if json_output:
            console.print_json(json.dumps(workflow, ensure_ascii=False))
            return
        console.print_json(json.dumps({
            "id": workflow["id"],
            "name": workflow["name"],
            "revision": workflow.get("revision", 1),
            "nodes": workflow["nodes"],
            "edges": workflow["edges"],
            "execution_status": "not_executable",
        }, ensure_ascii=False))

    @app.command("validate")
    def workflow_validate(workflow_id: str) -> None:
        """Validate a saved graph without running any workflow steps."""
        try:
            workflow = WorkflowStore().get(workflow_id)
        except (OSError, ValueError) as exc:
            _error(f"Workflow history is invalid: {exc}")
        if workflow is None:
            _error(f"Workflow not found: {workflow_id}")
        try:
            validate_workflow_graph(workflow["name"], workflow["nodes"], workflow["edges"])
        except (KeyError, TypeError, ValueError) as exc:
            _error(f"Workflow graph is invalid: {exc}")
        console.print_json(json.dumps({
            "id": workflow_id,
            "valid": True,
            "node_count": len(workflow["nodes"]),
            "connection_count": len(workflow["edges"]),
            "execution_status": "not_executable",
        }))


def _error(message: str) -> Any:
    console.print(f"[red]Error:[/red] {message}")
    raise typer.Exit(code=1)
