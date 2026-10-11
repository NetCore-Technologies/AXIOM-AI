# AXIOM Feature Implementation Plan

<!-- AXIOM-FEATURE-PLAN-UPDATE:START -->
## Beta implementation and acceptance criteria

The existing release has a dataset profiling foundation and model, optimisation,
quantization, workspace API and GUI components. This does not imply that every
roadmap feature is fully integrated.

For each feature, verify the following as applicable:

- **GUI:** usable controls, results, loading/error states and empty states.
- **Backend:** validated inputs, bounded resource use and useful errors.
- **CLI:** discoverable, documented commands when terminal usage is appropriate.
- **Security:** safe paths, permission checks and protected local files.
- **Tests:** unit, API, CLI and GUI checks that cover the feature.
- **Documentation:** user guide, command help, release notes and examples.

Priorities include workflow building, agent permissions, model compatibility,
quantization comparison, dataset privacy, experiment history, evaluation
regressions, a local API playground, telemetry and security diagnostics.
<!-- AXIOM-FEATURE-PLAN-UPDATE:END -->

1. Training workflow graph builder and validation.
2. MCP agent profiles with server-enforced default-deny tool permissions.
3. Local model compatibility registry.
4. Quantization estimates separated from measured benchmarks.
5. JSONL dataset profiling and privacy indicators (included in this patch).
6. Persistent experiment history.
7. Evaluation baselines and regression reports.
8. Local API playground with request limits/timeouts.
9. Historical hardware telemetry.
10. Read-only security/configuration audit.

Preserve the existing GUI theme. Do not call a feature complete until backend enforcement and tests exist.
