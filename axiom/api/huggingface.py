"""Hugging Face helpers for AXIOM."""

from __future__ import annotations

from typing import Any


def search_models(query: str, limit: int = 10) -> list[dict[str, Any]]:
    try:
        from huggingface_hub import HfApi
    except ImportError:
        return [{"error": "huggingface_hub is not installed (pip install huggingface_hub)"}]

    api = HfApi()
    rows: list[dict[str, Any]] = []

    for item in api.list_models(search=query, limit=max(1, min(int(limit), 50))):
        rows.append(
            {
                "id": item.id,
                "downloads": getattr(item, "downloads", None),
                "likes": getattr(item, "likes", None),
                "pipeline_tag": getattr(item, "pipeline_tag", None),
            }
        )

    return rows


def get_model_info(model_id: str) -> dict[str, Any]:
    try:
        from huggingface_hub import HfApi
    except ImportError:
        return {"error": "huggingface_hub is not installed (pip install huggingface_hub)"}

    info = HfApi().model_info(model_id)

    return {
        "id": info.id,
        "downloads": getattr(info, "downloads", None),
        "likes": getattr(info, "likes", None),
        "pipeline_tag": getattr(info, "pipeline_tag", None),
        "library_name": getattr(info, "library_name", None),
        "tags": list(getattr(info, "tags", None) or []),
    }
