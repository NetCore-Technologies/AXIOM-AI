# AXIOM AI Toolkit

The Control Center's **AI Toolkit** is a searchable, browser-local workbench containing 120 small utilities grouped into 12 categories. It is intended for bounded calculations, quick text/metadata checks, and preparing artefacts before running a real model or workspace workflow.

## Categories

| Category | Included utilities |
| --- | --- |
| Model sizing | FP16/BF16/FP32 and 2–8-bit weight footprints; KV-cache sizing |
| Quantization lab | Q2–Q8 savings, bit-width comparisons, memory fit screening, shard planning, compression ratios |
| Training planner | Effective batch, epoch/total steps, token counts, warmup, duration, LR schedules, optimizer/checkpoint storage |
| Dataset quality | JSON/JSONL shape/validity, duplicates, schema differences, null rates, text length, splits, class balance, exact leakage, CSV preview |
| Evaluation | Exact match, token overlap, Jaccard, Wilson intervals, threshold/pass-rate gates, score differences, MAE, RMSE |
| Inference operations | Approximate token count, context budget, throughput, latency percentiles, timeout budget, parallel slots, stop sequences, templates, truncation |
| Hardware planning | Memory reserve/fit, CPU workers, bandwidth ceiling, unified memory, PCIe transfer time, thermal headroom, performance per watt, uncertainty, power budgets |
| Security and privacy | Secret redaction/scanning, PII heuristics, path/URL checks, default-deny tool-policy review, prompt-injection heuristics, input bounds, local-address patterns |
| Workflow utilities | DAG/cycle/topological checks, missing inputs, manifests/seeds, artifact names, output-path and step-budget checks |
| API and operations | Retry/backoff schedules, timeout sums, pagination, request IDs, JSON formatting, query encoding, HTTPS GET curl construction, response envelopes, rate budgets |
| Prompt engineering | System prompt scaffold, role-shape check, prompt diff, few-shot formatter, test case and rubric scaffolds, JSON schema sample, instruction-density heuristic, budget and prompt variants |
| Release engineering | Semver parsing, simplified version compatibility, SHA-256, manifest sanity, platform label comparison, dependency-spec syntax, changelog grouping, port validation, support-text redaction, filename normalization |

## Input contract

Each utility has a description that explains the meaning of its inputs. The shared fields are:

- **Number A / B / C**: numeric inputs for the selected calculation. Their meaning is described by that utility.
- **Text A**: primary text, JSON/JSONL, measurements, prompt, URL, or metadata.
- **Text B**: comparison text or secondary input when required.

The SHA-256 tool hashes Text A in the current browser. CSV previews and class-balance checks can reveal values, so inspect the output before sharing it. Dataset summaries avoid returning record values by default, but users should still avoid pasting secrets and personal data.

## Automated validation

The release-smoke check verifies the exact 120-entry catalogue, unique utility titles, 12 categories, registered handlers for every distinct operation kind, browser-local implementation boundaries, and registration in both the Control Center navigation and Module Explorer. Playwright coverage exercises every catalogue entry with representative bounded inputs and includes targeted output assertions for selected calculations and security-sensitive helpers.

These tests establish automated regression coverage only when the corresponding CI run passes. They do not provide physical-hardware measurements, formal proof of security, a substitute for full-dataset validation, or a claim that other roadmap deliverables are complete.

## Execution and accuracy boundary

- Toolkit operations execute in the browser tab and do not call the AXIOM API, launch a shell process, download models, or make remote inference requests.
- Model-memory figures are screening estimates. Weight footprints exclude or simplify quantization metadata, KV cache, activations, fragmentation, and framework/runtime allocations.
- Token counts are character-based approximations, not tokenizer output.
- Text-based schema and dataset checks are bounded to the pasted sample; they are not substitutes for validating the full dataset on disk.
- URL, path, PII, secret, and prompt-injection checks are heuristics. They do not enforce API permissions, resolve symlinks, probe hosts, or replace server-side security controls.
- Version and dependency checks are deliberately simplified and are not a package resolver.
- A generated seed manifest records a desired seed but does not apply it to a training runtime.
- Workflow graph utilities validate pasted DAG metadata. They do not run workflow jobs or represent the workflow runner as implemented.
- Results should be reviewed before they are used as release gates or published as benchmark evidence.

The toolkit is an additional GUI utility surface; it does not claim that the separate R001–R120 roadmap deliverables are all complete.
