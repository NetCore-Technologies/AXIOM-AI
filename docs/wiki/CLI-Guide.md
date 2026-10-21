# AXIOM CLI Guide

Use the CLI for repeatable commands and automation independent of the Control Center UI.

## First commands

    axiom version
    axiom --help
    axiom guide
    axiom summary --json
    axiom status --json
    axiom doctor --json

Prefer supported JSON output for scripts, check exit codes, and handle failures. Do not parse human-oriented prose if structured output is available.

## Projects and configuration

    axiom init my-ai
    axiom project validate
    axiom config validate
    axiom info

## Models

    axiom model list
    axiom model inspect ./models/my-model
    axiom model search llama --path models
    axiom model info org/model
    axiom model analyze org/model

Remote metadata and downloads require network access. Model inspection does not execute inference.

## Datasets

    axiom dataset inspect ./data/train.jsonl
    axiom dataset validate ./data/train.jsonl
    axiom dataset stats ./data/train.jsonl
    axiom dataset profile ./data/train.jsonl
    axiom dataset manifest ./data/train.jsonl
    axiom dataset preview-clean ./data/train.jsonl

Dataset support focuses on JSONL. Structural validity does not prove semantic quality or compliance. PII checks, where supported, are opt-in heuristics. `preview-clean` does not write a file; `clean` is a separate explicit write operation.

## Hardware and planning

    axiom system info
    axiom train plan 7 --method auto
    axiom train plan 7 --method lora
    axiom train plan 7 --method qlora
    axiom ai plan --model ./models/my-model

Fit, speed, and VRAM figures are estimates, not measured performance or a guarantee that a runtime will succeed.

## Workflow, evaluation, and diagnostics

    axiom workflow list
    axiom workflow show <workflow-id>
    axiom workflow validate <workflow-id>
    axiom evaluation run ./data/eval.jsonl --prediction-field prediction --reference-field reference
    axiom doctor --json
    axiom roadmap audit --json
    axiom support-bundle --output ./axiom-support-bundle.zip

Workflow commands inspect designs. Evaluation scores precomputed predictions; it does not run inference.

## Tools and MCP

    axiom tools list
    axiom tools doctor
    axiom mcp serve
    axiom mcp permissions

Tool discovery does not prove vendor authentication. MCP is a separate stdio integration and its tools are denied by default until explicitly allowed.

Check `axiom <command> --help` on the installed build for the exact supported flags. Related: [Getting Started](Getting-Started), [Diagnostics](Workspace-Diagnostics-and-Support-Bundles).
