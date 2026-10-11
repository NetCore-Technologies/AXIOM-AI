# AXIOM

<!-- AXIOM-BETA1-UPDATE:START -->
## AXIOM AI v0.3.0-beta.1 — Feature update

**Build AI. Own AI.**

AXIOM is a local-first AI engineering platform with a Python CLI, local
workspace APIs and a React-based GUI.

### Beta foundations

- **Dataset profiling:** bounded JSONL scanning, row statistics, duplicate
  detection, field type/null summaries and potential sensitive-field-name
  warnings.
- **Workspace APIs:** foundations for dataset discovery, profiling, runtime
  information and training plans.
- **Model engineering:** existing model inspection, registry, optimisation,
  agent-profile and quantization components.
- **GUI:** Dashboard, Models, Datasets, Training, Evaluation, Runtime, MCP,
  Diagnostics and Logs sections.

Feature availability depends on installed version, backend support, hardware
and platform. The list above describes foundations, not a claim that every
planned end-to-end feature is complete.

### Install

    python -m pip install axiom-all

    axiom --help
    axiom init my-first-ai

See the [roadmap](ROADMAP.md), [feature implementation plan](docs/Feature-Implementation-Plan.md),
[release notes](docs/releases/v0.3.0-beta.1.md), and
[GitHub Wiki](https://github.com/NetCore-Technologies/AXIOM-AI/wiki).
<!-- AXIOM-BETA1-UPDATE:END -->

![AXIOM. Build AI. Own AI.](docs/assets/banner.svg)

[![Status](https://img.shields.io/badge/status-active%20development-22c55e?style=flat-square&labelColor=0f172a)](https://github.com/NetCore-Technologies/AXIOM-AI)
[![Version](https://img.shields.io/badge/version-v0.3.0--beta.1-f59e0b?style=flat-square&labelColor=0f172a)](https://github.com/NetCore-Technologies/AXIOM-AI/releases)
[![License](https://img.shields.io/badge/license-MIT-7c3aed?style=flat-square&labelColor=0f172a)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?style=flat-square&labelColor=0f172a&logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-475569?style=flat-square&labelColor=0f172a)](https://github.com/NetCore-Technologies/AXIOM-AI/releases)

AXIOM is a local-first CLI for answering the questions that come before a
local AI job:

- What is in this model directory?
- Is this JSONL dataset structurally usable?
- What hardware is available on this machine?
- What is a reasonable starting plan?

It inspects local files, keeps small amounts of project metadata, reports what
is available on the current machine, and suggests the next command. The
terminal is the product. The optional daemon exposes the same local context as
small JSON responses on a loopback address.

Project configuration lives in `axiom.yaml`; the local model registry lives in
`.axiom`. Core inspection and planning do not require an AXIOM account.

AXIOM does not execute training, run model inference, or provide a hosted
workspace. Estimates and plans are labeled as estimates and plans; they are
not benchmark results.

[**Start in 60 seconds**](#start-in-60-seconds) ·
[**Install**](#install) ·
[**Website**](https://netcore-technologies.github.io/AXIOM-AI/) ·
[**Contributing**](CONTRIBUTING.md)

## Start in 60 seconds

After installation, run:

```bash
axiom --help
axiom guide
axiom summary
```

For the interactive entry point, run bare `axiom`. In an interactive
terminal it prints the startup mark once for that terminal session, shows the
useful command path, starts the local daemon on a free port, and stays attached
until Ctrl-C. `axiom --help`, `axiom guide`, and `axiom summary` do not start
the daemon.

From a new project directory:

```bash
axiom init my-ai
cd my-ai
axiom project validate
axiom config validate
```

Then use the command that answers your next question:

| Question | Command | What it tells you |
| --- | --- | --- |
| What is this local model? | `axiom model inspect ./models/my-model` | Format, files, architecture hints, weight size, and conservative fit information. |
| What model metadata is published? | `axiom model info org/model` | Hugging Face metadata without downloading weights. Network access is required. |
| Is this dataset valid JSONL? | `axiom dataset validate ./data/train.jsonl` | Invalid records and duplicate objects; exits non-zero when records are invalid. |
| How large is the dataset? | `axiom dataset stats ./data/train.jsonl` | Record, field, and rough token counts. |
| Can I make a cleaned copy? | `axiom dataset clean ./data/train.jsonl ./data/train.cleaned.jsonl` | Writes a new JSONL file and leaves the source unchanged. |
| What hardware is present? | `axiom system info` | OS, architecture, CPU, RAM, GPU, VRAM, and CUDA availability. |
| What should I try first? | `axiom train plan 7 --method qlora` | A hardware-aware starting plan; it does not start training. |
| Which developer tools are visible? | `axiom tools doctor` | Executable presence and credential-reference presence, not vendor authentication. |

## Install

### PyPI

The beta package installs the `axiom` command from PyPI:

```bash
python -m pip install --upgrade --pre axiom-all
axiom version
```

`axiom-all` is the distribution name; the installed command is `axiom`.
Stable releases can be installed without `--pre` once one is published.

### macOS and Linux

<!-- markdownlint-disable MD013 -->
```bash
curl -fsSL https://raw.githubusercontent.com/NetCore-Technologies/AXIOM-AI/main/installers/install.sh | bash
axiom version
```
<!-- markdownlint-enable MD013 -->

The installer puts the command in `~/.local/bin/axiom`.

- Linux x86_64 uses the latest published `linux-x64` tarball and verifies its
  entry in `SHA256SUMS` before activation. The unpacked bundle is the faster
  repeated-start path.
- macOS and non-x86 Linux use an isolated Python environment and install from
  the repository's `main` branch. This fallback requires Python 3.11+ and is a
  source install, not a pinned native binary.

If `~/.local/bin` is not on `PATH`, the installer prints the export command.
Open a new shell after adding it.

### Windows PowerShell

<!-- markdownlint-disable MD013 -->
```powershell
irm https://raw.githubusercontent.com/NetCore-Technologies/AXIOM-AI/main/installers/install.ps1 | iex
```
<!-- markdownlint-enable MD013 -->

The installer downloads the latest non-draft Windows x64 release to
`%LOCALAPPDATA%\AXIOM`, adds that directory to the user `PATH`, and asks you to
restart PowerShell. Verify with:

```powershell
axiom version
```

Check the [Releases page](https://github.com/NetCore-Technologies/AXIOM-AI/releases)
for the exact assets and checksums available for a release. Beta.7 notes are
preparation notes until the matching release workflow and assets are verified.

## The daemon boundary

Run the daemon by itself when a script or local integration needs HTTP:

```bash
axiom daemon --host 127.0.0.1 --port 0
```

Port `0` asks the operating system for an available port. AXIOM prints the
resulting loopback URL, such as `http://127.0.0.1:53142`. While that process is
running, the daemon provides read-only JSON routes:

```text
GET /health
GET /api/info
GET /api/summary
GET /api/actions
GET /api/hardware
GET /api/tools
```

The default bind is local-only. A non-loopback bind is rejected unless
`--allow-network` is supplied deliberately. The daemon is not an account
service, hosted AXIOM backend, or general inference server. Stop it with
Ctrl-C.

## Web UI

The release packages and the PyPI wheel bundle the web UI. It includes the
Optimizer and the Quantization Lab, which compares FP16, INT8 and INT4 size
estimates against the memory AXIOM detects. Plans are estimates, not benchmark
results.

## Commands by job

### Project and environment

```bash
axiom version
axiom guide
axiom summary
axiom summary --json
axiom info
axiom status
axiom doctor
```

`guide` explains the current directory and suggests safe next commands.
`summary` returns a read-only snapshot of the project, hardware, visible tools,
and one recommendation; `--json` is intended for scripts. `doctor` checks
common executables and AXIOM package metadata.

### Models

```bash
axiom model list
axiom model add my-model local safetensors
axiom model inspect ./models/my-model
axiom model search llama --path models
axiom model info org/model
axiom model analyze org/model
axiom model pull org/model
```

The first three local commands do not need network access. Hugging Face
metadata and pull commands do; private or gated repositories also need
`axiom hf login`. `model pull` performs disk checks before downloading.

### Datasets

```bash
axiom dataset inspect ./data/train.jsonl
axiom dataset validate ./data/train.jsonl
axiom dataset stats ./data/train.jsonl
axiom dataset clean ./data/train.jsonl ./data/train.cleaned.jsonl
```

The current dataset path supports `.jsonl`. Validation checks JSON objects and
duplicates; it does not establish semantic quality or training readiness.

### Hardware and planning

```bash
axiom system info
axiom train plan 7 --method auto
axiom train plan 7 --method lora
axiom train plan 7 --method qlora
axiom train plan 7 --method full
axiom ai plan --model ./models/my-model
```

The planner uses detected hardware and conservative assumptions. Its fit and
VRAM values are planning estimates, not measured speed, memory usage, or a
promise that a later runtime will succeed.

### Developer tools

```bash
axiom tools list
axiom tools list --json
axiom tools doctor
axiom tools plan opencode
axiom tools install opencode       # preview only
axiom tools install opencode --yes # explicit package-manager install
```

The catalog covers Codex, Claude Code, Antigravity CLI, GitHub Copilot CLI,
Freebuff, Cursor Agent, free-pi, OpenCode, Gemini, OpenRouter, z.ai GLM, and a
keep-awake helper. `tools list` and `tools doctor` observe the current machine;
they do not prove that a vendor account is authenticated. Installation is a
preview unless `--yes` is supplied. AXIOM does not silently execute remote
installer scripts or store API-key values.

[Headroom](https://github.com/headroomlabs-ai/headroom) is a separate,
optional local context-compression proxy. If it is installed independently,
its own command path is:

```bash
headroom doctor
headroom proxy
headroom dashboard
```

AXIOM's role is limited to discovering or explaining Headroom. It does not
bundle, install, start, or supervise it; only the user starts the proxy or
dashboard. Do not read the integration as a promise of savings or a measured
result.

### MCP

Start the local stdio server from an MCP client configuration:

```bash
axiom mcp serve
```

It exposes local model, dataset, hardware, training-plan, and optional
SuperCompress tools as a process. It is separate from the HTTP daemon.

## What is shipped, and what is not

### Shipped in the beta

- A Python package and Typer CLI with a one-command local entry point.
- Project scaffolding, configuration checks, and local status/summary output.
- Model registration, local inspection, Hugging Face metadata analysis, and
  disk-checked model pulls.
- JSONL inspection, validation, duplicate detection, statistics, and cleaning.
- Hardware detection and hardware-aware LoRA, QLoRA, and full-training plans.
- A read-only loopback daemon with health, summary, action, hardware, and tool
  routes.
- MCP tools and an opt-in developer-tool catalog with preview-first installs.
- A static landing page that explains the terminal workflow.

### Not shipped by this product boundary

- Training execution, job management, checkpoints, or experiment tracking.
- Model inference, production serving, streaming, batching, or an
  OpenAI-compatible server.
- Live telemetry, background monitoring, hosted workspaces, accounts, or a
  browser control center.

## Repository shape

```text
axiom/
├── cli/          Typer command surface
├── core/         Project, hardware, storage, and integration helpers
├── models/       Local registry, inspection, and metadata analysis
├── datasets/     JSONL inspection and cleaning
├── training/     Hardware-aware plan generation
├── optimizer/    Agent workload plans and runtime bundles
├── runtime/      Optional runtime integrations
├── daemon.py     Dependency-free loopback HTTP daemon
└── mcp/          Stdio MCP server and tools
```

The public website is intentionally static. Product work belongs in the CLI,
local daemon, and reproducible project files.

## Principles

- **Local first:** keep models, datasets, configuration, and first-pass
  decisions close to the machine that will run them.
- **Evidence before execution:** expose assumptions before a user spends time
  or compute.
- **Explicit side effects:** preview external tool setup and require opt-in for
  package installation.
- **Honest boundaries:** separate detections, estimates, plans, and measured
  results.

## Contributing

AXIOM is in active beta development. Bug fixes, tests, documentation, and
tooling improvements are welcome.

Read [CONTRIBUTING.md](CONTRIBUTING.md) before making a larger change.

## License

MIT. See [LICENSE](LICENSE).

Built by [Manit Arora](https://github.com/manit6752025) and
[Rangan V Balaji](https://github.com/TaxCollector23).

[Website](https://netcore-technologies.github.io/AXIOM-AI/)
