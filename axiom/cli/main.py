import json
from pathlib import Path

import typer

from huggingface_hub import HfApi, login, logout, whoami
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from axiom.core.project import create_project
from axiom.datasets.cleaner import clean_jsonl
from axiom.datasets.inspector import inspect_dataset
from axiom.models.inspector import inspect_model
from axiom.models.analysis import analyze_config, disk_info
from axiom.models.registry import Model, ModelRegistry
from axiom.runtime.supercompress import compress_context

from axiom.training.planner import create_training_plan
from axiom.version import __version__
from axiom.core.hardware import detect_hardware, estimate_model_fit
from axiom.core.integrations import AgentIntegration, IntegrationRegistry, IntegrationType

app = typer.Typer(
    name="axiom",
    help="Build, train, evaluate, and deploy AI models.",
)

model_app = typer.Typer(help="Manage AI models.")
dataset_app = typer.Typer(help="Inspect and manage datasets.")
system_app = typer.Typer(help="Inspect system hardware and capabilities.")

hf_app = typer.Typer(help="Authenticate and manage Hugging Face access.")
supercompress_app = typer.Typer(help="Use SuperCompress before inference.")
integration_app = typer.Typer(help="Connect AXIOM to AI agents and runtimes.")
mcp_app = typer.Typer(help="Run AXIOM as an MCP server.")

app.add_typer(model_app, name="model")
app.add_typer(dataset_app, name="dataset")
app.add_typer(system_app, name="system")
app.add_typer(hf_app, name="hf")
app.add_typer(supercompress_app, name="supercompress")
app.add_typer(integration_app, name="integration")
app.add_typer(mcp_app, name="mcp")

train_app = typer.Typer(help="Plan and manage AI training jobs.")
app.add_typer(train_app, name="train")

console = Console()


@app.command()
def version():
    """Show AXIOM version."""
    console.print(f"[bold cyan]AXIOM[/bold cyan] v{__version__}")


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




@hf_app.command("login")
def hf_login():
    """Authenticate AXIOM with Hugging Face."""
    console.print(
        Panel.fit(
            "[bold cyan]AXIOM HUGGING FACE LOGIN[/bold cyan]\n\n"
            "A Hugging Face login will be started.\n"
            "Your token is handled by Hugging Face's authentication system\n"
            "and is not written into the AXIOM repository.",
            title="AXIOM",
        )
    )

    try:
        login()
    except Exception as exc:
        console.print(f"[red]Error:[/red] Hugging Face login failed: {exc}")
        raise typer.Exit(code=1)

    console.print(
        "[green]✓[/green] Hugging Face authentication configured."
    )


@hf_app.command("status")
def hf_status():
    """Show Hugging Face authentication status."""
    try:
        user = whoami()
    except Exception:
        console.print(
            Panel.fit(
                "[yellow]Not authenticated[/yellow]\n\n"
                "Run:\n"
                "  axiom hf login",
                title="AXIOM",
            )
        )
        return

    name = (
        user.get("name")
        or user.get("fullname")
        or user.get("username")
        or "Unknown"
    )

    orgs = user.get("orgs") or []

    if isinstance(orgs, list):
        organization_names = [
            item.get("name", str(item))
            if isinstance(item, dict)
            else str(item)
            for item in orgs
        ]
    else:
        organization_names = []

    console.print(
        Panel.fit(
            f"[bold green]✓ Authenticated[/bold green]\n\n"
            f"Account: {name}\n"
            f"Organizations: "
            f"{', '.join(organization_names) if organization_names else 'None'}\n\n"
            "[dim]Token value is never displayed.[/dim]",
            title="AXIOM",
        )
    )


@hf_app.command("logout")
def hf_logout():
    """Log out of Hugging Face."""
    try:
        logout()
    except Exception as exc:
        console.print(f"[red]Error:[/red] Hugging Face logout failed: {exc}")
        raise typer.Exit(code=1)

    console.print(
        "[green]✓[/green] Hugging Face authentication removed."
    )





