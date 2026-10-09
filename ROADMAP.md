# AXIOM Roadmap

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
