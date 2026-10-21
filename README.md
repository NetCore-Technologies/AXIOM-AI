<div align="center">

![AXIOM. Build AI. Own AI.](docs/assets/banner.svg)

[![Status](https://img.shields.io/badge/status-active%20development-22c55e?style=flat-square&labelColor=0f172a)](https://github.com/NetCore-Technologies/AXIOM-AI)
[![Version](https://img.shields.io/badge/version-v0.3.0--beta.4-f59e0b?style=flat-square&labelColor=0f172a)](https://github.com/NetCore-Technologies/AXIOM-AI/releases)
[![License](https://img.shields.io/badge/license-MIT-7c3aed?style=flat-square&labelColor=0f172a)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?style=flat-square&labelColor=0f172a&logo=python&logoColor=white)](https://www.python.org/)
[![Platforms](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-475569?style=flat-square&labelColor=0f172a)](https://github.com/NetCore-Technologies/AXIOM-AI/releases)

# AXIOM AI

### Build AI. Own AI.

**Know your model, your data, and your machine before you spend a single GPU hour.**

[Quick start](#-quick-start) · [Beta.4 highlights](#-whats-new-in-v030-beta4) · [Install](#-install) · [CLI](#-cli-by-job) · [Wiki](https://github.com/NetCore-Technologies/AXIOM-AI/wiki) · [Report a bug](https://github.com/NetCore-Technologies/AXIOM-AI/issues)

![AXIOM terminal demo](docs/assets/terminal.svg)

<sub>Planning output and resource estimates are not benchmark results.</sub>

</div>

---

## What is AXIOM?

AXIOM is a **local-first AI project inspection and planning toolkit**. It helps you answer practical questions before committing compute, downloading large artifacts, or changing a workspace:

- What is inside this model directory, and what can be identified from its files and metadata?
- Is this JSONL dataset structurally valid, and what quality or privacy signals should I review?
- What CPU, RAM, GPU, and VRAM are visible on this machine?
- What is a conservative starting plan for a model and the hardware available?
- Which local tools and runtime candidates can be discovered, and what still needs to be configured?
- Is the AXIOM workspace configuration healthy, and how can I produce a small support bundle?

AXIOM combines a CLI, a local Control Center GUI, a loopback-first API, workspace metadata, and planning utilities. Project configuration lives in `axiom.yaml`; the local model registry lives in `.axiom`. Core inspection and planning do not require an AXIOM account.

> **Product boundary:** AXIOM's planning and workflow-design features do not mean that training or inference is running. AXIOM does not provide a hosted workspace or claim a runtime is connected unless it has been detected and verified.

## 🚀 What's new in v0.3.0-beta.4

Beta.4 puts discoverability, diagnostics, and safer project operations front and centre.

| Area | What changed | Try it |
| --- | --- | --- |
| **Module Explorer** | Searchable index of existing Control Center pages, CLI command families, and API surfaces. GUI pages navigate to real pages; CLI-only capabilities remain clearly labeled. | Open the Control Center and choose **Module Explorer**. |
| **Workspace diagnostics** | Read-only checks for workspace discovery, `axiom.yaml`, filesystem access, disk space, Python compatibility, and required imports; structured output is available for automation. | `axiom doctor --json` |
| **Roadmap audit** | Audits the scoped 120-item roadmap for missing, duplicate, unexpected, or unknown IDs/statuses without silently changing status labels. | `axiom roadmap audit --json` |
| **Support bundles** | Creates a privacy-minimized diagnostic ZIP intended to make bug reports easier to investigate. Inspect it before sharing. | `axiom support-bundle --output ./axiom-support-bundle.zip` |
| **Read-only API Playground** | Uses a fixed GET-only endpoint allowlist, bounded requests, timeouts, and capped response previews rather than arbitrary URL or mutating-method execution. | Open **API Playground** in the Control Center. |
| **Workflow design** | Adds templates, versioned saves, duplication, revision history, structural validation, and dry-run resource estimates. | Use the workflow design tools in the Control Center or `axiom workflow` commands. |
| **Control Center & diagnostics** | Improves local navigation, remembered administrator sessions, API error clarity, and request correlation. | Start with `axiom gui`. |

The canonical change history is in [`docs/CHANGELOG.md`](docs/CHANGELOG.md). The release page and Actions workflow are the source of truth for the downloadable assets attached to beta.4.

### Release status

`v0.3.0-beta.4` is a prerelease. **Do not assume installers are available just because the tag exists:** check the [beta.4 release page](https://github.com/NetCore-Technologies/AXIOM-AI/releases/tag/v0.3.0-beta.4) for assets and the [release Actions workflow](https://github.com/NetCore-Technologies/AXIOM-AI/actions/workflows/release-assets.yml) for build and publish status. Wait for the required jobs to pass and the expected files to appear before installing packaged builds.

## ⚡ Quick start

### Install from PyPI

AXIOM's distribution package is named `axiom-all`; the installed command is `axiom`. For a beta version:

```bash
python -m pip install --upgrade --pre axiom-all
axiom version
```

See [Install](#-install) for operating-system options and release-package notes.

### Create and inspect a workspace

```bash
axiom --help
axiom guide
axiom init my-ai
cd my-ai
axiom project validate
axiom config validate
axiom system info
axiom train plan 7 --method qlora
```

The training-plan command produces a plan. **It does not start a training job.**

### Open the Control Center

```bash
axiom gui
```

To print the local URL without automatically opening a browser:

```bash
axiom gui --no-open
```

Both the GUI workspace API and the standalone daemon default to loopback addresses. Stop the foreground process with `Ctrl-C`.

## 📦 Install

### Debian / Ubuntu / Linux Mint (APT, amd64)

The project's APT repository provides the `axiom-ai` package for 64-bit Intel/AMD systems:

```bash
curl -fsSLo /tmp/axiom-archive-keyring.gpg https://netcore-technologies.github.io/AXIOM-AI/apt/axiom-archive-keyring.gpg
sudo install -Dm0644 /tmp/axiom-archive-keyring.gpg /usr/share/keyrings/axiom-archive-keyring.gpg
echo 'deb [arch=amd64 signed-by=/usr/share/keyrings/axiom-archive-keyring.gpg] https://netcore-technologies.github.io/AXIOM-AI/apt stable main' | sudo tee /etc/apt/sources.list.d/axiom.list
sudo apt update
sudo apt install axiom-ai
```

### Python / PyPI

```bash
python -m pip install --upgrade --pre axiom-all
axiom version
```

Use a virtual environment when you want to isolate Python dependencies from other projects.

### macOS and Linux installer

```bash
curl -fsSL https://raw.githubusercontent.com/NetCore-Technologies/AXIOM-AI/main/installers/install.sh | bash
axiom version
```

The installer places the command at `~/.local/bin/axiom`. Ensure `~/.local/bin` is on `PATH`. Linux x86_64 uses a published release bundle when one is available; other platforms may use a Python source-install fallback. Check the release page for the current asset list and checksums.

### Windows PowerShell

```powershell
irm https://raw.githubusercontent.com/NetCore-Technologies/AXIOM-AI/main/installers/install.ps1 | iex
```

The installer targets the current user's `%LOCALAPPDATA%\AXIOM` directory and may require reopening PowerShell for its `PATH` update to take effect:

```powershell
axiom version
```

**Security note:** review installation scripts and release assets according to your environment's policy before running them. Prefer a published, verified release asset when one is available.

## 🧭 Pick your next command

| Goal | Command | What it does — and doesn't do |
| --- | --- | --- |
| Check the current project | `axiom summary` | Produces a read-only project and environment summary. |
| Inspect a model folder | `axiom model inspect ./models/my-model` | Reports discoverable files and metadata; it does not load model weights for inference. |
| Read remote model metadata | `axiom model info org/model` | Uses network access to query published metadata; it does not require downloading weights. |
| Validate a JSONL dataset | `axiom dataset validate ./data/train.jsonl` | Checks structure and record-level validity; it does not prove semantic quality or training readiness. |
| Profile dataset structure | `axiom dataset profile ./data/train.jsonl` | Produces bounded structural summaries; optional PII scanning is opt-in. |
| Inspect this machine | `axiom system info` | Reports detected system and accelerator information available to the process. |
| Draft a hardware-aware plan | `axiom train plan 7 --method qlora` | Estimates a starting point; it is not a benchmark or execution job. |
| Check workspace health | `axiom doctor --json` | Emits structured diagnostic checks without repairing files automatically. |
| Audit roadmap consistency | `axiom roadmap audit --json` | Reports roadmap IDs/status integrity without changing the roadmap. |
| Export support diagnostics | `axiom support-bundle --output ./axiom-support-bundle.zip` | Writes a minimized diagnostic archive; inspect it before sharing. |
| Inspect saved workflow design | `axiom workflow list` | Lists designs; validation and dry-runs do not execute workflow steps. |

## 🖥️ Control Center

The local Control Center brings key inspection and planning functions into a browser UI served by AXIOM itself. Beta.4 improves discoverability and navigation while keeping the current interface's local-first product boundary.

- **Module Explorer:** searchable map of existing GUI pages, CLI-only command families, and the live OpenAPI reference.
- **Diagnostics:** workspace checks with stable identifiers and clear status detail.
- **Roadmap:** a view of statuses represented in `ROADMAP.md`, with integrity reporting from the roadmap audit.
- **API Playground:** bounded, read-only GET requests to a predefined allowlist. It is not a generic HTTP client.
- **Workflow design:** templates, save history, duplication, validation, and resource estimates for review before an external execution tool is used.
- **Optimizer and Quantization Lab:** hardware-aware estimates and comparisons; values are estimates, not performance benchmarks.

The Module Explorer is a discovery layer, not proof that every roadmap item is implemented. CLI-only commands are shown as CLI-only rather than silently run in the browser.

## 🛠️ CLI by job

### Project and environment

```bash
axiom version
axiom guide
axiom summary --json
axiom info
axiom status
axiom doctor
axiom project validate
axiom config validate
```

### Models

```bash
axiom model list
axiom model inspect ./models/my-model
axiom model search llama --path models
axiom model info org/model
axiom model analyze org/model
```

Remote metadata and downloads require network access. Private or gated Hugging Face repositories may require `axiom hf login`. Review disk checks and repository licensing before downloading weights.

### Datasets

```bash
axiom dataset inspect ./data/train.jsonl
axiom dataset validate ./data/train.jsonl
axiom dataset stats ./data/train.jsonl
axiom dataset profile ./data/train.jsonl
axiom dataset manifest ./data/train.jsonl
axiom dataset preview-clean ./data/train.jsonl
```

Dataset inspection is structural. Optional PII heuristics are not a guarantee of privacy or compliance; review the dataset and the reported field names. `dataset clean` is a separate explicit operation that writes an output file, leaving the source file unchanged.

### Hardware, planning, and evaluation

```bash
axiom system info
axiom train plan 7 --method auto
axiom train plan 7 --method lora
axiom train plan 7 --method qlora
axiom ai plan --model ./models/my-model
axiom evaluation run ./data/eval.jsonl --prediction-field prediction --reference-field reference
```

Evaluation scores **precomputed predictions**. It does not run model inference. Resource and fit estimates are conservative planning aids rather than guarantees of runtime success.

### Experiments and workflow designs

```bash
axiom experiment list
axiom experiment show <experiment-id>
axiom workflow list
axiom workflow show <workflow-id>
axiom workflow validate <workflow-id>
```

Experiment records are plan snapshots, not executed training runs. Workflow designs describe and validate intended steps; they do not run those steps or manage checkpoints.

### Diagnostics and developer integrations

```bash
axiom roadmap audit --json
axiom support-bundle --output ./axiom-support-bundle.zip
axiom tools list
axiom tools doctor
axiom mcp serve
```

MCP is a separate stdio integration path. MCP tools are denied by default; inspect and explicitly configure permissions before enabling tools for a client. Tool discovery does not prove that a vendor account is authenticated.

## Local inference

AXIOM can run actual text generation through an Ollama service on `127.0.0.1:11434`. It does not download models or call a cloud inference API. See [Local inference](docs/Local-Inference.md) for setup and safety limits.

```bash
axiom --no-banner infer status
axiom --no-banner infer models
axiom --no-banner infer run qwen2.5:0.5b --prompt "Say hello in one sentence." --num-predict 128
```

## 🔌 Local API and security model

Run the standalone daemon when a local script needs HTTP responses:

```bash
axiom daemon --host 127.0.0.1 --port 0
```

Port `0` asks the operating system for an available port. Common read-only routes include:

```text
GET /health
GET /api/info
GET /api/summary
GET /api/actions
GET /api/hardware
GET /api/tools
```

The daemon's default bind is local-only. A non-loopback bind requires the deliberate `--allow-network` option. Do not expose the service to an untrusted network without assessing authentication, network controls, and the API contract. The daemon is not an account service, hosted AXIOM backend, or general inference server.

The API Playground has an explicit GET-only allowlist, timeouts, bounded reads, and capped response previews. It is not designed to issue arbitrary URLs or state-changing requests. See [`docs/API.md`](docs/API.md) and [`docs/Diagnostics-and-Support.md`](docs/Diagnostics-and-Support.md).

## 🔐 Diagnostics and support-bundle privacy

The support bundle is deliberately small and minimizes the information needed for debugging. Its documented contents are `diagnostics.json`, `environment.json`, and a static `README.txt`. It excludes configuration file contents, environment-variable values, credentials, model weights, datasets, logs, experiment records, user-authored data, and absolute paths.

Metadata minimization is not a guarantee of anonymity in every context. **Inspect the ZIP before sharing it**, and remove anything you do not want to disclose. Diagnostic commands are read-only and do not automatically repair workspace files.

## ✅ Shipped scope and honest limits

| Capability | Current contract |
| --- | --- |
| Model and dataset inspection | Local metadata and structure inspection; no automatic claim of full model compatibility or data quality. |
| Hardware-aware planning | Estimates based on visible hardware and explicit assumptions; not a speed benchmark. |
| Workflow designs | Templates, revisions, validation, and dry-run estimates; no execution engine implied. |
| Evaluation | Scores precomputed predictions; no inference is run. |
| Runtime discovery | Reports locally discoverable candidates and readiness evidence; does not fake a connected runtime. |
| Control Center | Local GUI for existing functions; Module Explorer does not make every roadmap item shipped. |
| Support bundles | Minimized diagnostic metadata; user review remains required before external sharing. |
| Hosted workspaces | Not introduced by beta.4. |

## 🧪 Contributing and quality checks

Bug reports should include the OS, Python version, AXIOM version, the command or GUI path used, and a minimal reproducible example. Review a support bundle before attaching it. Please do not attach credentials, API keys, private datasets, model weights, or unredacted logs.

For a local development checkout, common checks include:

```bash
python -m pytest -q
npm run lint
npm run build
npm run e2e
python scripts/release_smoke.py
```

Run checks in the environment and dependency state described by the repository; one passing check does not imply every platform build or end-to-end workflow has passed. See [`CONTRIBUTING.md`](CONTRIBUTING.md), [`ROADMAP.md`](ROADMAP.md), and [`docs/CHANGELOG.md`](docs/CHANGELOG.md).

## 📚 Documentation

- [Project Wiki](https://github.com/NetCore-Technologies/AXIOM-AI/wiki) — getting started, module guide, CLI, diagnostics, security, troubleshooting, and beta.4 notes.
- [Changelog](docs/CHANGELOG.md) — release-by-release changes.
- [Diagnostics and Support](docs/Diagnostics-and-Support.md) — workspace checks and the support-bundle privacy contract.
- [API contract](docs/API.md) — local API behavior and compatibility policy.
- [Evaluation guide](docs/Evaluation.md) — metrics over precomputed outputs.
- [Roadmap](ROADMAP.md) — scoped deliverables and their recorded status.
- [GitHub Releases](https://github.com/NetCore-Technologies/AXIOM-AI/releases) — published packages and checksums when available.
- [GitHub Actions](https://github.com/NetCore-Technologies/AXIOM-AI/actions/workflows/release-assets.yml) — build and publish status.

## License

AXIOM is released under the [MIT License](LICENSE).

<div align="center">

**AXIOM — Build AI. Own AI.**

</div>