@supercompress_app.command("status")
def supercompress_status():
    """Show SuperCompress configuration without exposing secrets."""
    import os

    configured = bool(
        os.getenv("SUPERCOMPRESS_API_KEY")
    )

    endpoint = os.getenv(
        "SUPERCOMPRESS_API_BASE",
        "https://api.supercompress.dev",
    )

    key_status = (
        "[green]configured[/green]"
        if configured
        else "[red]not configured[/red]"
    )

    console.print(
        Panel.fit(
            f"[bold cyan]AXIOM SUPERCOMPRESS[/bold cyan]\n\n"
            f"Endpoint: {endpoint}\n"
            f"API key:  {key_status}\n\n"
            "[dim]The secret value is never displayed.[/dim]",
            title="AXIOM",
        )
    )


@supercompress_app.command("compress")
def supercompress_compress(
    context_file: str,
    query: str = typer.Option(
        ...,
        "--query",
        "-q",
    ),
    budget_ratio: float = typer.Option(
        0.35,
        "--budget-ratio",
        min=0.05,
        max=1.0,
    ),
    ccr: bool = typer.Option(
        False,
        "--ccr",
        help="Enable reversible Cache-Compress-Retrieve mode.",
    ),
):
    """Compress a context file before inference."""
    path = Path(context_file)

    if not path.is_file():
        console.print(
            f"[red]Error:[/red] Context file not found: {path}"
        )
        raise typer.Exit(code=1)

    try:
        context = path.read_text(encoding="utf-8")

        result = compress_context(
            context,
            query,
            budget_ratio=budget_ratio,
            ccr=ccr,
        )

    except (OSError, RuntimeError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)

    savings = (
        f"{result.savings_pct:.1f}%"
        if result.savings_pct is not None
        else "Unknown"
    )

    console.print(
        Panel.fit(
            f"[bold cyan]AXIOM + SUPERCOMPRESS[/bold cyan]\n\n"
            f"Original tokens: "
            f"{result.original_tokens or 'Unknown'}\n"
            f"Kept tokens:     "
            f"{result.kept_tokens or 'Unknown'}\n"
            f"Tokens saved:    "
            f"{result.tokens_saved or 'Unknown'}\n"
            f"Reduction:       {savings}\n"
            f"Risk:             "
            f"{result.compression_risk or 'Unknown'}\n"
            f"Policy:           "
            f"{result.policy_name or 'Unknown'}\n"
            f"Mode:             "
            f"{result.mode or 'Unknown'}\n\n"
            f"{result.compressed_text}",
            title="AXIOM",
        )
    )


@integration_app.command("list")
def integration_list():
    """List configured AI agent integrations."""
    registry = IntegrationRegistry()
    integrations = registry.list()

    if not integrations:
        console.print(
            "[yellow]No agent integrations configured.[/yellow]"
        )
        return

    table = Table(title="AXIOM Agent Integrations")
    table.add_column("Name")
    table.add_column("Type")
    table.add_column("Target")
    table.add_column("Description")

    for item in integrations:
        target = item.command or item.url or "-"
        table.add_row(
            item.name,
            item.type.value,
            target,
            item.description or "-",
        )

    console.print(table)


@integration_app.command("add")
def integration_add(
    name: str,
    type: str = typer.Option(
        "mcp",
        "--type",
        help="Integration type: mcp, cli, http, or a2a.",
    ),
    command: str | None = typer.Option(
        None,
        "--command",
        help="Command used by CLI/MCP integrations.",
    ),
    url: str | None = typer.Option(
        None,
        "--url",
        help="URL used by HTTP/A2A integrations.",
    ),
):
    """Register an external AI agent or runtime."""
    try:
        integration_type = IntegrationType(type.lower())
    except ValueError:
        console.print(
            "[red]Error:[/red] Type must be one of: "
            "mcp, cli, http, a2a."
        )
        raise typer.Exit(code=1)

    if integration_type in {
        IntegrationType.MCP,
        IntegrationType.CLI,
    } and not command:
        console.print(
            "[red]Error:[/red] --command is required for "
            f"{integration_type.value} integrations."
        )
        raise typer.Exit(code=1)

    if integration_type in {
        IntegrationType.HTTP,
        IntegrationType.A2A,
    } and not url:
        console.print(
            "[red]Error:[/red] --url is required for "
            f"{integration_type.value} integrations."
        )
        raise typer.Exit(code=1)

    registry = IntegrationRegistry()

    try:
        registry.add(
            AgentIntegration(
                name=name,
                type=integration_type,
                command=command,
                url=url,
                description=f"AXIOM {integration_type.value} integration",
            )
        )
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)

    console.print(
        f"[green]✓[/green] Registered integration: "
        f"[cyan]{name}[/cyan]"
    )


