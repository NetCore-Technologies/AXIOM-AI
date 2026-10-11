# AXIOM Roadmap

<!-- AXIOM-ROADMAP-UPDATE:START -->
## Beta roadmap and implementation status

### Current foundations

- [x] Bounded JSONL profiling with row, field and privacy-review statistics.
- [x] Workspace API foundations for datasets, runtime information and training plans.
- [x] Existing model inspection, registry, optimisation and quantization components.
- [x] GUI sections for the principal engineering workflows.

### Planned feature priorities

| Priority | Feature | Goal |
|---|---|---|
| 1 | Visual training workflow builder | Connect and validate training steps visually. |
| 2 | Agent profiles and tool permissions | Add explicit permissions and auditable tool usage. |
| 3 | Model registry and compatibility | Improve discovery, metadata and hardware/runtime checks. |
| 4 | Quantization comparison lab | Compare options with documented assumptions. |
| 5 | Dataset profiling and privacy checks | Expand bounded validation and privacy signals. |
| 6 | Persistent experiment history | Save settings, outcomes and run history. |
| 7 | Evaluation and regression reports | Repeat evaluations and compare results. |
| 8 | Local API playground | Exercise supported endpoints and inspect responses. |
| 9 | Hardware telemetry and resource history | Record resource snapshots and performance trends. |
| 10 | Security and configuration audit | Provide actionable local diagnostics. |

### Delivery standard

A feature should not be marked shipped until the applicable backend, GUI,
CLI, validation, tests and documentation have been verified. Roadmap entries
remain planned work until that evidence exists.
<!-- AXIOM-ROADMAP-UPDATE:END -->

## Beta.5 — released

- [x] Agent/model optimizer
- [x] Quantization lab
- [x] Hardware-aware optimization planning
- [x] Local daemon health and capability endpoints
- [x] Dataset quality inspection
- [x] Trusted model filesystem boundaries
- [x] Secure administrator storage
- [x] E2E authentication validation

### Next

- Connect the local daemon to model, dataset, training, runtime, and MCP workflows
- Deeper runtime benchmarking
- Broader local-model/runtime integration
- Profiling and telemetry improvements

<!-- AXIOM-BETA5-RELEASE -->

## Beta.5 completed

- Agent/model optimization planning
- Quantization workflow and hardware-aware recommendations
- Security hardening for model filesystem access
- Secure administrator verification storage
- CI browser/E2E reliability improvements for the landing page

## Next

- Expand measured runtime benchmarking across supported backends
- Broaden model format and accelerator coverage
- Continue security/code-quality hardening
- Improve optimizer telemetry and diagnostics

## v0.2.0-beta.5

AXIOM beta.5 adds the optimizer/quantization workflow, hardware-aware model planning, hardened model filesystem boundaries, safer administrator verifier storage, and improved CI/E2E validation. See [the beta.5 release notes](docs/releases/v0.2.0-beta.5.md).

### Beta.5 — released

- Optimizer and quantization lab workflow
- Agent-oriented model planning
- Filesystem/path security hardening
- Administrator storage hardening
- CI/E2E reliability improvements

## v0.2.0-beta.7 — released

- Optimizer and quantization planning improvements.
- Model-path and administrator-storage hardening.
- E2E and release-pipeline verification.

## AXIOM v0.2.0-beta.5 macOS DMG

The release workflow packages separate macOS Apple Silicon (arm64) and Intel (x86_64) DMGs. Each contains the AXIOM CLI executable and compiled Control Center frontend, plus a SHA-256 checksum. The DMGs are currently unsigned and not notarized; API-backed UI features require a separately running/configured AXIOM backend. See `docs/releases/v0.2.0-beta.5.md` for release details.

## v0.2.0-beta.9 — released

- [x] Unified Optimizer and Quantization Lab theme
- [x] Quantization Lab size comparison
- [x] Read-only workspace API on the local daemon
- [x] Web UI served by the daemon at `/ui/`
- [x] Web UI bundled into every release package and the PyPI wheel
- [x] Automatic PyPI publishing on version tags

### Next

- Connect every GUI page to the daemon routes
- Measured runtime benchmarking across supported backends
- Broader model format and accelerator coverage
