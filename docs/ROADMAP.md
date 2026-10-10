# AXIOM Roadmap

## v0.2.0-beta.9 — previous beta

- [x] Unified Optimizer and Quantization Lab theme
- [x] Quantization size comparison
- [x] Read-only local workspace API and daemon-served web UI
- [x] Web UI bundled into release packages and the Python wheel
- [x] PyPI tag publishing workflow
- [x] Security hardening for filesystem boundaries and HTTP handling

## v0.3.0-beta.1 — engineering expansion

This release cycle keeps the existing Control Center layout and visual language. New capabilities belong inside the current pages; no wholesale redesign is planned.

### Feature implementation status

| Feature | Existing destination | Status for beta.1 |
| --- | --- | --- |
| Visual training workflow builder and graph validation | Training | Planned; do not imply training execution exists |
| Agent profiles and explicit tool-permission policies | MCP | Planned; require backend enforcement before claiming security |
| Local model registry and compatibility metadata | Models | Foundation exists; deeper compatibility scoring planned |
| Quantization comparison with explicit estimates vs measured results | Quantization Lab | Existing comparison; measured benchmarks planned |
| Dataset profiling, duplicate checks, and privacy indicators | Datasets | Inspection foundation exists; richer profiles planned |
| Persistent experiment history | Evaluation | Planned; needs a durable backend store |
| Repeatable evaluation baselines and regression reports | Evaluation | Planned; requires real evaluation runner |
| Local API playground | Runtime | Planned; needs a defined runtime/inference contract |
| Hardware telemetry and resource history | Control Center / Diagnostics | Partial hardware endpoint; history planned |
| Security/configuration audit dashboard | Diagnostics | Existing diagnostics are partial; full audit planned |

### Engineering priorities

1. Make backend contracts explicit before wiring new controls.
2. Add unit, API, and browser tests alongside each feature.
3. Distinguish estimated values from measured benchmarks.
4. Keep experiment records local-first and make export/import explicit.
5. Enforce MCP permissions and API authentication on the backend, not only in the GUI.
6. Preserve the existing GUI theme, navigation, and page structure.

### Distribution targets

- GitHub Releases: canonical signed/tagged source and platform artifacts.
- PyPI: Python CLI/daemon package.
- npm: only publish a clearly documented launcher/wrapper if it can reliably locate or install the Python runtime.
- APT: signed repository metadata and package checksums.
- Homebrew, Scoop/WinGet, and AUR: package manifests maintained against actual release artifacts.

Package publication depends on maintainer account access, registry configuration, signing keys, and CI secrets. Do not report a channel as published until its release workflow succeeds.

## Acceptance gates for beta.1

- Python tests pass.
- Frontend type-check, lint, and production build pass.
- Release asset contract tests pass.
- CodeQL/security review has no untriaged findings.
- Version numbers and release notes agree.
- A release tag is created only after the main branch is synced and validated.


<!-- AXIOM_DATASET_PROFILER_BEGIN -->
### Dataset profiler — implemented foundation
- [x] Bounded JSONL row/field profiling endpoint (`/api/dataset/profile`)
- [x] Duplicate, malformed-row, null-rate, and field-type statistics
- [x] Sensitive-looking field-name warnings without returning row values
- [x] Existing Datasets page integration and automated tests
- [ ] Broader privacy analysis and configurable retention/report export
<!-- AXIOM_DATASET_PROFILER_END -->
