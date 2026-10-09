# AXIOM

![AXIOM. Build AI. Own AI.](docs/assets/banner.svg)

[![Status](https://img.shields.io/badge/status-active%20development-22c55e?style=flat-square&labelColor=0f172a)](https://github.com/NetCore-Technologies/AXIOM-AI)
[![Version](https://img.shields.io/badge/version-v0.2.0--beta.7-0ea5e9?style=flat-square&labelColor=0f172a)](https://github.com/NetCore-Technologies/AXIOM-AI/releases)
[![License](https://img.shields.io/badge/license-MIT-7c3aed?style=flat-square&labelColor=0f172a)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?style=flat-square&labelColor=0f172a&logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-475569?style=flat-square&labelColor=0f172a)](https://github.com/NetCore-Technologies/AXIOM-AI/releases)
[![Stars](https://img.shields.io/github/stars/NetCore-Technologies/AXIOM-AI?style=flat-square&labelColor=0f172a&color=f59e0b)](https://github.com/NetCore-Technologies/AXIOM-AI)

**AXIOM** is a local-first CLI and loopback daemon that helps you understand AI
work before you run it: inspect the model, validate the data, read the machine,
and choose the next command.

It keeps project files and local model metadata on your machine. The terminal
is the product. Running bare `axiom` prints the useful command list and starts a
local daemon on a free loopback port. `axiom daemon` starts only that daemon for
scripts and integrations. AXIOM does not execute training or serve model
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
- Start the dependency-free local daemon on a free loopback port and inspect
  its `/health`, `/api/info`, `/api/summary`, `/api/actions`, `/api/hardware`,
  and `/api/tools` endpoints.

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

The shell installer uses the latest verified Linux x86_64 tarball when one is
available. That bundle keeps the runtime unpacked between launches, so the
CLI and daemon start without the repeated extraction cost of a one-file
binary. macOS and non-x86 Linux use an isolated Python environment and
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
Bare `axiom` is the interactive entry point: it prints the most useful
commands, starts the local daemon, and stays open until you press Ctrl-C.

```bash
# 1. Learn the local workflow
axiom --help
# Prints the commands, then starts the local daemon. Press Ctrl-C when done.
axiom
axiom guide
axiom summary

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

When a script or integration needs only the local HTTP boundary, run this in a
separate terminal. It prints a URL such as `http://127.0.0.1:53142`; stop it
with Ctrl-C:

```bash
axiom daemon
```

`axiom model inspect` expects a local model directory. The dataset commands
currently support `.jsonl`. `axiom dataset validate` exits non-zero when it
finds invalid records; `axiom dataset clean` writes a new file and leaves the
input untouched.

`axiom train plan` takes model size in billions of parameters. Its VRAM and
fit values are conservative planning estimates, not measured runtime usage,
and the command does not start training.

The daemon is loopback-only by default. Its JSON routes expose actionable
commands, detected hardware, and executable presence without reading API-key
values or sending project files anywhere.

## MCP tools

Start the stdio server from an MCP client configuration:

```bash
axiom mcp serve
```

The shipped server exposes `axiom_info`, `axiom_model_list`,
`axiom_model_info`, `axiom_dataset_inspect`, `axiom_dataset_clean`,
`axiom_system_info`, `axiom_training_plan`, `axiom_supercompress_status`, and
`axiom_supercompress`. It is a local process, not an HTTP endpoint.

## Developer tools

AXIOM keeps optional developer-tool setup visible and reviewable:

```bash
axiom tools list
axiom tools doctor
axiom tools plan opencode
axiom tools install opencode       # preview only
axiom tools install opencode --yes
```

The catalog covers Codex, Claude Code, Antigravity CLI, GitHub Copilot CLI,
Freebuff, Cursor Agent, free-pi, OpenCode, Gemini, OpenRouter, and z.ai GLM.
Package-manager installs are opt-in; remote installer scripts, SDK-only
providers, and API-key setup are shown for review instead of being executed or
stored by AXIOM. Successful package installs can add a detected user-level bin
directory to the user's shell profile without touching system PATH.

For long-running local work, use a bounded cross-platform keep-awake session:

```bash
axiom session --keep-awake --minutes 60
```

The session uses the host's native helper and releases it on exit.

## CLI surface

```text
axiom version                         Show the installed version
axiom init <name>                     Create a local project scaffold
axiom guide                           Explain the current project state
axiom summary                         Show project, machine, tools, and next action
axiom check                           Check standard project paths
axiom status                          Show local config and Git status
axiom info                            Show the local Python environment
axiom doctor                          Check common local tools
axiom daemon                          Run the local daemon on a free port

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
- Dependency-free loopback daemon with health and local capability info routes

### Foundations and roadmap items

These are not live services in the current repository:

- Training execution, job management, checkpoints, and experiment tracking
- Model inference, production serving, streaming, batching, and an
  OpenAI-compatible API. The optimizer prepares bundles; it is not a serving
  engine.
- Automated evaluation runners, benchmark pipelines, model comparison, and
  regression reports
- Live telemetry, request tracing, GPU monitoring, and metrics export
- Hosted deployment, collaboration, and cloud workspaces

## Architecture

```text
axiom/
├── cli/          Typer command surface
├── api/          Internal planning and safety adapters
├── core/         Project, hardware, storage, and integration helpers
├── models/       Local registry, inspection, and metadata analysis
├── datasets/     JSONL inspection and cleaning
├── training/     Hardware-aware plan generation
├── optimizer/     Agent workload plans and runtime bundles
├── runtime/      Optional runtime integrations such as SuperCompress
├── daemon.py      Dependency-free loopback HTTP daemon
└── mcp/          Stdio MCP server and tools
```

The primary executable boundary is the Python CLI and its local daemon:

```bash
axiom daemon
```

The daemon binds to `127.0.0.1` and asks the operating system for a free port
when no port is supplied. It exposes `GET /`, `GET /health`, `GET /api/info`,
`GET /api/summary`, `GET /api/actions`, `GET /api/hardware`, and
`GET /api/tools`; it is not a hosted AXIOM service or a general inference
server. Use `--allow-network` only when you intentionally need a non-loopback
bind.

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

Built by [Manit Arora](https://github.com/manit6752025) and
[Rangan V Balaji](https://github.com/TaxCollector23).

[Website](https://netcore-technologies.github.io/AXIOM-AI/)

**AXIOM. Build AI. Own AI.**

## AXIOM v0.2.0-beta.7

Optimizer/quantization planning, security hardening and E2E release verification. [Release notes](docs/releases/v0.2.0-beta.7.md).

## AXIOM v0.2.0-beta.5 macOS DMG

The release workflow packages separate macOS Apple Silicon (arm64) and Intel (x86_64) DMGs. Each contains the AXIOM CLI executable and compiled Control Center frontend, plus a SHA-256 checksum. The DMGs are currently unsigned and not notarized; API-backed UI features require a separately running/configured AXIOM backend. See `docs/releases/v0.2.0-beta.5.md` for release details.
