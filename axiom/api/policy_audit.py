from __future__ import annotations

from pathlib import Path
import json
from typing import Any

from axiom.api.model_paths import validate_model_path


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


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def audit_model(model_path: str) -> dict[str, Any]:
    root = validate_model_path(model_path)

    if root.is_file():
        base = root.parent
        files = (root,)
    else:
        base = root
        files = tuple(
            item
            for item in root.rglob("*")
            if item.is_file()
        )[:5000]

    indicators: set[str] = set()
    configs: list[str] = []

    for path in files:
        relative = str(path.relative_to(base))

        if any(hint in path.name.lower() for hint in HINTS):
            indicators.add(relative)

        if path.suffix.lower() == ".json" and path.name.lower() in {
            "config.json",
            "generation_config.json",
            "tokenizer_config.json",
        }:
            configs.append(relative)
            blob = json.dumps(
                _load_json(path),
                ensure_ascii=False,
            ).lower()

            for hint in HINTS:
                if hint in blob:
                    indicators.add(
                        f"{relative}: contains '{hint}'"
                    )

    return {
        "model": str(root),
        "status": (
            "review_required"
            if indicators
            else "no_obvious_policy_indicators"
        ),
        "policy_indicators": sorted(indicators),
        "config_files": sorted(configs),
        "scope": (
            "Audit only. AXIOM does not remove, disable, bypass, "
            "or weaken model safety mechanisms."
        ),
    }
