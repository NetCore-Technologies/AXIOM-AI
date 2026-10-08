

from __future__ import annotations
def _safe_model_path(user_path: str, base_dir: Path) -> Path:
    """Resolve a user-supplied model path beneath the configured model directory."""
    base = base_dir.expanduser().resolve()
    candidate = (base / user_path).resolve()
    if candidate != base and base not in candidate.parents:
        raise ValueError("Model path escapes the configured model directory")
    return candidate
"""Safe, transparent model policy/safety audit.

This module intentionally does not remove or bypass safety controls.
"""


import json
from pathlib import Path
from typing import Any

HINTS = (
    "safety",
    "guardrail",
    "policy",
    "moderation",
    "refusal",
    "content_filter",
    "safety_checker",
    "chat_template",
)

CONFIG_NAMES = {"config.json", "generation_config.json", "tokenizer_config.json"}




def _safe_path(user_path: str, base_dir: Path) -> Path:
    """Resolve a user supplied path beneath a trusted base directory."""
    base = base_dir.expanduser().resolve()
    candidate = (base / user_path).resolve()
    if candidate != base and base not in candidate.parents:
        raise ValueError("Path escapes the allowed directory")
    return candidate

def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def audit_model(model_path: str) -> dict[str, Any]:
    root = _safe_path(model_path, Path("models"))

    if not root.exists():
        raise FileNotFoundError(model_path)

    if root.is_file():
        files = [root]
        base = root.parent
    else:
        files = [p for p in root.rglob("*") if p.is_file()]
        base = root

    indicators: set[str] = set()
    configs: list[str] = []

    for path in files[:5000]:
        rel = str(path.relative_to(base))

        if any(hint in path.name.lower() for hint in HINTS):
            indicators.add(rel)

        if path.name.lower() in CONFIG_NAMES:
            configs.append(rel)
            blob = json.dumps(_load_json(path), ensure_ascii=False).lower()

            for hint in HINTS:
                if hint in blob:
                    indicators.add(f"{rel}: contains '{hint}'")

    return {
        "model": model_path,
        "status": "review_required" if indicators else "no_obvious_policy_indicators",
        "policy_indicators": sorted(indicators),
        "config_files": sorted(configs),
        "scope": (
            "Audit only. AXIOM does not remove, disable, bypass, "
            "or weaken model safety mechanisms."
        ),
    }
