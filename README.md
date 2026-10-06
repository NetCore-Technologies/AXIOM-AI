# AXIOM AI

<p align="center">

**Build AI. Own AI.**

An open-source platform for building, fine-tuning, evaluating, and deploying AI models.

[![Status](https://img.shields.io/badge/status-early%20development-orange)](https://github.com/NetCore-Technologies/AXIOM-AI)
[![License](https://img.shields.io/badge/license-GPL--2.0-blue)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB)](https://www.python.org/)
[![GitHub](https://img.shields.io/github/stars/NetCore-Technologies/AXIOM-AI?style=social)](https://github.com/NetCore-Technologies/AXIOM-AI)

</p>

---

## What is AXIOM?

**AXIOM** is an open-source AI engineering platform designed to make building your own AI systems simpler, reproducible, and self-hosted.

Instead of stitching together separate tools for models, datasets, training, evaluation, and deployment, AXIOM aims to provide one workflow:

```text
                AXIOM
                  │
        ┌─────────┼─────────┐
        │         │         │
      Models    Data      Config
        │         │         │
        └─────────┼─────────┘
                  │
               Training
                  │
               Evaluation
                  │
              Optimization
                  │
               Deployment
```

The long-term goal is simple:

> **Give developers the tools to build AI they can actually own.**

AXIOM is designed around local hardware and self-hosting first, with cloud infrastructure planned as an optional layer rather than a requirement.

---

## Why AXIOM?

Modern AI development often means combining many different tools:

* model repositories
* dataset utilities
* training frameworks
* experiment trackers
* evaluation tools
* inference servers
* deployment systems

AXIOM is being built to make that process feel like one coherent development workflow.

### The vision

```text
Create
  ↓
Configure
  ↓
Import data
  ↓
Train / Fine-tune
  ↓
Evaluate
  ↓
Package
  ↓
Deploy
```

One project. One configuration. One workflow.

---

## Current status

AXIOM is in **early development**.

The project currently has a working Python CLI with:

### Project initialization

```bash
axiom init my-ai
```

Creates a reproducible AI project structure:

```text
my-ai/
├── axiom.yaml
├── README.md
├── data/
│   ├── raw/
│   └── processed/
├── models/
├── experiments/
├── evaluations/
└── outputs/
```

### Model registry

```bash
axiom model list
```

```bash
axiom model add my-model \
  MySource \
  --format safetensors \
  --parameters 7B \
  --quantization int4
```

AXIOM can currently maintain a local model registry with basic model metadata.

### Dataset inspection

```bash
axiom dataset inspect ./train.jsonl
```

The current inspector can identify:

* total samples
* valid samples
* invalid samples
* empty records
* duplicate records
* detected fields
* estimated token count

Example:

```text
AXIOM DATASET INSPECTION

Samples:          6
Valid:            5
Invalid:          1
Empty:            0
Duplicates:       1
Estimated tokens: 76

Fields:
instruction, output
```

---

# Architecture

AXIOM is being built as a modular platform.

```text
axiom/
├── cli/
├── core/
├── models/
├── datasets/
├── training/
├── evaluation/
├── runtime/
└── config/
```

The architecture is intentionally modular so individual systems can evolve without turning AXIOM into one giant monolithic application.

---

# Planned capabilities

The roadmap includes:

### Model management

* Hugging Face model discovery
* local model importing
* model metadata detection
* model versioning
* quantization awareness
* model packaging

### Dataset engineering

* dataset cleaning
* validation
* deduplication
* dataset statistics
* token estimation
* dataset transformations
* conversational dataset support

### Training

* LoRA
* QLoRA
* fine-tuning workflows
* hardware-aware configuration
* GPU detection
* experiment tracking
* checkpoint management

### Evaluation

* automated benchmarks
* custom evaluation suites
* regression testing
* model comparison
* quality reports

### Runtime

* local inference
* model serving
* OpenAI-compatible APIs
* resource monitoring
* deployment profiles

### Deployment

* Docker
* local GPU systems
* self-hosted servers
* cloud GPU environments
* reproducible deployments

---

# CLI vision

The eventual AXIOM workflow should look something like:

```bash
axiom init my-ai

axiom model add Qwen/...

axiom dataset inspect ./data/train.jsonl

axiom dataset clean ./data/train.jsonl

axiom train

axiom evaluate

axiom serve
```

The objective is for AXIOM to understand the relationship between each stage rather than treating every command as an isolated tool.

---

# Hardware philosophy

AXIOM is being designed with **real-world hardware constraints** in mind.

It should be possible to use AXIOM with:

* consumer GPUs
* workstation GPUs
* CPU-only environments for lightweight workloads
* local servers
* cloud GPUs
* future specialized accelerators

AXIOM should detect available hardware and help produce sensible configurations instead of assuming everyone has a large GPU cluster.

---

# Open source

AXIOM is open source because AI tooling should not require handing your entire development workflow to a hosted service.

The core project is intended to remain:

* self-hostable
* inspectable
* extensible
* reproducible
* community-driven

Cloud services may exist in the future, but they will complement the open-source core rather than replace it.

---

# Project principles

### Own your models

Use the models you choose, on infrastructure you control.

### Own your data

Your datasets should remain yours.

### Reproducibility first

Training and evaluation should be reproducible from configuration.

### Local-first

Local hardware should be a first-class environment.

### Modular by design

AXIOM should integrate with existing AI ecosystems rather than forcing developers into one stack.

---

# Development

Clone the repository:

```bash
git clone https://github.com/NetCore-Technologies/AXIOM-AI.git
cd AXIOM-AI
```

Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install in editable mode:

```bash
pip install -e .
```

Check AXIOM:

```bash
axiom version
```

Create a project:

```bash
axiom init my-ai
```

---

# Contributing

AXIOM is still young, so architecture and APIs may change quickly.

Before contributing major features, please open an issue to discuss the proposed design.

Small improvements, bug fixes, tests, documentation, and developer tooling are welcome.

---

# Roadmap

See [`ROADMAP.md`](ROADMAP.md) for the current development plan.

# Security

See [`SECURITY.md`](SECURITY.md) for reporting security vulnerabilities.

---

# License

AXIOM is released under the **GNU General Public License v2.0**.

See [`LICENSE`](LICENSE) for the full license text.

---

<p align="center">

**AXIOM — Build AI. Own AI.**

</p>
