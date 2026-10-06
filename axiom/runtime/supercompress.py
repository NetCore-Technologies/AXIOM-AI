from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib import error, request


DEFAULT_BASE_URL = "https://api.supercompress.dev"


@dataclass
class CompressionResult:
    compressed_text: str
    original_tokens: int | None
    kept_tokens: int | None
    tokens_saved: int | None
    savings_pct: float | None
    compression_risk: str | None
    policy_name: str | None
    mode: str | None


def compress_context(
    context: str,
    query: str,
    *,
    budget_ratio: float = 0.35,
    ccr: bool = False,
) -> CompressionResult:
    api_key = os.getenv("SUPERCOMPRESS_API_KEY")

    if not api_key:
        raise RuntimeError(
            "SUPERCOMPRESS_API_KEY is not configured."
        )

    base_url = os.getenv(
        "SUPERCOMPRESS_API_BASE",
        DEFAULT_BASE_URL,
    ).rstrip("/")

    payload = {
        "context": context,
        "query": query,
        "budget_ratio": budget_ratio,
        "ccr": ccr,
    }

    req = request.Request(
        f"{base_url}/api/v1/compress",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-API-Key": api_key,
            "User-Agent": "AXIOM-AI/0.1",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=30) as response:
            data = json.loads(
                response.read().decode("utf-8")
            )
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")

        if exc.code == 503 and "neural_unavailable" in body:
            raise RuntimeError(
                "SuperCompress neural compression is currently unavailable. "
                "The remote service accepted the request but its neural "
                "compression backend is not configured."
            ) from exc

        raise RuntimeError(
            f"SuperCompress HTTP {exc.code}: {body}"
        ) from exc
    except error.URLError as exc:
        raise RuntimeError(
            f"SuperCompress connection failed: {exc.reason}"
        ) from exc

    compressed = (
        data.get("compressed_text")
        or data.get("compressed")
    )

    if not isinstance(compressed, str):
        raise RuntimeError(
            "SuperCompress response did not contain compressed text."
        )

    original = data.get("original_tokens")
    kept = data.get("kept_tokens")
    saved = data.get("tokens_saved")
    savings = data.get("kv_savings_pct")

    if savings is None and original and kept is not None:
        savings = ((original - kept) / original) * 100

    return CompressionResult(
        compressed_text=compressed,
        original_tokens=original,
        kept_tokens=kept,
        tokens_saved=saved,
        savings_pct=savings,
        compression_risk=data.get("compression_risk"),
        policy_name=data.get("policy_name"),
        mode=data.get("mode"),
    )
