import typer
from rich.console import Console

app = typer.Typer(
    name="axiom",
    help="Build, train, evaluate, and deploy AI models."
)

console = Console()


@app.command()
def version():
    """Show AXIOM version."""
    console.print("[bold cyan]AXIOM[/bold cyan] v0.1.0")


@app.command()
def create(name: str):
    """Create a new AXIOM project."""
    console.print(f"[bold cyan]AXIOM[/bold cyan] creating project: {name}")
    console.print("Project scaffolding coming next.")


if __name__ == "__main__":
    app()
