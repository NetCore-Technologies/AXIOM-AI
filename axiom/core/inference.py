"""Bounded local inference adapter for an Ollama instance on loopback only."""
from __future__ import annotations

import json
import re
import shutil
from datetime import UTC, datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

OLLAMA_ENDPOINT = "http://127.0.0.1:11434"
_STATUS_TIMEOUT_SECONDS = 2.5
_GENERATION_TIMEOUT_SECONDS = 300
_MAX_PROMPT_CHARS = 12_000
_MAX_MODEL_NAME_CHARS = 120
_MAX_GENERATED_TOKENS = 2_048
_MODEL_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,119}$")


class InferenceRuntimeError(RuntimeError):
    """Raised when the local inference runtime cannot complete a request."""


def validate_model_name(model: str) -> str:
    value = model.strip() if isinstance(model, str) else ""
    if not value or len(value) > _MAX_MODEL_NAME_CHARS or "://" in value or not _MODEL_NAME.fullmatch(value):
        raise ValueError(
            "Model name must be 1–120 characters and contain only letters, digits, '.', '_', ':', '/', or '-'."
        )
    return value


def validate_generation(prompt: str, num_predict: int, temperature: float) -> tuple[str, int, float]:
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Prompt must contain at least one non-whitespace character.")
    if len(prompt) > _MAX_PROMPT_CHARS:
        raise ValueError(f"Prompt exceeds the {_MAX_PROMPT_CHARS:,}-character limit.")
    if isinstance(num_predict, bool) or not isinstance(num_predict, int) or not 1 <= num_predict <= _MAX_GENERATED_TOKENS:
        raise ValueError(f"Maximum generated tokens must be between 1 and {_MAX_GENERATED_TOKENS}.")
    if isinstance(temperature, bool) or not isinstance(temperature, (int, float)) or not 0 <= float(temperature) <= 2:
        raise ValueError("Temperature must be between 0 and 2.")
    return prompt, num_predict, float(temperature)


def _open_loopback(request: Request, timeout: float):
    # Explicitly disable environment-configured proxies. The request destination
    # is a constant IPv4 loopback URL; callers cannot provide a hostname or URL.
    return build_opener(ProxyHandler({})).open(request, timeout=timeout)


def _request_json(path: str, *, payload: dict[str, Any] | None = None, timeout: float) -> dict[str, Any]:
    if path not in {"/api/tags", "/api/generate"}:
        raise ValueError("Unsupported local inference endpoint.")
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        f"{OLLAMA_ENDPOINT}{path}",
        data=data,
        method="GET" if data is None else "POST",
        headers={"Accept": "application/json", **({"Content-Type": "application/json"} if data is not None else {})},
    )
    try:
        with _open_loopback(request, timeout) as response:
            raw = response.read(2_000_000)
    except HTTPError as exc:
        try:
            error_raw = exc.read(8192).decode("utf-8", errors="replace")
            parsed = json.loads(error_raw) if error_raw else {}
            detail = parsed.get("error", "") if isinstance(parsed, dict) else ""
        except (ValueError, UnicodeError):
            detail = ""
        detail = str(detail).replace("\n", " ").strip()[:240]
        if exc.code == 404 and path == "/api/generate":
            raise InferenceRuntimeError(detail or "Ollama could not find that model. Pull the model locally first.") from None
        raise InferenceRuntimeError(f"Local Ollama request failed (HTTP {exc.code}). {detail}".strip()) from None
    except (URLError, TimeoutError, OSError) as exc:
        # Do not reveal machine-local paths or proxy/config details.
        raise InferenceRuntimeError(
            "Ollama is not responding at 127.0.0.1:11434. Start the local Ollama service and retry."
        ) from None
    try:
        result = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError):
        raise InferenceRuntimeError("The local inference runtime returned invalid JSON.") from None
    if not isinstance(result, dict):
        raise InferenceRuntimeError("The local inference runtime returned an unexpected response shape.")
    return result


def runtime_status() -> dict[str, Any]:
    """Probe only the fixed Ollama loopback API; never launch or contact remote services."""
    base: dict[str, Any] = {
        "backend": "ollama",
        "endpoint": OLLAMA_ENDPOINT,
        "runtime_installed": shutil.which("ollama") is not None,
        "status": "offline",
        "models": [],
        "error": None,
        "checked_at": datetime.now(UTC).isoformat(),
    }
    try:
        result = _request_json("/api/tags", timeout=_STATUS_TIMEOUT_SECONDS)
        raw_models = result.get("models", [])
        if not isinstance(raw_models, list):
            raise InferenceRuntimeError("Ollama returned an invalid model inventory.")
        names: list[str] = []
        for item in raw_models[:100]:
            if isinstance(item, dict):
                name = item.get("name")
                if isinstance(name, str):
                    try:
                        names.append(validate_model_name(name))
                    except ValueError:
                        continue
        base.update(status="online", models=names)
    except InferenceRuntimeError:
        base["error"] = f"Local inference runtime is unavailable at {OLLAMA_ENDPOINT}."
    return base


def run_local_inference(
    model: str,
    prompt: str,
    num_predict: int = 256,
    temperature: float = 0.7,
) -> dict[str, Any]:
    """Generate text through a local Ollama service with bounded input/output."""
    model = validate_model_name(model)
    prompt, num_predict, temperature = validate_generation(prompt, num_predict, temperature)
    result = _request_json(
        "/api/generate",
        payload={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": num_predict, "temperature": temperature},
        },
        timeout=_GENERATION_TIMEOUT_SECONDS,
    )
    response = result.get("response")
    if not isinstance(response, str):
        raise InferenceRuntimeError("The local inference runtime did not return generated text.")
    # Output is limited by Ollama's num_predict option; truncate defensively in
    # case a compatible runtime ignores the option or returns an oversized body.
    response = response[:100_000]
    total_duration = result.get("total_duration")
    return {
        "model": model,
        "response": response,
        "done": bool(result.get("done", True)),
        "prompt_eval_count": result.get("prompt_eval_count") if isinstance(result.get("prompt_eval_count"), int) else None,
        "eval_count": result.get("eval_count") if isinstance(result.get("eval_count"), int) else None,
        "total_duration_ms": round(total_duration / 1_000_000, 2) if isinstance(total_duration, (int, float)) and total_duration >= 0 else None,
        "generated_at": datetime.now(UTC).isoformat(),
    }
