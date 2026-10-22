from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("axiom_release_smoke", ROOT / "scripts" / "release_smoke.py")
assert SPEC and SPEC.loader
release_smoke = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release_smoke)


def test_roadmap_audit_accepts_all_unique_deliverables() -> None:
    markdown = "\n".join(
        f"- [R{i:03d} · {'Planned' if i % 2 else 'Implemented; tests passing'}] Requirement {i}."
        for i in range(1, 121)
    )
    assert release_smoke.roadmap_issues(markdown) == []


def test_roadmap_audit_detects_duplicates_missing_ids_and_unknown_status() -> None:
    markdown = "- [R001 · Maybe] A\n- [R001 · Planned] Duplicate\n"
    issues = release_smoke.roadmap_issues(markdown)
    assert any("Expected 120" in item for item in issues)
    assert any("Missing roadmap IDs" in item for item in issues)
    assert any("Duplicate roadmap IDs: R001" in item for item in issues)
    assert any("Unknown roadmap statuses: Maybe" in item for item in issues)


def test_gui_page_registration_requires_union_nav_metadata_and_switch() -> None:
    complete = '''
  | "api-playground"
  { id: "api-playground", label: "API Playground" }
  "api-playground": { label: "API Playground" }
  case "api-playground": return <ApiPlayground />;
'''
    assert release_smoke.page_registration_issues(complete, "api-playground") == []
    incomplete = '''
  | "api-playground"
  { id: "api-playground" }
'''
    issues = release_smoke.page_registration_issues(incomplete, "api-playground")
    assert any("page metadata" in item for item in issues)
    assert any("render switch" in item for item in issues)


def test_agent_profile_page_registration_requires_all_four_gui_links() -> None:
    source = '''
  | "agent-profiles"
    id: "agent-profiles"
  "agent-profiles": { label: "Agent Profiles" }
    case "agent-profiles": return <AgentProfiles />;
'''
    assert release_smoke.page_registration_issues(source, "agent-profiles") == []


def test_module_explorer_requires_new_gui_pages_in_the_catalog() -> None:
    complete = 'function ModulesPage() { const entries = [{ id: "api-playground" }, { id: "agent-profiles" }]; }'
    assert release_smoke.module_catalog_issues(complete) == []
    incomplete = "function ModulesPage() { const entries = [{ id: \"api-playground\" }]; }"
    assert any("agent-profiles" in issue for issue in release_smoke.module_catalog_issues(incomplete))


def test_toolkit_catalog_has_120_unique_tools_and_every_handler() -> None:
    component = (ROOT / "src" / "components" / "AxiomToolkit.tsx").read_text(encoding="utf-8")
    assert release_smoke.toolkit_catalog_issues(component) == []


def test_toolkit_catalog_rejects_missing_operation_handler() -> None:
    component = (ROOT / "src" / "components" / "AxiomToolkit.tsx").read_text(encoding="utf-8")
    broken = component.replace('case "filename":', 'case "missing-handler":', 1)
    issues = release_smoke.toolkit_catalog_issues(broken)
    assert any("no operation handler: filename" in issue for issue in issues)


def test_toolkit_page_requires_navigation_metadata_and_module_catalog_entry() -> None:
    complete = '''
  | "toolkit"
  { id: "toolkit", label: "AI Toolkit" }
  toolkit: { label: "AI Toolkit" }
  case "toolkit": return <AxiomToolkit />;
  function ModulesPage() { const entries = [{ id: "toolkit" }]; }
'''
    assert release_smoke.page_registration_issues(complete, "toolkit") == []
    assert release_smoke.module_catalog_issues(complete, ("toolkit",)) == []
    assert release_smoke.module_catalog_issues("function ModulesPage() { const entries = []; }", ("toolkit",)) == [
        "Module Explorer is missing an entry for 'toolkit'."
    ]


def test_api_playground_smoke_checks_typed_get_only_contract() -> None:
    component = (
        "playgroundRead allowlist GET only Arbitrary URLs mutating methods"
    )
    client = (
        "PlaygroundEndpoint playgroundEndpointPaths playgroundRead method: \"GET\""
    )
    assert release_smoke.api_playground_issues(component, client) == []


def test_api_playground_smoke_rejects_unbounded_client_or_missing_disclosure() -> None:
    component = "playgroundRead allowlist"
    client = "playgroundRead fetch(any_url)"
    issues = release_smoke.api_playground_issues(component, client)
    assert any("typed endpoint allowlist" in issue for issue in issues)
    assert any("disclose the allowlist" in issue for issue in issues)
