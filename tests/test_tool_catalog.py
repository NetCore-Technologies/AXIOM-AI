from __future__ import annotations

import json
import re
from dataclasses import asdict, is_dataclass

from axiom.tools.catalog import (
    ALL_PLATFORMS,
    CAPABILITY_CATALOG,
    KEEP_AWAKE_CAPABILITY,
    TOOL_CATALOG,
    CapabilitySpec,
    ToolSpec,
)

EXPECTED_TOOL_IDS = {
    "codex",
    "claude-code",
    "antigravity-cli",
    "github-copilot-cli",
    "freebuff",
    "cursor-agent",
    "free-pi",
    "opencode",
    "gemini-cli",
    "openrouter",
    "zai-glm",
}


def test_catalog_contains_requested_tools_with_unique_ids():
    ids = [tool.id for tool in TOOL_CATALOG]

    assert set(ids) == EXPECTED_TOOL_IDS
    assert len(ids) == len(set(ids))
    assert all(isinstance(tool, ToolSpec) for tool in TOOL_CATALOG)


def test_cli_executable_names_are_present_and_globally_unique():
    cli_tools = [tool for tool in TOOL_CATALOG if tool.kind == "cli"]
    executable_names = [
        executable
        for tool in cli_tools
        for executable in tool.executable_names
    ]

    assert cli_tools
    assert all(executable_names)
    assert len(executable_names) == len(set(executable_names))
    assert all(executable == executable.strip() for executable in executable_names)
    assert all(tool.executable_names for tool in TOOL_CATALOG if tool.kind == "cli")
    assert all(not tool.executable_names for tool in TOOL_CATALOG if tool.kind == "api")


def test_every_tool_has_supported_platforms_and_a_candidate_per_platform():
    allowed_platforms = set(ALL_PLATFORMS)

    for tool in TOOL_CATALOG:
        supported = set(tool.supported_platforms)
        candidate_platforms = {candidate.platform for candidate in tool.install_candidates}

        assert supported == allowed_platforms
        assert supported <= allowed_platforms
        assert candidate_platforms == supported
        assert tool.homepage_url.startswith("https://")
        assert tool.source_url.startswith("https://")
        assert all(candidate.source_url.startswith("https://") for candidate in tool.install_candidates)


def test_catalog_and_capability_are_frozen_data_only_records():
    assert all(is_dataclass(tool) for tool in TOOL_CATALOG)
    assert all(is_dataclass(capability) for capability in CAPABILITY_CATALOG)
    assert all(type(tool).__dataclass_params__.frozen for tool in TOOL_CATALOG)
    assert all(type(capability).__dataclass_params__.frozen for capability in CAPABILITY_CATALOG)
    assert all(isinstance(tool, ToolSpec) for tool in TOOL_CATALOG)
    assert all(isinstance(capability, CapabilitySpec) for capability in CAPABILITY_CATALOG)


def test_catalog_contains_no_secret_values():
    serialized = json.dumps(
        {
            "tools": [asdict(tool) for tool in TOOL_CATALOG],
            "capabilities": [asdict(capability) for capability in CAPABILITY_CATALOG],
        },
        sort_keys=True,
    )
    secret_value_patterns = (
        r"\bsk-[A-Za-z0-9_-]{16,}",
        r"\bghp_[A-Za-z0-9]{20,}",
        r"\bgithub_pat_[A-Za-z0-9_]{20,}",
        r"\bAIza[A-Za-z0-9_-]{20,}",
        r"\bxox[baprs]-[A-Za-z0-9-]{10,}",
        r"\beyJ[A-Za-z0-9_-]{20,}\.",
    )

    assert not any(re.search(pattern, serialized) for pattern in secret_value_patterns)
    assert "YOUR_API_KEY" not in serialized
    assert "your_api_key" not in serialized


def test_keep_awake_capability_is_future_axiom_session_and_not_a_portability_claim_for_insomnia():
    assert KEEP_AWAKE_CAPABILITY.id == "insomnia-keep-awake"
    assert KEEP_AWAKE_CAPABILITY.command == "axiom session --keep-awake"
    assert set(KEEP_AWAKE_CAPABILITY.supported_platforms) == set(ALL_PLATFORMS)
    assert "krishhgg/Insomnia" in KEEP_AWAKE_CAPABILITY.reference_url
    assert "Future AXIOM capability" in KEEP_AWAKE_CAPABILITY.notes
    assert "macOS-only" in KEEP_AWAKE_CAPABILITY.notes
    assert "not claimed to run on Linux or Windows" in KEEP_AWAKE_CAPABILITY.notes
