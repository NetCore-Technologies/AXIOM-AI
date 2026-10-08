# AXIOM

![AXIOM. Build AI. Own AI.](docs/assets/banner.svg)

[![Status](https://img.shields.io/badge/status-active%20development-22c55e?style=flat-square&labelColor=0f172a)](https://github.com/NetCore-Technologies/AXIOM-AI)
[![Version](https://img.shields.io/badge/version-v0.2.0--beta.5-0ea5e9?style=flat-square&labelColor=0f172a)](https://github.com/NetCore-Technologies/AXIOM-AI/releases)
[![License](https://img.shields.io/badge/license-MIT-7c3aed?style=flat-square&labelColor=0f172a)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?style=flat-square&labelColor=0f172a&logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-475569?style=flat-square&labelColor=0f172a)](https://github.com/NetCore-Technologies/AXIOM-AI/releases)
[![Stars](https://img.shields.io/github/stars/NetCore-Technologies/AXIOM-AI?style=flat-square&labelColor=0f172a&color=f59e0b)](https://github.com/NetCore-Technologies/AXIOM-AI)

**AXIOM** is a local-first CLI for inspecting models, checking datasets,
planning hardware-fit training, and exposing those operations through MCP
tools.

It keeps project files and local model metadata on your machine. The current
beta ships the Python CLI, a stdio MCP server, and a small optional local API
for optimizer and audit routes; it does not execute training or serve model
inference yet.

[**Install from the terminal**](#install) ·
[**Website**](https://netcore-technologies.github.io/AXIOM-AI/) ·
[**Contributing**](CONTRIBUTING.md)

---

## What ships today

The useful path is terminal-first and local:

- Inspect local model directories and files, register model metadata, and
  estimate model fit.
- Inspect, validate, clean, and summarize JSONL datasets without changing the
  source during cleaning.
- Detect local CPU, RAM, GPU, and VRAM, then generate a hardware-aware training
  plan.
- Build agent-workload optimization plans and local runtime bundles. Throughput
  targets remain targets until a supported local runtime measures them.
- Authenticate with Hugging Face and optionally inspect or pull remote model
  repositories.
- Run the AXIOM MCP server over stdio for model, dataset, hardware,
  training-plan, and optional SuperCompress tools.
- Optionally run the local FastAPI contract for health, hardware and optimizer
  plans, model optimization, and read-only policy audits.

AXIOM stores project configuration in `axiom.yaml` and local registry state in
`.axiom`. Core inspection and planning commands do not require a hosted AXIOM
account or API.

## Install

### macOS and Linux

<!-- markdownlint-disable MD013 -->
```bash
curl -fsSL https://raw.githubusercontent.com/NetCore-Technologies/AXIOM-AI/main/installers/install.sh | bash
axiom version
```
<!-- markdownlint-enable MD013 -->

The shell installer uses the latest Linux x86_64 release when one is
available. macOS and non-x86 Linux use an isolated Python environment and
install from the repository; those paths require Python 3.11+.

The command is linked at `~/.local/bin/axiom`. If the installer tells you that
directory is not on `PATH`, run the printed export command or open a new shell
after adding it.

### Windows PowerShell

<!-- markdownlint-disable MD013 -->
```powershell
irm https://raw.githubusercontent.com/NetCore-Technologies/AXIOM-AI/main/installers/install.ps1 | iex
```
<!-- markdownlint-enable MD013 -->

Restart PowerShell, then verify:

```powershell
axiom version
```

The Windows installer downloads the latest non-draft release to
`%LOCALAPPDATA%\AXIOM` and adds that directory to the user `PATH`.

## First five minutes

Run these from a terminal. `axiom --help` prints the complete command list.

The current CLI guidance update also provides the bare `axiom` welcome and
`axiom guide`. On a beta.5 binary before that update, skip those two lines and
continue with `axiom init`.

```bash
# 1. Learn the local workflow
axiom --help
# Current CLI guidance build:
axiom
axiom guide

# 2. Create and validate a project
axiom init my-ai
cd my-ai
# Current CLI guidance build:
axiom guide
axiom project validate
axiom config validate

# 3. Register metadata, then inspect a model directory when you have one
axiom model add my-model local --format safetensors
axiom model list
axiom model inspect ./models/my-model

# 4. Check a JSONL training dataset
axiom dataset inspect ./data/train.jsonl
axiom dataset validate ./data/train.jsonl
axiom dataset stats ./data/train.jsonl
axiom dataset clean ./data/train.jsonl --output ./data/train.cleaned.jsonl

# 5. Inspect hardware and plan a training configuration
axiom system info
axiom train plan 7 --method qlora
```

`axiom model inspect` expects a local model directory. The dataset commands
currently support `.jsonl`. `axiom dataset validate` exits non-zero when it
finds invalid records; `axiom dataset clean` writes a new file and leaves the
input untouched.

`axiom train plan` takes model size in billions of parameters. Its VRAM and
fit values are conservative planning estimates, not measured runtime usage,
and the command does not start training.

`axiom guide` and the bare `axiom` welcome are local-only CLI conveniences.

## MCP tools

Start the stdio server from an MCP client configuration:

```bash
axiom mcp serve
```

The shipped server exposes `axiom_info`, `axiom_model_list`,
`axiom_model_info`, `axiom_dataset_inspect`, `axiom_dataset_clean`,
`axiom_system_info`, `axiom_training_plan`, `axiom_supercompress_status`, and
`axiom_supercompress`. It is a local process, not an HTTP endpoint.

## CLI surface

```text
axiom version                         Show the installed version
axiom init <name>                     Create a local project scaffold
axiom guide                           Explain the current project state
axiom check                           Check standard project paths
axiom status                          Show local config and Git status
axiom info                            Show the local Python environment
axiom doctor                          Check common local tools

axiom model list                      List registered models
axiom model add <name> <source>       Register local model metadata
axiom model info <repo>               Read Hugging Face model metadata
axiom model add-hf <repo>             Discover and register a Hugging Face model
axiom model analyze <repo>            Analyze remote model metadata without weights
axiom model pull <repo>               Download after disk-safety checks
axiom model inspect <path>            Inspect a local model directory
axiom model search <query>            Search local model paths

axiom dataset inspect <path>          Inspect a JSONL dataset
axiom dataset validate <path>         Check JSONL records and duplicates
axiom dataset clean <path>            Write a cleaned JSONL copy
axiom dataset stats <path>            Show counts and a rough token estimate

axiom system info                     Show detected hardware
axiom train plan <billions>           Generate a hardware-aware plan
axiom ai plan --model <repo-or-path>  Plan an agent workload around a model
axiom ai hf-search <query>            Search Hugging Face models
axiom ai policy-audit <path>          Audit model policy indicators
axiom optimize profiles               List agent optimization profiles
axiom optimize run                    Build a local runtime bundle
axiom project info                    Show project markers
axiom project validate                Check the standard project structure
axiom config show                     Print axiom.yaml
axiom config validate                 Check axiom.yaml
axiom mcp serve                       Run the stdio MCP server
```

Hugging Face commands need network access and, for gated or private
repositories, Hugging Face authentication via `axiom hf login`. The local
inspection, project, dataset, and planning paths do not need that login.

## Shipped versus planned

### Shipped in the beta

- Python package and Typer CLI
- Local project scaffolding and validation
- Local model registry, model inspection, metadata analysis, and disk-checked
  pulls
- JSONL inspection, validation, cleaning, duplicate detection, statistics, and
  token estimates
- CPU/GPU detection and hardware-aware LoRA, QLoRA, and full-training planning
- Agent optimization plans, runtime-bundle preparation, and policy-audit
  commands
- Hugging Face access, integration registry, optional SuperCompress integration,
  and stdio MCP tooling
- Optional local FastAPI routes for health, hardware and optimizer plans,
  model optimization, and policy audits

### Foundations and roadmap items

These are not live services in the current repository:

- Training execution, job management, checkpoints, and experiment tracking
- Model inference, production serving, streaming, batching, and an
  OpenAI-compatible API. The optimizer prepares bundles; it is not a serving
  engine.
- Automated evaluation runners, benchmark pipelines, model comparison, and
  regression reports
- Live telemetry, request tracing, GPU monitoring, and metrics export
- Broader frontend/API contracts for model, dataset, training, evaluation,
  runtime, and log inventory pages
- Hosted deployment, collaboration, and cloud workspaces

## Architecture

```text
axiom/
├── cli/          Typer command surface
├── api/          Optional local FastAPI routes
├── core/         Project, hardware, storage, and integration helpers
├── models/       Local registry, inspection, and metadata analysis
├── datasets/     JSONL inspection and cleaning
├── training/     Hardware-aware plan generation
├── optimizer/     Agent workload plans and runtime bundles
├── runtime/      Optional runtime integrations such as SuperCompress
└── mcp/          Stdio MCP server and tools

src/              React Control Center frontend
```

The primary executable boundary is the Python CLI and stdio MCP server. The
repository also contains an optional local FastAPI app at
`axiom.api.server:create_app`, with health, optimizer-plan, model-optimization,
and policy-audit routes. Start it with `uvicorn` when the API dependencies are
installed:

```bash
uvicorn axiom.api.server:create_app --factory --host 127.0.0.1 --port 8000
```

This API is local and narrow; it is not a hosted AXIOM service or a general
inference server. The Control Center uses the current optimizer and health
contract, while broader model, dataset, training, evaluation, runtime, and log
surfaces remain placeholders until their API contracts are implemented.

## Principles

- **Local first:** Keep models, datasets, configuration, and first-pass
  decisions close to the machine that will run them.
- **Evidence before execution:** Inspection and planning should make assumptions
  visible before a training run.
- **Modular by design:** Use the CLI, project files, and MCP tools
  independently.
- **Honest boundaries:** Estimates and foundations are labeled as such; they
  are not presented as measured runtime behavior.

## Contributing

AXIOM is in active beta development. Bug fixes, tests, documentation, and
tooling improvements are welcome.

Read [CONTRIBUTING.md](CONTRIBUTING.md) before making a larger change.

## License

MIT. See [LICENSE](LICENSE).

Built by [@manit6752025](https://github.com/manit6752025) and
[contributors](https://github.com/NetCore-Technologies/AXIOM-AI/graphs/contributors).

[Website](https://netcore-technologies.github.io/AXIOM-AI/)

**AXIOM. Build AI. Own AI.**
