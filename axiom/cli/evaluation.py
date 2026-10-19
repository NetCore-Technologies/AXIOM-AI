"""Commands for evaluating precomputed JSONL predictions locally."""

from __future__ import annotations

import json
import math
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from axiom.evaluation.jsonl import (
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_LINE_BYTES,
    DEFAULT_MAX_ROWS,
    compare_to_baseline,
    create_output_manifest,
    evaluate_jsonl_stream,
)
from axiom.evaluation.store import EvaluationStore
from axiom.path_safety import open_regular_file
from axiom.version import __version__

console = Console()


def register_evaluation_cli(app: typer.Typer) -> None:
    @app.command("run")
    def evaluation_run(
        path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
        prediction_field: str = typer.Option(..., "--prediction-field"),
        reference_field: str = typer.Option(..., "--reference-field"),
        split_field: str | None = typer.Option(None, "--split-field"),
        split_value: str | None = typer.Option(None, "--split-value"),
        name: str | None = typer.Option(None, "--name"),
        model_label: str | None = typer.Option(None, "--model-label"),
        baseline: bool = typer.Option(False, "--baseline", help="Mark this immutable run as a comparison baseline."),
        baseline_run_id: str | None = typer.Option(None, "--baseline-run-id"),
        metric: str = typer.Option("token_f1_micro", "--regression-metric"),
        tolerance: float = typer.Option(0.05, "--regression-tolerance", min=0, max=1),
        max_bytes: int = typer.Option(DEFAULT_MAX_BYTES, min=1, max=256 * 1024 * 1024),
        max_rows: int = typer.Option(DEFAULT_MAX_ROWS, min=1, max=500_000),
        max_line_bytes: int = typer.Option(DEFAULT_MAX_LINE_BYTES, min=1, max=8 * 1024 * 1024),
        json_output: bool = typer.Option(False, "--json", help="Emit the complete report as JSON."),
    ) -> None:
        """Score existing predictions against references; no model is executed."""
        if name is not None and (not name.strip() or len(name) > 120):
            _error("Evaluation names must contain 1 to 120 characters.")
        if model_label is not None and len(model_label) > 256:
            _error("Model labels cannot exceed 256 characters.")
        if baseline_run_id is not None and (not baseline_run_id or len(baseline_run_id) > 64):
            _error("Baseline run IDs must contain 1 to 64 characters.")
        if metric not in {"exact_match", "normalized_exact_match", "token_f1_micro"}:
            _error("Choose exact_match, normalized_exact_match, or token_f1_micro as the regression metric.")
        if not math.isfinite(tolerance) or not 0 <= tolerance <= 1:
            _error("Regression tolerance must be a finite number between 0 and 1.")
        try:
            source = path.expanduser().resolve(strict=True)
            if not source.is_file() or source.suffix.casefold() != ".jsonl":
                _error("Evaluation input must be a regular .jsonl file.")
            try:
                data_root = (Path.cwd() / "data").resolve(strict=True)
                report_path = source.relative_to(data_root).as_posix()
            except (FileNotFoundError, ValueError):
                report_path = str(source)

            with open_regular_file(source) as stream:
                before = os.fstat(stream.fileno())
                report = evaluate_jsonl_stream(
                    stream,
                    path=report_path,
                    file_name=source.name,
                    file_size_bytes=before.st_size,
                    prediction_field=prediction_field,
                    reference_field=reference_field,
                    split_field=split_field,
                    split_value=split_value,
                    max_bytes=max_bytes,
                    max_rows=max_rows,
                    max_line_bytes=max_line_bytes,
                )
                after = os.fstat(stream.fileno())
                if (before.st_size, before.st_mtime_ns, before.st_ino) != (
                    after.st_size, after.st_mtime_ns, after.st_ino
                ):
                    _error("Dataset changed during evaluation; retry against a stable file.")

            store = EvaluationStore()
            comparison = None
            if baseline_run_id:
                baseline_record = store.get(baseline_run_id)
                if baseline_record is None:
                    _error(f"Baseline evaluation run not found: {baseline_run_id}")
                if baseline_record.get("baseline") is not True:
                    _error("Only a run explicitly marked as a baseline can be compared.")
                comparison = compare_to_baseline(
                    report,
                    baseline_record,
                    baseline_run_id=baseline_run_id,
                    metric=metric,
                    regression_tolerance=tolerance,
                )
        except (OSError, TimeoutError, ValueError) as exc:
            _error(str(exc))

        now = datetime.now(UTC).isoformat()
        record = {
            "schema_version": EvaluationStore.SCHEMA_VERSION,
            "id": uuid.uuid4().hex,
            "name": name or f"{source.stem} offline evaluation",
            "created_at": now,
            "model_label": model_label,
            "baseline": baseline,
            "comparison": comparison,
            "status": "partial" if report["truncated"] else "complete",
            "execution_status": "precomputed_outputs_only",
            "software": {"axiom": __version__},
            "output_manifest": create_output_manifest(report),
            "report": report,
        }
        try:
            EvaluationStore().add(record)
        except (OSError, TimeoutError, ValueError) as exc:
            _error(f"Evaluation report could not be saved: {exc}")
        if json_output:
            console.print_json(json.dumps({"run": record}, ensure_ascii=False, allow_nan=False))
            return
        console.print(f"Saved offline evaluation [cyan]{record['id']}[/cyan] · {record['status']}")
        console.print(f"Samples: {report['counts']['valid_samples']:,}")
        for metric_name, score in report["metrics"].items():
            console.print(f"{metric_name}: {score:.4f}")
        if comparison:
            console.print(f"Baseline gate: {comparison['status']} ({comparison['delta']:+.4f})")
        console.print("No model inference was run; only precomputed outputs were scored.")

    @app.command("list")
    def evaluation_list(
        limit: int = typer.Option(20, min=1, max=1000),
        offset: int = typer.Option(0, min=0, max=1_000_000),
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        """List saved offline evaluation reports."""
        try:
            page = EvaluationStore().list_page(limit=limit, offset=offset)
        except (OSError, ValueError) as exc:
            _error(f"Evaluation history is invalid: {exc}")
        runs = page["runs"]
        if json_output:
            console.print_json(json.dumps(page, ensure_ascii=False))
            return
        if not runs:
            console.print("No saved evaluation reports.")
            return
        table = Table(title="Offline evaluation reports")
        table.add_column("ID", style="cyan")
        table.add_column("Name")
        table.add_column("Samples", justify="right")
        table.add_column("Token F1", justify="right")
        table.add_column("Status")
        for run in runs:
            report = run.get("report", {})
            table.add_row(
                str(run.get("id", ""))[:12],
                str(run.get("name", "Unnamed")),
                str(report.get("counts", {}).get("valid_samples", 0)),
                f"{report.get('metrics', {}).get('token_f1_micro', 0):.4f}",
                "baseline" if run.get("baseline") else run.get("comparison", {}).get("status", run.get("status", "unknown")),
            )
        console.print(table)

    @app.command("show")
    def evaluation_show(run_id: str) -> None:
        """Show an immutable evaluation report by its ID."""
        try:
            run = EvaluationStore().get(run_id)
        except (OSError, ValueError) as exc:
            _error(f"Evaluation history is invalid: {exc}")
        if run is None:
            _error(f"Evaluation run not found: {run_id}")
        console.print_json(json.dumps(run, ensure_ascii=False))

    @app.command("delete")
    def evaluation_delete(
        run_id: str,
        yes: bool = typer.Option(False, "--yes", help="Delete without an interactive confirmation."),
    ) -> None:
        """Delete one saved evaluation report."""
        if not yes and not typer.confirm(f"Delete evaluation report {run_id}?", default=False):
            console.print("Cancelled.")
            return
        try:
            deleted = EvaluationStore().delete(run_id)
        except (OSError, TimeoutError, ValueError) as exc:
            _error(f"Evaluation history could not be updated: {exc}")
        if deleted is None:
            _error(f"Evaluation run not found: {run_id}")
        console.print_json(json.dumps({"deleted": deleted}, ensure_ascii=False))


def _error(message: str) -> Any:
    console.print(f"[red]Error:[/red] {message}")
    raise typer.Exit(code=1)
