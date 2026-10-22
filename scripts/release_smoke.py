#!/usr/bin/env python3
"""Dependency-free static acceptance checks for an AXIOM checkout.

This complements (rather than replaces) pytest, ESLint, the production build, and
Playwright tests. It never imports the application or contacts external services.
"""
from __future__ import annotations

import argparse
import json
import re
import tomllib
from pathlib import Path
from typing import Any

ROADMAP_PATTERN = re.compile(r"^- \[(R\d{3}) · ([^\]]+)\]", re.MULTILINE)
VALID_STATUSES = {
    "Implemented; tests passing",
    "Planned",
    "In progress",
    "In progress; validation pending",
}


def roadmap_issues(markdown: str) -> list[str]:
    entries = ROADMAP_PATTERN.findall(markdown)
    ids = [item[0] for item in entries]
    expected = {f"R{i:03d}" for i in range(1, 121)}
    issues: list[str] = []
    missing = sorted(expected - set(ids))
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    unexpected = sorted(set(ids) - expected)
    unknown_statuses = sorted({status for _, status in entries if status not in VALID_STATUSES})
    if len(entries) != 120:
        issues.append(f"Expected 120 roadmap entries; found {len(entries)}.")
    if missing:
        issues.append("Missing roadmap IDs: " + ", ".join(missing))
    if duplicates:
        issues.append("Duplicate roadmap IDs: " + ", ".join(duplicates))
    if unexpected:
        issues.append("Unexpected roadmap IDs: " + ", ".join(unexpected))
    if unknown_statuses:
        issues.append("Unknown roadmap statuses: " + ", ".join(unknown_statuses))
    return issues


def page_registration_issues(app_source: str, page_id: str) -> list[str]:
    """Check that a page is represented in the Page union, nav, metadata and switch."""
    checks = {
        "Page union": bool(re.search(rf'^\s*\| "{re.escape(page_id)}"\s*$', app_source, re.MULTILINE)),
        "navigation": bool(re.search(rf'\bid:\s*"{re.escape(page_id)}"', app_source)),
        "page metadata": bool(re.search(rf'^\s*(?:"{re.escape(page_id)}"|{re.escape(page_id)}):\s*\{{', app_source, re.MULTILINE)),
        "render switch": bool(re.search(rf'case "{re.escape(page_id)}":', app_source)),
    }
    return [f"GUI page '{page_id}' is missing from {where}." for where, present in checks.items() if not present]


def module_catalog_issues(app_source: str, page_ids: tuple[str, ...] = ("api-playground", "agent-profiles")) -> list[str]:
    marker = "function ModulesPage"
    start = app_source.find(marker)
    if start < 0:
        return ["GUI Module Explorer function is missing."]
    catalog = app_source[start:]
    return [
        f"Module Explorer is missing an entry for '{page_id}'."
        for page_id in page_ids
        if f'id: "{page_id}"' not in catalog
    ]


def model_registry_filter_issues(api_source: str, client_source: str, app_source: str, e2e_source: str) -> list[str]:
    """Check the model registry filter path from its API through GUI and browser tests."""
    issues: list[str] = []
    for token in (
        'search: str = Query(default="", max_length=160)',
        "favorite_only: bool = False",
        "format: str | None = Query",
        "tag: str | None = Query",
        'sort_by: Literal["name", "source", "format", "parameters", "quantization", "favorite"]',
        'sort_order: Literal["asc", "desc"]',
        '"has_more": offset + limit < total',
    ):
        if token not in api_source:
            issues.append("Model registry API is missing a supported filter/sort/pagination contract: " + token)
    for token in (
        'query.set("search"',
        'query.set("favorite_only"',
        'query.set("format"',
        'query.set("tag"',
        'query.set("sort_by"',
        'query.set("sort_order"',
    ):
        if token not in client_source:
            issues.append("Typed API client is missing model registry query serialization: " + token)
    for token in (
        'aria-label="Search model registry"',
        'aria-label="Exact model format"',
        'aria-label="Exact model tag"',
        'aria-label="Favorites only"',
        "SAVED_MODEL_FILTERS_KEY",
        "localStorage.setItem(SAVED_MODEL_FILTERS_KEY",
        "setAppliedFilters] = useState<ModelRegistryFilters>",
        "modelsPage(models.length, 25, appliedFilters)",
    ):
        if token not in app_source:
            issues.append("Models GUI is missing integrated filter/preset behavior: " + token)
    for token in (
        "model registry filters and saved presets",
        'searchParams.get("favorite_only")',
        'searchParams.get("sort_by")',
        "Save current filters",
        'getByRole("button", { name: "Apply", exact: true })',
    ):
        if token not in e2e_source:
            issues.append("Model registry browser acceptance coverage is missing: " + token)
    return issues


