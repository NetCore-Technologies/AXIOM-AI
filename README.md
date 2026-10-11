<div align="center">

![AXIOM. Build AI. Own AI.](docs/assets/banner.svg)

[![Status](https://img.shields.io/badge/status-active%20development-22c55e?style=flat-square&labelColor=0f172a)](https://github.com/NetCore-Technologies/AXIOM-AI)
[![Version](https://img.shields.io/badge/version-v0.3.0--beta.1-f59e0b?style=flat-square&labelColor=0f172a)](https://github.com/NetCore-Technologies/AXIOM-AI/releases)
[![License](https://img.shields.io/badge/license-MIT-7c3aed?style=flat-square&labelColor=0f172a)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?style=flat-square&labelColor=0f172a&logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-475569?style=flat-square&labelColor=0f172a)](https://github.com/NetCore-Technologies/AXIOM-AI/releases)

**Know your model, your data, and your machine before you spend a single GPU hour.**

[Quick start](#-quick-start) ·
[Install](#-install) ·
[Commands](#-commands-by-job) ·
[Website](https://netcore-technologies.github.io/AXIOM-AI/) ·
[Contributing](CONTRIBUTING.md)

![AXIOM terminal demo](docs/assets/terminal.svg)

<sub>Sample output. Plans and estimates are not benchmark results. See the [Web UI](#%EF%B8%8F-web-ui) below.</sub>

</div>

## What is AXIOM?

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

> AXIOM does not execute training, run model inference, or provide a hosted
> workspace. Estimates and plans are labeled as estimates and plans.

## What is new in v0.3.0-beta.1

- Version bumped to `v0.3.0-beta.1` across the package, badges, and docs.
- Refreshed README with an animated banner and a terminal walkthrough.
- Step-by-step quick start and a first-10-minutes guide below.

## 🚀 Quick start

Do these in order. Each step is one command.

1. Install AXIOM (see [Install](#-install)), then confirm it works:

   ```bash
   axiom version
   ```

2. Get oriented. None of these start the daemon:

   ```bash
   axiom --help
   axiom guide
   axiom summary
   ```

3. Create a project and check it:

   ```bash
   axiom init my-ai
   cd my-ai
   axiom project validate
   axiom config validate
   ```

4. Look at your machine:

   ```bash
   axiom system info
   ```

5. Get a starting plan for a 7B model:

   ```bash
   axiom train plan 7 --method qlora
   ```

Want the interactive mode? Run bare `axiom`. In an interactive terminal it
prints the startup mark once per session, shows the useful command path,
starts the local daemon on a free port, and stays attached until Ctrl-C.

## 🧭 First 10 minutes

Pick the path that matches what you have in front of you.

| I have... | Run this | You get |
| --- | --- | --- |
| A local model folder | `axiom model inspect ./models/my-model` | Format, files, architecture hints, weight size, conservative fit info. |
| A model name on Hugging Face | `axiom model info org/model` | Published metadata without downloading weights. Needs network. |
| A JSONL dataset | `axiom dataset validate ./data/train.jsonl` | Invalid records and duplicates; exits non-zero if records are invalid. |
| A dataset I want sized up | `axiom dataset stats ./data/train.jsonl` | Record, field, and rough token counts. |
| A messy dataset | `axiom dataset clean ./data/train.jsonl ./data/train.cleaned.jsonl` | A new cleaned file; the source is left unchanged. |
| A new machine | `axiom system info` | OS, architecture, CPU, RAM, GPU, VRAM, CUDA availability. |
| A plan to make | `axiom train plan 7 --method qlora` | Hardware-aware starting plan. It does not start training. |
| Some dev tools installed | `axiom tools doctor` | Executable and credential-reference presence, not vendor login state. |

## 📦 Install

### Debian / Ubuntu / Linux Mint (APT, amd64)

AXIOM publishes a signed APT repository alongside the project website. Add its public key and repository, then install the `axiom-ai` package:

```bash
curl -fsSLo /tmp/axiom-archive-keyring.gpg https://netcore-technologies.github.io/AXIOM-AI/apt/axiom-archive-keyring.gpg
sudo install -Dm0644 /tmp/axiom-archive-keyring.gpg /usr/share/keyrings/axiom-archive-keyring.gpg
echo 'deb [arch=amd64 signed-by=/usr/share/keyrings/axiom-archive-keyring.gpg] https://netcore-technologies.github.io/AXIOM-AI/apt stable main' | sudo tee /etc/apt/sources.list.d/axiom.list
sudo apt update
sudo apt install axiom-ai
```

The APT package currently targets 64-bit Intel/AMD (`amd64`). The repository metadata and release signature are verified by APT using the dedicated public keyring.

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
for the exact assets and checksums available for a release.

## 🔌 The daemon boundary

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

## 🖥️ Web UI

The release packages and the PyPI wheel bundle the web UI. Start the daemon
(or bare `axiom`), then open the loopback URL it prints.

<div align="center">

![AXIOM Web UI: Quantization Lab and Optimizer](docs/assets/webui.svg)

<sub>Sample data. Sizes and plans are estimates, not benchmark results.</sub>

</div>

- **Quantization Lab** compares FP16, INT8 and INT4 size estimates against the
  memory AXIOM detects, so you can see what fits before you download anything.
- **Optimizer** turns that into a conservative starting plan.

## 🛠️ Commands by job

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

## ✅ What is shipped, and what is not

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

## 🗂️ Repository shape

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

## 🧱 Principles

- **Local first:** keep models, datasets, configuration, and first-pass
  decisions close to the machine that will run them.
- **Evidence before execution:** expose assumptions before a user spends time
  or compute.
- **Explicit side effects:** preview external tool setup and require opt-in for
  package installation.
- **Honest boundaries:** separate detections, estimates, plans, and measured
  results.

## 🤝 Contributing

AXIOM is in active beta development. Bug fixes, tests, documentation, and
tooling improvements are welcome.

Read [CONTRIBUTING.md](CONTRIBUTING.md) before making a larger change.

## 📄 License

MIT. See [LICENSE](LICENSE).

Built by [Manit Arora](https://github.com/manit6752025) and
[Rangan V Balaji](https://github.com/TaxCollector23).

[Website](https://netcore-technologies.github.io/AXIOM-AI/)