@integration_app.command("remove")
def integration_remove(name: str):
    """Remove an agent integration."""
    registry = IntegrationRegistry()

    if not registry.remove(name):
        console.print(
            f"[yellow]Integration not found:[/yellow] {name}"
        )
        raise typer.Exit(code=1)

    console.print(
        f"[green]✓[/green] Removed integration: [cyan]{name}[/cyan]"
    )


@integration_app.command("doctor")
def integration_doctor():
    """Check whether configured integration commands exist."""
    import shutil

    registry = IntegrationRegistry()
    integrations = registry.list()

    if not integrations:
        console.print(
            "[yellow]No agent integrations configured.[/yellow]"
        )
        return

    table = Table(title="AXIOM Integration Doctor")
    table.add_column("Name")
    table.add_column("Type")
    table.add_column("Status")
    table.add_column("Target")

    for item in integrations:
        if item.command:
            executable = item.command.split()[0]
            available = shutil.which(executable) is not None

            status = (
                "[green]✓ Available[/green]"
                if available
                else "[red]✗ Not found[/red]"
            )
        elif item.url:
            status = "[cyan]Configured[/cyan]"
        else:
            status = "[yellow]Incomplete[/yellow]"

        table.add_row(
            item.name,
            item.type.value,
            status,
            item.command or item.url or "-",
        )

    console.print(table)


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



