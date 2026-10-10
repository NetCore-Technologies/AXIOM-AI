"""Dataset profile CLI command."""
from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table
from axiom.datasets.profiler import profile_jsonl
console=Console()
def register(dataset_app: typer.Typer) -> None:
 @dataset_app.command("profile")
 def dataset_profile(path: Path=typer.Argument(...,exists=True,dir_okay=False,readable=True), max_rows: int=typer.Option(100000,min=1), max_mb: int=typer.Option(64,min=1)) -> None:
  """Profile JSONL rows, duplicates, field types and possible privacy risks."""
  if path.suffix.lower()!=".jsonl": raise typer.BadParameter("Only .jsonl files are supported.")
  try: report=profile_jsonl(path,max_rows=max_rows,max_bytes=max_mb*1024*1024)
  except (OSError,ValueError) as exc: console.print(f"[red]Profile failed:[/red] {exc}"); raise typer.Exit(code=1) from exc
  table=Table(title="AXIOM DATASET PROFILE"); table.add_column("Metric"); table.add_column("Value",justify="right")
  for key in ("valid_rows","invalid_rows","empty_rows","duplicate_rows","unique_fields_tracked","bytes_scanned"): table.add_row(key.replace("_"," ").title(),str(report[key]))
  console.print(table)
  if report["possibly_sensitive_fields"]: console.print("[yellow]Privacy review:[/yellow] "+", ".join(report["possibly_sensitive_fields"]))
  for warning in report["warnings"]: console.print(f"[yellow]Warning:[/yellow] {warning}")