def model_compatibility_issues(core_source: str, api_source: str, client_source: str, app_source: str, e2e_source: str) -> list[str]:
    """Check model-fit estimates are connected from the backend into the existing Models page."""
    issues: list[str] = []
    for token in (
        "def estimate_model_compatibility(",
        '"estimated_weight_gb": estimated_weights',
        '"estimated_runtime_memory_gb": estimated_runtime',
        '"system_ram_fit": ram_fit',
        '"gpu_memory_fit": vram_fit',
        '"format_compatibility": format_compatibility',
    ):
        if token not in core_source:
            issues.append("Model fit engine is missing an evidence-labelled estimate: " + token)
    for token in (
        '@router.get("/models/{model_id}/compatibility")',
        "estimate_model_compatibility(model, detect_hardware())",
        'return {"report": report}',
    ):
        if token not in api_source:
            issues.append("Model fit API is missing a backend connection: " + token)
    for token in (
        "export type WorkspaceModelCompatibility",
        "modelCompatibility: (id: string)",
        "/compatibility",
    ):
        if token not in client_source:
            issues.append("Typed API client is missing the model fit endpoint: " + token)
    for token in (
        'aria-label={`Check hardware fit for ${model.name}`}',
    ):
        if token not in app_source:
            issues.append("Models GUI is missing the compatibility action: " + token)
    for token in (
        'getByRole("button", { name: "Check hardware fit for Qwen Seven" })',
        'getByRole("heading", { name: "Hardware fit · Qwen Seven" })',
        'getByText("UNLIKELY", { exact: true })',
    ):
        if token not in e2e_source:
            issues.append("Model fit browser coverage is missing: " + token)
    return issues


def inference_benchmark_issues(core_source: str, api_source: str, client_source: str, panel_source: str, e2e_source: str) -> list[str]:
    """Check benchmark implementation connects the measured loopback runtime to Runtime UI."""
    issues: list[str] = []
    for token in (
        "def run_local_inference_benchmark(",
        "ThreadPoolExecutor",
        "measured_requests > 10",
        '"completion_tokens_per_second":',
        '"prompt_returned": False',
        '"responses_returned": False',
        '"results_persisted": False',
    ):
        if token not in core_source:
            issues.append("Local inference benchmark engine is missing a bounded measurement contract: " + token)
    for token in (
        '@router.post("/benchmark")',
        "run_local_inference_benchmark(",
        "request.iterations * request.concurrency > 10",
    ):
        if token not in api_source:
            issues.append("Local inference benchmark API is missing: " + token)
    for token in (
        "export type LocalInferenceBenchmark",
        '"/api/inference/benchmark"',
        "runLocalInferenceBenchmark:",
    ):
        if token not in client_source:
            issues.append("Typed inference benchmark client is missing: " + token)
    for token in (
        'aria-labelledby="inference-benchmark-title"',
        'aria-label="Benchmark iterations"',
        'aria-label="Benchmark concurrency"',
        'onClick={() => void benchmarkLocalModel()}',
        "runLocalInferenceBenchmark({",
        "Benchmark this prompt",
        "Inference benchmark result",
    ):
        if token not in panel_source:
            issues.append("Runtime GUI benchmark controls/results are missing: " + token)
    for token in (
        "Measured local inference benchmark",
        '"/api/inference/benchmark"',
        "blocks a requested workload above the ten measured-request limit",
        "42.857 tokens/s",
    ):
        if token not in e2e_source:
            issues.append("Inference benchmark browser acceptance coverage is missing: " + token)
    return issues


def api_playground_issues(component: str, client: str) -> list[str]:
    """Validate the Playground's actual typed GET-only client contract and disclosure."""
    issues: list[str] = []
    client_is_bounded_get = all(
        token in client
        for token in (
            "PlaygroundEndpoint",
            "playgroundEndpointPaths",
            "playgroundRead",
            'method: "GET"',
        )
    )
    if "playgroundRead" not in component or not client_is_bounded_get:
        issues.append(
            "API playground must use the typed endpoint allowlist and GET-only API client."
        )
    if not all(
        token in component
        for token in ("allowlist", "GET only", "Arbitrary URLs", "mutating methods")
    ):
        issues.append(
            "API playground must disclose the allowlist, GET-only boundary, and rejected arbitrary/mutating requests."
        )
    return issues

