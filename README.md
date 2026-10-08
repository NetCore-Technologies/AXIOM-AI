<div align="center">

<img src="docs/assets/banner.svg" alt="AXIOM. Build AI. Own AI." width="100%"/>

<br/>

[![Status](https://img.shields.io/badge/status-active%20development-22c55e?style=flat-square&labelColor=0f172a)](https://github.com/NetCore-Technologies/AXIOM-AI)
[![Version](https://img.shields.io/badge/version-v0.2.0--beta.5-0ea5e9?style=flat-square&labelColor=0f172a)](https://github.com/NetCore-Technologies/AXIOM-AI/releases)
[![License](https://img.shields.io/badge/license-MIT-7c3aed?style=flat-square&labelColor=0f172a)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?style=flat-square&labelColor=0f172a&logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-475569?style=flat-square&labelColor=0f172a)](https://github.com/NetCore-Technologies/AXIOM-AI/releases)
[![Stars](https://img.shields.io/github/stars/NetCore-Technologies/AXIOM-AI?style=flat-square&labelColor=0f172a&color=f59e0b)](https://github.com/NetCore-Technologies/AXIOM-AI)

<br/>

**AXIOM** is an open-source AI engineering platform that brings models, datasets, training, evaluation, runtime and deployment into one focused workspace. It is local-first, self-hosted, and built for engineers who want to own their AI stack.

<br/>

[**Install from terminal**](#install-from-the-terminal) &nbsp;·&nbsp; [**Website**](https://netcore-technologies.github.io/AXIOM-AI/) &nbsp;·&nbsp; [**Wiki**](https://github.com/NetCore-Technologies/AXIOM-AI/wiki) &nbsp;·&nbsp; [**Roadmap**](https://github.com/NetCore-Technologies/AXIOM-AI/wiki/Roadmap) &nbsp;·&nbsp; [**Contributing**](CONTRIBUTING.md)

</div>

---

## Control Center

```
╔══════════════════════════════════════════════════════════════╗
║  AXIOM CONTROL CENTER                              READY  ◉  ║
╠══════════════════════════════════════════════════════════════╣
║  SYSTEM HEALTH     ████████████████████  OPERATIONAL         ║
║  AI RUNTIME        ████████████████████  LOCAL ENGINE  LIVE  ║
║  MODEL REGISTRY    ████████████████████  SYNCED              ║
║  INFERENCE         ████████████████████  ACTIVE              ║
╠══════════════════════════════════════════════════════════════╣
║  ✓ Local workspace  ·  Your models  ·  Your data             ║
╚══════════════════════════════════════════════════════════════╝
```

---

## Why AXIOM

Modern AI development means juggling a different tool for every stage. AXIOM replaces the entire stack with one coherent engineering workspace.

<br/>

<div align="center">

| | Stage | What AXIOM does |
|---|---|---|
| ◎ | **Models** | Inspect metadata, manage a local registry, search Hugging Face |
| ◇ | **Datasets** | Validate, clean, deduplicate and analyse training data |
| ⌁ | **Training** | Hardware-aware plans, LoRA/QLoRA configs, fit estimation |
| ◌ | **Evaluation** | Benchmarks, quality checks and model comparison |
| ▣ | **Runtime** | Runtime foundations, MCP tooling and resource planning |
| ⌬ | **Diagnostics** | MCP tooling, system health, request tracing |

</div>

<br/>

> **One project. One configuration. One workflow.**

---

## Install from the terminal

```bash
# macOS and Linux
curl -fsSL https://raw.githubusercontent.com/NetCore-Technologies/AXIOM-AI/main/installers/install.sh | bash

# Verify
axiom version
```

### Windows PowerShell

```powershell
irm https://raw.githubusercontent.com/NetCore-Technologies/AXIOM-AI/main/installers/install.ps1 | iex
axiom version
```

AXIOM is intentionally installed and used from the terminal. The website does not expose binary download links.

---

## CLI

```bash
# Start a project
axiom init my-ai
axiom status
axiom doctor

# Models
axiom model list
axiom model add my-model local --format safetensors
axiom model inspect ./models/my-model
axiom model search "mistral 7b"

# Datasets
axiom dataset inspect ./data/train.jsonl
axiom dataset validate ./data/train.jsonl
axiom dataset clean ./data/train.jsonl
axiom dataset stats ./data/train.jsonl

# Project
axiom project info
axiom project validate
axiom config show

# Hugging Face
axiom hf login
axiom hf status

# Training (plan generation)
axiom train plan 7

# Runtime
axiom mcp serve
```

---

## Architecture

```
axiom/
├── cli/          ← Typer command surface
├── core/         ← Platform engine
├── models/       ← Registry, inspection, metadata
├── datasets/     ← Validation, cleaning, stats
├── training/     ← Planning, hardware detection, fit estimation
├── evaluation/   ← Benchmarks, quality, comparison
├── runtime/      ← Provider integrations and runtime foundations
├── mcp/          ← Stdio MCP server and tools
└── config/       ← Configuration management
```

Intentionally modular. Each subsystem evolves independently without coupling to the rest.

### Current backend boundary

AXIOM currently exposes its local backend through the Python CLI and a stdio MCP server (`axiom mcp serve`). This repository does not contain an HTTP service, database, CORS/auth middleware, or hosted API deployment. The Control Center therefore reports disconnected states until a real API contract is added; it does not invent live model, dataset, or runtime data.

---

## Features

<!-- AXIOM_FEATURES_BEGIN -->
<details>
<summary><strong>Core Platform</strong></summary>
<br/>

- [x] AXIOM project initialization
- [x] Modular AI engineering architecture
- [x] First-boot administrator setup
- [x] Local authentication
- [x] Session timeout protection
- [x] Password management
- [x] Modern AXIOM control center
- [x] Light / dark UI support

</details>

<details>
<summary><strong>CLI. 21 commands shipping</strong></summary>
<br/>

- [x] `axiom version` · `axiom init` · `axiom doctor` · `axiom info` · `axiom status`
- [x] `axiom model list` · `axiom model add` · `axiom model inspect` · `axiom model search`
- [x] `axiom dataset inspect` · `axiom dataset clean` · `axiom dataset validate` · `axiom dataset stats`
- [x] `axiom project info` · `axiom project validate`
- [x] `axiom config show` · `axiom config validate`
- [x] Hugging Face authentication · SuperCompress · Integration registry · MCP support

</details>

<details>
<summary><strong>Models</strong></summary>
<br/>

- [x] Model registry · inspection · metadata · format awareness · parameter count · quantization
- [ ] Automated download manager · conversion pipeline · benchmark suite · compatibility checks · version management

</details>

<details>
<summary><strong>Datasets</strong></summary>
<br/>

- [x] JSONL inspection · cleaning · validation · duplicate detection · statistics · field detection · token estimation
- [ ] Versioning · diffing · deduplication engine · sampling · augmentation · quality scoring

</details>

<details>
<summary><strong>Training</strong></summary>
<br/>

- [x] Training planning · hardware-aware planning · LoRA planning · CPU/GPU detection · model-fit estimation
- [ ] Training execution · job management · experiment tracking · checkpoints · dashboards · multi-GPU · distributed · hyperparameter search

</details>

<details>
<summary><strong>Evaluation</strong></summary>
<br/>

- [x] Evaluation subsystem foundation
- [ ] Automated pipelines · benchmark runner · dataset-based eval · model comparison · regression testing · custom metrics · reports

</details>

<details>
<summary><strong>Runtime</strong></summary>
<br/>

- [x] Runtime foundation · MCP foundation · integration registry
- [ ] Production serving · streaming inference · request batching · scheduling · autoscaling · health checks · load testing · optimization

</details>

<details>
<summary><strong>Observability</strong></summary>
<br/>

- [x] Diagnostics foundation · system information · CLI health checks
- [ ] Live telemetry · request tracing · token tracking · GPU monitoring · training telemetry · metrics · log search · profiling · export

</details>

<details>
<summary><strong>Security</strong></summary>
<br/>

- [x] Administrator authentication · session timeout · password management · GPG-signed releases
- [ ] API auth · secrets management · RBAC · audit logging · security diagnostics · enterprise controls

</details>

<details>
<summary><strong>Developer Experience</strong></summary>
<br/>

- [x] Python package · Typer CLI · release packaging · GitHub Actions pipeline · Wiki · community docs · issue templates · PR templates
- [ ] Python API docs · plugin SDK · shell completion · diagnostics bundle

</details>
<!-- AXIOM_FEATURES_END -->

---

<!-- AXIOM_BETA5_FEATURES_BEGIN -->
## Beta.5 Features

### AI Model Optimizer
- [x] Agent-type questionnaire
- [x] Primary use-case selection
- [x] Privacy preference
- [x] Latency preference
- [x] Target tokens/sec
- [x] Hardware-aware planning
- [x] Quantization recommendation
- [x] Memory-fit estimation
- [x] Hugging Face model discovery
- [ ] Real device benchmark engine
- [ ] Automatic quantization/export
- [ ] Benchmark, tune, re-run loop

### Model Policy Audit
- [x] Visible safety/policy indicator inspection
- [x] Configuration inspection
- [x] Audit-only workflow
- [ ] Expanded policy metadata analysis
- [ ] Model lineage reporting

> AXIOM does not remove or bypass model safety controls. Beta.5 provides transparent policy auditing instead.
<!-- AXIOM_BETA5_FEATURES_END -->

## Roadmap

<!-- AXIOM_ROADMAP_BEGIN -->
<details open>
<summary><strong>✅ Completed</strong></summary>
<br/>

Core platform · First-boot admin · Authentication · Session controls · Model registry · Dataset inspection & cleaning · Training plan generation · Hardware detection · Model-fit estimation · Hugging Face integration · SuperCompress · Integration registry · MCP foundation · CLI expansion (21 commands) · Project validation · Config validation · Diagnostics · Wiki · Community docs · Release packaging · GPG-signed releases

</details>

<details>
<summary><strong>Next. AI Engineering</strong></summary>
<br/>

- [ ] Training execution · job manager · queue · experiment tracking · checkpoints · resume/recovery · hyperparameter search
- [ ] Evaluation pipelines · benchmark runner · model comparison · regression testing · reports

</details>

<details>
<summary><strong>Next. Data and Models</strong></summary>
<br/>

- [ ] Dataset versioning · diffing · deduplication · quality scoring · sampling · augmentation · lineage
- [ ] Model download manager · conversion · compatibility matrix · benchmarking · version management · quantization workflows

</details>

<details>
<summary><strong>Next. Runtime and Observability</strong></summary>
<br/>

- [ ] Production serving · streaming inference · batching · scheduling · autoscaling · health monitoring
- [ ] Live telemetry · request tracing · GPU monitoring · log search · performance profiling · metrics export

</details>

<details>
<summary><strong>🔭 Platform Expansion</strong></summary>
<br/>

- [ ] Plugin SDK · Python API · CLI shell completion · remote training · multi-GPU · distributed training/inference · agent orchestration · advanced MCP · deployment automation

</details>

<details>
<summary><strong>🌐 Long-Term Vision</strong></summary>
<br/>

- [ ] Full AI experiment workspace · end-to-end lifecycle management · collaborative AI engineering · enterprise deployment · AXIOM plugin marketplace · advanced agent platform

</details>
<!-- AXIOM_ROADMAP_END -->

---

## Principles

<div align="center">

| | |
|---|---|
| **Own your models** | Use what you choose, on infrastructure you control |
| **Own your data** | Your datasets stay yours |
| **Reproducibility first** | Training and evaluation reproducible from config |
| **Local-first** | Local hardware is a first-class environment |
| **Modular by design** | Integrates with existing ecosystems, no lock-in |

</div>

---

<!-- AXIOM_BETA5_ROADMAP_BEGIN -->
## Expanded Roadmap

### Agent & Model Optimization
- [x] Agent questionnaire
- [x] Hugging Face discovery
- [x] Hardware-aware planning
- [x] Quantization recommendation
- [ ] Real device benchmark engine
- [ ] Automatic quantization/export
- [ ] Per-device performance profiles
- [ ] Benchmark history
- [ ] Performance regression detection
- [ ] Automatic optimize, benchmark, retune

### Training
- [ ] Training execution
- [ ] Training job manager
- [ ] Training queue
- [ ] Experiment tracking
- [ ] Checkpoint management
- [ ] Resume/recovery
- [ ] Hyperparameter search
- [ ] Multi-GPU training
- [ ] Distributed training

### Evaluation
- [ ] Evaluation pipelines
- [ ] Benchmark runner
- [ ] Model comparison
- [ ] Regression testing
- [ ] Custom evaluation metrics
- [ ] Evaluation reports
- [ ] Evaluation dashboard

### Runtime
- [ ] Production model serving
- [ ] Streaming inference
- [ ] Request batching
- [ ] Request scheduling
- [ ] Runtime autoscaling
- [ ] Endpoint management
- [ ] Runtime load testing
- [ ] Inference optimization

### Observability
- [ ] Token throughput telemetry
- [ ] Latency telemetry
- [ ] CPU/RAM/GPU monitoring
- [ ] Request tracing
- [ ] Performance profiling
- [ ] Benchmark dashboards
- [ ] Telemetry export

### Hugging Face
- [x] Authentication
- [x] Model discovery
- [ ] One-click model import
- [ ] Model metadata browser
- [ ] Compatibility scoring
- [ ] Artifact verification
- [ ] Local cache manager

### GUI
- [x] Agent Model Optimizer
- [x] Agent questionnaire
- [x] Model Policy Audit
- [ ] Interactive hardware profiler
- [ ] Live benchmark panel
- [ ] Training workspace
- [ ] Evaluation workspace
- [ ] Runtime control center

### Security
- [x] Browser credential persistence cleanup
- [x] Model Policy Audit
- [x] GPG-signed release assets
- [ ] API authentication
- [ ] Secrets manager
- [ ] Role-based access control
- [ ] Audit logging
- [ ] Security health dashboard

### Developer Platform
- [ ] Python API
- [ ] Plugin SDK
- [ ] CLI shell completion
- [ ] Remote training
- [ ] Distributed inference
- [ ] Advanced MCP tooling
- [ ] Agent orchestration
- [ ] Reproducible environments
- [ ] Deployment automation
<!-- AXIOM_BETA5_ROADMAP_END -->

## Contributing

AXIOM is young. Architecture and APIs move fast.

Open an issue before large feature contributions. Bug fixes, tests, docs and tooling improvements are always welcome.

→ [CONTRIBUTING.md](CONTRIBUTING.md) &nbsp;·&nbsp; [Code of Conduct](CODE_OF_CONDUCT.md) &nbsp;·&nbsp; [Security Policy](SECURITY.md)

---

## License

MIT. [LICENSE](LICENSE)

---

<div align="center">

<sub>Built by <a href="https://github.com/manit6752025">@manit6752025</a> and <a href="https://github.com/NetCore-Technologies/AXIOM-AI/graphs/contributors">contributors</a> · <a href="https://netcore-technologies.github.io/AXIOM-AI/">netcore-technologies.github.io/AXIOM-AI</a></sub>

<br/>

<sub><strong>AXIOM. Build AI. Own AI.</strong></sub>

</div>
