# AXIOM roadmap

AXIOM is a terminal-first companion for local AI work. The current product
surface is a static landing page, a Python CLI, and a small loopback daemon.
This roadmap is directional; a checked box means the repository contains the
behavior, not that a hosted service or benchmark has been proven.

## Current beta

- [x] Installable Typer CLI with `axiom`, `guide`, `summary`, and `doctor`.
- [x] Project scaffolding, configuration validation, and local status output.
- [x] Local model registry, model inspection, metadata analysis, and
  disk-checked Hugging Face pulls.
- [x] JSONL inspection, validation, duplicate detection, statistics, and
  source-preserving cleaning.
- [x] CPU, RAM, GPU, VRAM, and CUDA detection with hardware-aware training
  plans.
- [x] Read-only loopback daemon with health, summary, action, hardware, and
  tool routes.
- [x] MCP stdio tools for local model, dataset, hardware, and planning tasks.
- [x] Preview-first developer-tool catalog with explicit package-install opt-in.
- [x] Cross-platform release workflows and a static landing page.

## Next, in order

### 1. Make local output easier to automate

- Add stable JSON output to the local inspection commands where the schema is
  useful and testable.
- Keep `axiom summary --json` stable enough for scripts and document changes to
  that shape.
- Improve missing-path errors so each failure names the cause and one recovery
  command.

### 2. Make inspection more informative without pretending to evaluate quality

- Add opt-in dataset schema hints and training-format checks.
- Improve model architecture and quantization detection from local metadata.
- Keep semantic quality, benchmark performance, and training success outside
  the claims of an inspection command.

### 3. Strengthen the daemon contract

- Keep `/api/info`, `/api/summary`, `/api/actions`, `/api/hardware`, and
  `/api/tools` small, local, and documented.
- Add graceful shutdown and clearer fixed-port collision errors.
- Add request routes only after path, size, content-type, and authorization
  rules have tests.

### 4. Harden tool setup and releases

- Add a machine-readable `tools doctor` report and a command that explains the
  user-level PATH locations AXIOM can update.
- Keep vendor authentication, pricing, quotas, and API-key storage outside
  AXIOM's authority.
- Verify exact release commits, checksums, installer behavior, and live Pages
  content before calling a build published.

### 5. Measure only when the evidence exists

If optimization or runtime work produces a benchmark, record the model,
checkpoint, runtime, device, driver, seed, workload, command, and environment.
Until then, use “recommended,” “estimated,” and “target,” not “faster” or
“reduced” as if those were measured results.

## Outside the current release boundary

The following are not part of the current AXIOM product contract:

- hosted workspaces, accounts, collaboration, or a browser control center;
- training execution, job management, checkpoints, or experiment tracking;
- model inference, production serving, streaming, batching, or an
  OpenAI-compatible API;
- background telemetry, live hardware monitoring, or hidden analytics.

Those ideas may be revisited only with a clear local-first contract and
evidence that they shorten a real developer workflow.