@train_app.command("plan")
def train_plan(
    parameters: float = typer.Argument(..., help="Model size in billions of parameters."),
    method: str = typer.Option(
        "auto",
        "--method",
        help="Training method: auto, qlora, lora, or full.",
    ),
):
    """Generate a hardware-aware training plan."""
    hardware = detect_hardware()

    try:
        plan = create_training_plan(
            parameter_billions=parameters,
            hardware=hardware,
            method=method.lower(),
        )
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)

    if hardware.gpu_name:
        gpu = hardware.gpu_name
        vram = (
            f"{hardware.vram_gb:.2f} GB"
            if hardware.vram_gb is not None
            else "Unknown"
        )
    else:
        gpu = "Not detected"
        vram = "N/A"

    fit = "[green]✓ FITS[/green]" if plan.fits_hardware else "[red]✗ DOES NOT FIT[/red]"

    console.print(
        Panel.fit(
            f"[bold cyan]AXIOM TRAINING PLANNER[/bold cyan]\n\n"
            f"Model:              {parameters:g}B parameters\n"
            f"Method:             {plan.method}\n\n"
            f"Hardware\n"
            f"GPU:                {gpu}\n"
            f"VRAM:               {vram}\n\n"
            f"Recommended\n"
            f"Precision:           {plan.precision}\n"
            f"LoRA rank:          {plan.lora_rank}\n"
            f"Batch size:         {plan.batch_size}\n"
            f"Grad accumulation:  {plan.gradient_accumulation}\n"
            f"Sequence length:    {plan.sequence_length}\n"
            f"Learning rate:      {plan.learning_rate:g}\n\n"
            f"Estimated VRAM:     {plan.estimated_vram_gb:.2f} GB\n"
            f"Hardware check:     {fit}\n\n"
            f"{plan.reason}",
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



@model_app.command("info")
def model_info(repo_id: str):
    """Show metadata for a Hugging Face model."""
    api = HfApi()

    try:
        info = api.model_info(repo_id=repo_id, files_metadata=True)
    except Exception as exc:
        console.print(
            f"[red]Error:[/red] Could not retrieve model information: {exc}"
        )
        raise typer.Exit(code=1)

    files = getattr(info, "siblings", None) or []

    file_names = []
    for item in files:
        name = getattr(item, "rfilename", None)
        if name:
            file_names.append(name)

    formats = set()

    for name in file_names:
        lower = name.lower()

        if lower.endswith(".safetensors"):
            formats.add("Safetensors")
        elif lower.endswith(".gguf"):
            formats.add("GGUF")
        elif lower.endswith((".bin", ".pt", ".pth")):
            formats.add("PyTorch")

    format_text = ", ".join(sorted(formats)) if formats else "Not detected"

    tags = getattr(info, "tags", None) or []
    library = getattr(info, "library_name", None) or "Unknown"
    pipeline = getattr(info, "pipeline_tag", None) or "Unknown"

    downloads = getattr(info, "downloads", 0) or 0
    likes = getattr(info, "likes", 0) or 0

    gated = getattr(info, "gated", False)
    private = getattr(info, "private", False)

    console.print(
        Panel.fit(
            f"[bold cyan]AXIOM HUGGING FACE MODEL[/bold cyan]\n\n"
            f"Repository:   {info.id}\n"
            f"Author:       {getattr(info, 'author', None) or 'Unknown'}\n"
            f"Library:      {library}\n"
            f"Task:         {pipeline}\n"
            f"Formats:      {format_text}\n"
            f"Downloads:    {downloads:,}\n"
            f"Likes:        {likes:,}\n"
            f"Gated:        {'✓' if gated else '✗'}\n"
            f"Private:      {'✓' if private else '✗'}\n\n"
            f"Files:        {len(file_names):,}\n"
            f"Tags:         {', '.join(tags[:8]) if tags else '-'}\n\n"
            "[dim]Metadata only — no model weights were downloaded.[/dim]",
            title="AXIOM",
        )
    )


@model_app.command("add-hf")
def model_add_hf(repo_id: str):
    """Discover and register a Hugging Face model."""
    api = HfApi()

    try:
        info = api.model_info(repo_id=repo_id, files_metadata=True)
    except Exception as exc:
        console.print(
            f"[red]Error:[/red] Could not retrieve model information: {exc}"
        )
        raise typer.Exit(code=1)

    files = getattr(info, "siblings", None) or []

    file_names = [
        getattr(item, "rfilename", "")
        for item in files
    ]

    formats = set()

    for name in file_names:
        lower = name.lower()

        if lower.endswith(".safetensors"):
            formats.add("safetensors")
        elif lower.endswith(".gguf"):
            formats.add("gguf")
        elif lower.endswith((".bin", ".pt", ".pth")):
            formats.add("pytorch")

    model_format = (
        ", ".join(sorted(formats))
        if formats
        else "unknown"
    )

    pipeline = getattr(info, "pipeline_tag", None)

    registry = ModelRegistry()

    try:
        registry.add(
            Model(
                name=repo_id,
                source=f"huggingface:{repo_id}",
                format=model_format,
                parameters=None,
                quantization=None,
            )
        )
    except ValueError:
        console.print(
            f"[yellow]Model already registered:[/yellow] {repo_id}"
        )
        return

    console.print(
        Panel.fit(
            f"[bold green]✓ Model discovered and registered[/bold green]\n\n"
            f"Model:    [cyan]{repo_id}[/cyan]\n"
            f"Task:     {pipeline or 'Unknown'}\n"
            f"Format:   {model_format}\n\n"
            "[dim]Weights were not downloaded.[/dim]",
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



@model_app.command("analyze")
def model_analyze(repo_id: str):
    """Analyze a Hugging Face model without downloading weights."""
    api = HfApi()

    try:
        info = api.model_info(repo_id=repo_id, files_metadata=True)
    except Exception as exc:
        console.print(
            f"[red]Error:[/red] Could not retrieve model information: {exc}"
        )
        raise typer.Exit(code=1)

    files = [
        getattr(item, "rfilename", "")
        for item in (getattr(info, "siblings", None) or [])
        if getattr(item, "rfilename", None)
    ]

    config = {}

    try:
        config_file = api.hf_hub_download(
            repo_id=repo_id,
            filename="config.json",
        )

        config_path = Path(config_file)

        if config_path.is_file():
            config = json.loads(
                config_path.read_text(encoding="utf-8")
            )
    except Exception as exc:
        console.print(
            f"[yellow]Warning:[/yellow] Could not read config.json: {exc}"
        )

    total_size = 0

    for item in (getattr(info, "siblings", None) or []):
        name = getattr(item, "rfilename", "") or ""
        size = getattr(item, "size", None)

        if size is not None and (
            name.endswith(".safetensors")
            or name.endswith(".gguf")
            or name.endswith(".bin")
            or name.endswith(".pt")
            or name.endswith(".pth")
        ):
            total_size += int(size)

    analysis = analyze_config(
        repo_id=repo_id,
        config=config,
        files=files,
        weight_size_bytes=total_size,
    )

    parameters = (
        f"{analysis.parameter_count / 1_000_000_000:.2f}B"
        if analysis.parameter_count
        else "Unknown"
    )

    context = (
        f"{analysis.context_length:,}"
        if analysis.context_length
        else "Unknown"
    )

    weight_size = (
        f"{analysis.weight_size_gb:.2f} GB"
        if analysis.weight_size_gb is not None
        else "Unknown"
    )

    console.print(
        Panel.fit(
            f"[bold cyan]AXIOM MODEL ANALYSIS[/bold cyan]\n\n"
            f"Repository:      {analysis.repo_id}\n"
            f"Architecture:    {analysis.architecture}\n"
            f"Model type:      {analysis.model_type}\n"
            f"Parameters:      {parameters}\n"
            f"Parameter basis: {analysis.parameter_source}\n"
            f"Context length:  {context}\n"
            f"Precision:       {analysis.precision}\n"
            f"Weight size:     {weight_size}\n"
            f"Files:           {analysis.file_count:,}\n\n"
            f"[dim]No model weights were downloaded.[/dim]",
            title="AXIOM",
        )
    )


@model_app.command("pull")
def model_pull(
    repo_id: str,
    max_disk_usage_gb: float = typer.Option(
        85.0,
        "--max-disk-usage",
        help="Maximum allowed disk usage percentage.",
    ),
):
    """Safely download a Hugging Face model after disk checks."""
    api = HfApi()

    try:
        info = api.model_info(repo_id=repo_id, files_metadata=True)
    except Exception as exc:
        console.print(
            f"[red]Error:[/red] Could not retrieve model information: {exc}"
        )
        raise typer.Exit(code=1)

    total_size = 0

    for item in (getattr(info, "siblings", None) or []):
        size = getattr(item, "size", None)
        name = getattr(item, "rfilename", "") or ""

        if size is not None:
            total_size += int(size)

    free_bytes, total_bytes = disk_info(".")

    used_bytes = total_bytes - free_bytes
    used_percent = (used_bytes / total_bytes) * 100 if total_bytes else 100
    download_gb = total_size / (1024 ** 3)
    free_gb = free_bytes / (1024 ** 3)
    remaining_gb = free_gb - download_gb

    console.print(
        Panel.fit(
            f"[bold cyan]AXIOM MODEL DOWNLOAD CHECK[/bold cyan]\n\n"
            f"Model:             {repo_id}\n"
            f"Repository size:   {download_gb:.2f} GB\n"
            f"Free disk:         {free_gb:.2f} GB\n"
            f"Free after pull:   {remaining_gb:.2f} GB\n"
            f"Current usage:     {used_percent:.1f}%\n"
            f"Usage limit:       {max_disk_usage_gb:.1f}%",
            title="AXIOM",
        )
    )

    if remaining_gb < 0:
        console.print(
            "[red]✗ Download blocked:[/red] insufficient disk space."
        )
        raise typer.Exit(code=1)

    projected_used_percent = (
        ((total_bytes - free_bytes + total_size) / total_bytes) * 100
        if total_bytes
        else 100
    )

    if projected_used_percent > max_disk_usage_gb:
        console.print(
            "[red]✗ Download blocked:[/red] "
            f"projected disk usage would reach {projected_used_percent:.1f}%."
        )
        raise typer.Exit(code=1)

    console.print("[green]✓ Disk safety check passed.[/green]")

    try:
        destination = snapshot_download(
            repo_id=repo_id,
            local_dir=Path("models") / repo_id.replace("/", "__"),
        )
    except Exception as exc:
        console.print(
            f"[red]Error:[/red] Model download failed: {exc}"
        )
        raise typer.Exit(code=1)

    console.print(
        f"[green]✓ Model downloaded:[/green] {destination}"
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


@mcp_app.command("serve")
def mcp_serve():
    """Run the AXIOM MCP server over stdio."""
    from axiom.mcp.server import mcp

    mcp.run()
