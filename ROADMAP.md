# AXIOM Roadmap

> **Build AI. Own AI.**

AXIOM is under active development. The roadmap is directional and may change as the architecture matures.

---

## Phase 0 — Foundation

**Status: In progress**

* [x] Python package
* [x] AXIOM CLI
* [x] Project initialization
* [x] `axiom.yaml` project configuration
* [x] Local model registry
* [x] JSONL dataset inspection
* [x] Basic dataset statistics
* [x] GitHub repository structure

---

## Phase 1 — Data Engineering

**Status: Next**

* [ ] Dataset cleaning
* [ ] Invalid record detection
* [ ] Duplicate removal
* [ ] Schema validation
* [ ] Dataset preview
* [ ] Dataset statistics
* [ ] Dataset versioning
* [ ] Token estimation improvements
* [ ] Conversational dataset support
* [ ] Training-format conversion

Target workflow:

```bash
axiom dataset inspect ./data/train.jsonl
axiom dataset clean ./data/train.jsonl
axiom dataset validate ./data/train.jsonl
```

---

## Phase 2 — Model Intelligence

* [ ] Hugging Face model discovery
* [ ] Automatic model metadata
* [ ] Local model import
* [ ] Safetensors detection
* [ ] GGUF detection
* [ ] Quantization detection
* [ ] Architecture detection
* [ ] Parameter estimation
* [ ] Model compatibility checks
* [ ] Model versioning

Target workflow:

```bash
axiom model add Qwen/...
axiom model inspect Qwen/...
```

---

## Phase 3 — Training Engine

* [ ] GPU detection
* [ ] VRAM detection
* [ ] CPU/RAM detection
* [ ] Hardware-aware training recommendations
* [ ] LoRA support
* [ ] QLoRA support
* [ ] Fine-tuning configuration
* [ ] Training jobs
* [ ] Checkpoints
* [ ] Training logs
* [ ] Experiment tracking

Target workflow:

```bash
axiom train
```

---

## Phase 4 — Evaluation

* [ ] Evaluation framework
* [ ] Custom test datasets
* [ ] Benchmark runners
* [ ] Regression testing
* [ ] Model comparison
* [ ] Evaluation reports
* [ ] Automated quality gates

Target workflow:

```bash
axiom evaluate
```

---

## Phase 5 — Runtime

* [ ] Local inference
* [ ] Model loading
* [ ] Streaming generation
* [ ] OpenAI-compatible API
* [ ] Runtime configuration
* [ ] GPU/CPU selection
* [ ] Resource monitoring
* [ ] Local model serving

Target workflow:

```bash
axiom serve
```

---

## Phase 6 — Deployment

* [ ] Docker support
* [ ] Reproducible deployments
* [ ] Local server deployment
* [ ] Remote server deployment
* [ ] GPU deployment profiles
* [ ] Model packaging
* [ ] Deployment health checks
* [ ] Rollback support

---

## Phase 7 — AXIOM Studio

A web interface for the complete AXIOM workflow.

```text
Dashboard
   │
   ├── Models
   ├── Datasets
   ├── Training
   ├── Experiments
   ├── Evaluations
   └── Deployments
```

Planned capabilities:

* visual project management
* dataset browser
* training controls
* experiment graphs
* model comparison
* deployment management
* hardware monitoring

---

## Phase 8 — AXIOM Cloud

Optional hosted services built around the open-source core.

Potential capabilities:

* cloud GPU training
* hosted inference
* private workspaces
* team collaboration
* model storage
* experiment storage
* remote deployment
* usage monitoring

The goal is to keep the local/self-hosted AXIOM experience fully viable.

---

## Long-term vision

AXIOM should eventually make this possible:

```text
Idea
 ↓
Dataset
 ↓
Base Model
 ↓
Fine-tuning
 ↓
Evaluation
 ↓
Optimization
 ↓
Package
 ↓
Deploy
 ↓
Monitor
```

From a single reproducible project.

---

## Guiding principle

**AXIOM should make building your own AI feel like software development.**

Models become versioned artifacts.

Datasets become versioned inputs.

Training becomes reproducible builds.

Evaluation becomes testing.

Deployment becomes release engineering.

---

This roadmap is intentionally ambitious. Features may be reordered as implementation and community feedback shape the project.