def inspect(root: Path) -> dict[str, Any]:
    failures: list[str] = []
    warnings: list[str] = []
    required = [
        "pyproject.toml", "axiom/version.py", "ROADMAP.md", "src/App.tsx",
        "src/api/client.ts", "src/components/ApiPlayground.tsx", "src/components/RuntimeConnectorPanel.tsx", "src/components/AgentProfiles.tsx", "src/components/LocalInferencePanel.tsx", "src/styles.css",
        "axiom/api/server.py", "axiom/api/workspace.py", "axiom/api/inference.py", "axiom/core/inference.py", "axiom/models/compatibility.py", "axiom/api/diagnostics.py", "axiom/api/runtime_discovery.py", "axiom/api/agent_profiles.py", "axiom/core/runtime_discovery.py", "axiom/core/agent_profiles.py", "axiom/cli/agent_profiles.py", "scripts/release_smoke.py",
        "tests/test_release_smoke.py", "e2e/helpers/auth.ts", "e2e/modules.spec.ts", "e2e/workflows.spec.ts", "e2e/evaluation.spec.ts",
        "e2e/model-registry-filters.spec.ts", "e2e/inference-benchmark.spec.ts", "tests/test_workspace_model_registry_filters.py",
        "tests/test_model_compatibility.py", "tests/test_inference_benchmark.py", "tests/test_inference_benchmark_api.py", "tests/test_runtime_discovery.py", "tests/test_runtime_discovery_api.py", "tests/test_agent_profiles.py", "tests/test_agent_profiles_api.py", "tests/test_agent_profiles_cli.py", "e2e/api-playground.spec.ts", "e2e/runtime-connectors.spec.ts", "e2e/agent-profiles.spec.ts",
        "docs/Runtime-Discovery.md", "docs/Agent-Profiles.md", "docs/Api-Playground.md", "docs/Inference-Benchmarking.md", ".github/workflows/quality-gates.yml", ".github/workflows/nightly-build.yml",
    ]
    for relative in required:
        if not (root / relative).is_file():
            failures.append(f"Missing required file: {relative}")
    if failures:
        return {"schema_version": 1, "status": "failed", "failures": failures, "warnings": warnings}

    try:
        project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
        project_version = str(project["project"]["version"])
    except (OSError, KeyError, tomllib.TOMLDecodeError) as exc:
        failures.append(f"Could not read project metadata: {type(exc).__name__}")
        project_version = "unknown"

    version_source = (root / "axiom/version.py").read_text(encoding="utf-8")
    version_match = re.search(r'^__version__\s*=\s*["\']([^"\']+)', version_source, re.MULTILINE)
    runtime_version = version_match.group(1) if version_match else "unknown"
    if project_version != runtime_version:
        failures.append(f"Python package version ({project_version}) differs from runtime version ({runtime_version}).")

    roadmap = (root / "ROADMAP.md").read_text(encoding="utf-8")
    failures.extend(roadmap_issues(roadmap))

    app_source = (root / "src/App.tsx").read_text(encoding="utf-8")
    failures.extend(page_registration_issues(app_source, "api-playground"))
    failures.extend(page_registration_issues(app_source, "agent-profiles"))
    failures.extend(module_catalog_issues(app_source))
    component = (root / "src/components/ApiPlayground.tsx").read_text(encoding="utf-8")
    client = (root / "src/api/client.ts").read_text(encoding="utf-8")
    workspace_api = (root / "axiom/api/workspace.py").read_text(encoding="utf-8")
    model_registry_e2e = (root / "e2e/model-registry-filters.spec.ts").read_text(encoding="utf-8")
    failures.extend(model_registry_filter_issues(workspace_api, client, app_source, model_registry_e2e))
    compatibility_core = (root / "axiom/models/compatibility.py").read_text(encoding="utf-8")
    compatibility_e2e = model_registry_e2e
    failures.extend(model_compatibility_issues(compatibility_core, workspace_api, client, app_source, compatibility_e2e))
    inference_core = (root / "axiom/core/inference.py").read_text(encoding="utf-8")
    inference_api = (root / "axiom/api/inference.py").read_text(encoding="utf-8")
    inference_panel = (root / "src/components/LocalInferencePanel.tsx").read_text(encoding="utf-8")
    inference_e2e = (root / "e2e/inference-benchmark.spec.ts").read_text(encoding="utf-8")
    failures.extend(inference_benchmark_issues(inference_core, inference_api, client, inference_panel, inference_e2e))
    for path in (
        "/api/health", "/api/meta", "/api/workspace/runtime",
        "/api/workspace/models?offset=0&limit=5", "/api/workspace/datasets",
        "/api/workspace/events", "/api/diagnostics/workspace",
        "/api/diagnostics/roadmap", "/api/diagnostics/runtime-connectors",
    ):
        if path not in client:
            failures.append(f"API playground allowlist is missing {path}.")
    failures.extend(api_playground_issues(component, client))
    if "15_000" not in client:
        failures.append("The shared API client timeout is missing or has changed; review timeout policy.")
    styles_source = (root / "src/styles.css").read_text(encoding="utf-8")
    if "api-playground-json" not in styles_source:
        failures.append("API playground response styling is missing.")
    if "runtime-connector-row" not in styles_source:
        failures.append("Runtime connector panel styling is missing.")
    if "runtimeConnectors" not in client or "RuntimeConnectorPanel" not in app_source:
        failures.append("Runtime connector discovery is not wired through the client and GUI.")
    if not all(token in client for token in ("agentProfiles", "createAgentProfile", "updateAgentProfile", "deleteAgentProfile")):
        failures.append("Agent profile operations are missing from the typed API client.")
    if "AgentProfiles" not in app_source or "register_agent_profiles(app)" not in (root / "axiom/cli/main.py").read_text(encoding="utf-8"):
        failures.append("Agent profiles are not wired to both the GUI and CLI entry point.")
    server_source = (root / "axiom/api/server.py").read_text(encoding="utf-8")
    if "agent_profiles_router" not in server_source:
        failures.append("Agent profile API router is not registered.")
    runtime_api = (root / "axiom/api/runtime_discovery.py").read_text(encoding="utf-8")
    if '@router.get("/runtime-connectors")' not in runtime_api or "discover_runtime_connectors" not in runtime_api:
        failures.append("Runtime connector discovery endpoint is not registered.")
    if "runtime_discovery_router" not in server_source:
        failures.append("Runtime connector discovery router is not included in the API application.")

    try:
        package = json.loads((root / "package.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        failures.append(f"Could not parse package.json: {type(exc).__name__}")
        package = {}
    scripts = package.get("scripts", {})
    for name in ("lint", "build", "e2e"):
        if name not in scripts:
            failures.append(f"package.json is missing the '{name}' script.")

    for relative in (
        "e2e/helpers/auth.ts", "e2e/modules.spec.ts", "e2e/workflows.spec.ts",
        "e2e/evaluation.spec.ts", "e2e/api-playground.spec.ts",
        "e2e/runtime-connectors.spec.ts", "e2e/agent-profiles.spec.ts",
        "e2e/model-registry-filters.spec.ts", "e2e/inference-benchmark.spec.ts",
    ):
        target = root / relative
        if not target.is_file():
            failures.append(f"Browser E2E must bootstrap the local control-center session: {relative}")
        elif relative != "e2e/helpers/auth.ts" and "ensureAuthenticated" not in target.read_text(encoding="utf-8"):
            failures.append(f"Browser E2E must bootstrap the local control-center session: {relative}")

    return {
        "schema_version": 1,
        "status": "passed" if not failures else "failed",
        "project_version": project_version,
        "runtime_version": runtime_version,
        "roadmap_deliverables": len(ROADMAP_PATTERN.findall(roadmap)),
        "failures": failures,
        "warnings": warnings,
        "scope_note": "Static acceptance checks only; they do not establish runtime benchmark or training execution support.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="AXIOM repository root")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of text")
    args = parser.parse_args()
    report = inspect(args.root.resolve())
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"AXIOM release smoke: {report['status'].upper()}")
        if "project_version" in report:
            print(f"Version: {report['project_version']} (runtime {report['runtime_version']})")
            print(f"Roadmap deliverables detected: {report['roadmap_deliverables']}")
        for issue in report.get("failures", []):
            print(f"FAIL: {issue}")
        for warning in report.get("warnings", []):
            print(f"WARN: {warning}")
        if report.get("scope_note"):
            print(report["scope_note"])
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
