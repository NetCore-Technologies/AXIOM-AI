# AXIOM Feature Implementation Plan

This page is suitable for copying into the repository Wiki. It deliberately separates implemented foundations from proposed features.

## 1. Visual training workflow builder
**UI:** Training. **Backend:** validated workflow schema and planner.
- Connect model, dataset, training configuration, and evaluation nodes.
- Validate missing inputs, incompatible edges, and cycles.
- Export a reproducible plan before any execution is offered.
- Acceptance: invalid graphs are rejected by backend tests; export is deterministic.

## 2. Agent profiles and tool permissions
**UI:** MCP. **Backend:** permission policy enforcement.
- Named profiles declare allowed servers/tools and confirmation requirements.
- Default-deny unknown tools; log policy decisions.
- Acceptance: denied calls never reach tool execution; UI-only hiding is not considered enforcement.

## 3. Model compatibility registry
**UI:** Models. **Backend:** metadata inspection.
- Show format, parameter count when known, quantization, required memory estimate, and supported runtime.
- Mark unknown values as unknown instead of guessing.
- Acceptance: corrupt or incomplete metadata does not crash registry views.

## 4. Quantization comparison
**UI:** Quantization Lab.
- Compare supported formats and estimated storage/memory needs.
- Label estimates, assumptions, and measured values separately.
- Acceptance: formula tests cover supported parameter/bit-width combinations.

## 5. Dataset profile and privacy review
**UI:** Datasets. **Backend:** bounded JSONL inspection.
- Count valid/invalid rows, duplicate rows, field frequencies, and likely sensitive-field names.
- Never upload dataset contents by default.
- Acceptance: size/line limits prevent unbounded reads; report avoids printing raw sensitive values.

## 6. Experiment journal
**UI:** Evaluation. **Backend:** persistent local records.
- Store run label, model/dataset identifiers, configuration hash, timestamp, metrics, and notes.
- Export/import versioned JSON.
- Acceptance: records survive daemon restart and malformed imports are rejected.

## 7. Evaluation baselines and regression reports
**UI:** Evaluation. **Backend:** deterministic evaluation runner.
- Compare new results against an explicit baseline and configured thresholds.
- Do not invent a score when no evaluator is configured.
- Acceptance: regression status is testable from fixture reports.

## 8. Local API playground
**UI:** Runtime. **Backend:** explicit inference contract.
- Select local model/endpoint, send a prompt, inspect status, latency, and errors.
- Enforce loopback/local endpoint policy unless remote access is explicitly configured.
- Acceptance: request limits, timeout, and safe error handling are tested.

## 9. Hardware telemetry history
**UI:** Dashboard and Diagnostics. **Backend:** bounded sampling.
- Capture CPU, memory, GPU availability, and timestamps where supported.
- Expose sampling cadence and retention limits.
- Acceptance: unsupported sensors show unavailable; sampling does not block request handling.

## 10. Security/configuration audit
**UI:** Diagnostics. **Backend:** read-only audit engine.
- Check permissions, unsafe paths, exposed listeners, weak configuration, and dependency advisories where available.
- Separate findings from recommendations and disclose checks that could not run.
- Acceptance: fixtures cover pass, warning, fail, and unavailable states.

## Cross-cutting requirements

- Keep the current GUI theme and page structure.
- Every UI action must call a real contract or clearly state that it is a preview.
- Add backend enforcement for security features.
- Add tests and documentation with each implementation.
- Avoid describing planned work as shipped.
