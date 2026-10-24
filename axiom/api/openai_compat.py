"""OpenAI-compatible chat-completions surface over AXIOM Native Engine.

This API intentionally serves only models discovered under AXIOM's configured trusted
model roots. It does not forward inference to Ollama, Transformers, or remote providers.
"""
from __future__ import annotations

import asyncio
import json
import hmac
import os
import time
import uuid
from queue import Empty, Full, Queue
from threading import Event, Thread
from typing import Any, AsyncIterator, Iterator, Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from starlette.responses import JSONResponse, StreamingResponse

from axiom.core.engine import AxiomEngineError, discover_local_engine_assets, generate_local_stream

router = APIRouter()
_STREAM_END = object()
_STREAM_QUEUE_SIZE = 2


def _authorization_error(request: Request) -> JSONResponse | None:
    """Enforce an optional bearer token for clients exposed beyond loopback."""
    expected = os.environ.get("AXIOM_OPENAI_API_TOKEN", "").strip()
    if not expected:
        return None
    authorization = request.headers.get("Authorization", "")
    scheme, separator, supplied = authorization.partition(" ")
    matched = bool(separator and scheme.lower() == "bearer" and hmac.compare_digest(supplied.encode("utf-8"), expected.encode("utf-8")))
    if matched:
        return None
    return JSONResponse(
        status_code=401,
        headers={"WWW-Authenticate": "Bearer"},
        content={"error": {"message": "A valid AXIOM bearer token is required.", "type": "authentication_error", "param": None, "code": "invalid_api_key"}},
    )


def _openai_error(message: str, status_code: int, *, code: str | None = None,
                  error_type: str = "invalid_request_error") -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"message": message, "type": error_type, "param": None, "code": code}},
    )


def _native_models() -> list[dict[str, Any]]:
    report = discover_local_engine_assets()
    models = report.get("models", []) if isinstance(report, dict) else []
    return [
        item for item in models
        if isinstance(item, dict)
        and isinstance(item.get("name"), str)
        and isinstance(item.get("path"), str)
        and item.get("model_type") in {"llama", "mistral", "qwen2", "qwen3"}
    ]


def _resolve_model(model_id: str) -> dict[str, Any] | None:
    matches = [item for item in _native_models() if item.get("name") == model_id]
    return matches[0] if len(matches) == 1 else None


class OpenAIChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=12000)

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Chat message content must not be blank.")
        return value


class OpenAIChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: str = Field(min_length=1, max_length=256)
    messages: list[OpenAIChatMessage] = Field(min_length=1, max_length=128)
    max_tokens: int | None = Field(default=256, ge=1, le=2048)
    max_completion_tokens: int | None = Field(default=None, ge=1, le=2048)
    temperature: float = Field(default=0.7, ge=0, le=2)
    top_p: float = Field(default=0.9, gt=0, le=1)
    top_k: int = Field(default=0, ge=0, le=100000)
    repetition_penalty: float = Field(default=1.0, ge=0.1, le=5)
    seed: int | None = Field(default=None, ge=0, le=9223372036854775807)
    stop: str | list[str] | None = None
    stream: bool = False
    n: int = Field(default=1, ge=1, le=1)
    user: str | None = Field(default=None, max_length=256)
    adapter_path: str | None = Field(default=None, max_length=4096)
    device: Literal["auto", "cpu", "cuda", "rocm", "mps", "xpu"] = "auto"
    memory_mode: Literal["auto", "full", "layer_streaming", "disk_streaming"] = "auto"
    precision: Literal["auto", "fp32", "fp16", "bf16"] = "auto"

    @model_validator(mode="after")
    def validate_messages_and_stop(self) -> "OpenAIChatCompletionRequest":
        combined = sum(len(message.content) for message in self.messages)
        if combined > 12000:
            raise ValueError("Combined chat message content must not exceed 12000 characters.")
        if not any(message.role == "user" for message in self.messages):
            raise ValueError("At least one user message is required.")
        if isinstance(self.stop, list):
            if len(self.stop) > 16 or any(not item or len(item) > 256 for item in self.stop):
                raise ValueError("stop must contain at most 16 non-empty strings of 256 characters or fewer.")
        return self


def _stop_sequences(request: OpenAIChatCompletionRequest) -> list[str]:
    if request.stop is None:
        return []
    return [request.stop] if isinstance(request.stop, str) else request.stop


def _generation_args(request: OpenAIChatCompletionRequest, model: dict[str, Any]) -> dict[str, Any]:
    return {
        "model_path": model["path"],
        "prompt": next(message.content for message in reversed(request.messages) if message.role == "user"),
        "adapter_path": request.adapter_path,
        "max_new_tokens": request.max_completion_tokens or request.max_tokens or 256,
        "temperature": request.temperature,
        "top_p": request.top_p,
        "top_k": request.top_k,
        "repetition_penalty": request.repetition_penalty,
        "seed": request.seed,
        "stop_sequences": _stop_sequences(request),
        "device_preference": request.device,
        "memory_mode": request.memory_mode,
        "precision": request.precision,
        "chat_messages": [message.model_dump() for message in request.messages],
    }


def _finish_reason(stop_reason: str) -> str:
    if stop_reason == "max_new_tokens":
        return "length"
    return "stop"


def _produce_stream(iterator: Iterator[dict[str, Any]], output: Queue, cancelled: Event) -> None:
    try:
        for item in iterator:
            while not cancelled.is_set():
                try:
                    output.put(item, timeout=0.1)
                    break
                except Full:
                    continue
            else:
                break
    except (ValueError, AxiomEngineError) as exc:
        while not cancelled.is_set():
            try:
                output.put({"type": "error", "message": str(exc)}, timeout=0.1)
                break
            except Full:
                continue
    except Exception:
        while not cancelled.is_set():
            try:
                output.put({"type": "error", "message": "AXIOM Native Engine failed during chat completion."}, timeout=0.1)
                break
            except Full:
                continue
    finally:
        close = getattr(iterator, "close", None)
        if callable(close):
            try:
                close()
            except (RuntimeError, ValueError):
                pass
        while not cancelled.is_set():
            try:
                output.put(_STREAM_END, timeout=0.1)
                break
            except Full:
                continue


@router.get("/v1/models")
def openai_list_models(request: Request) -> Any:
    """List native models as OpenAI-compatible model objects."""
    auth_error = _authorization_error(request)
    if auth_error is not None:
        return auth_error
    created = int(time.time())
    models = _native_models()
    return {
        "object": "list",
        "data": [
            {"id": model["name"], "object": "model", "created": created, "owned_by": "axiom"}
            for model in models
        ],
    }



def _run_nonstream(request: OpenAIChatCompletionRequest, model: dict[str, Any]) -> Any:
    try:
        final: dict[str, Any] | None = None
        for event in generate_local_stream(**_generation_args(request, model), include_token_events=False):
            if event.get("type") == "complete":
                final = event.get("result")
        if not isinstance(final, dict):
            return _openai_error("AXIOM Native Engine did not return a completion result.", 503, code="native_engine_error", error_type="server_error")
    except ValueError as exc:
        return _openai_error(str(exc), 422, code="invalid_request")
    except AxiomEngineError as exc:
        return _openai_error(str(exc), 503, code="native_engine_error", error_type="server_error")
    created = int(time.time())
    prompt_tokens = int(final.get("prompt_tokens", 0))
    completion_tokens = int(final.get("completion_tokens", 0))
    return {
        "id": "chatcmpl-" + uuid.uuid4().hex,
        "object": "chat.completion",
        "created": created,
        "model": request.model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": final.get("response", "")},
            "finish_reason": _finish_reason(str(final.get("stop_reason", "stop"))),
        }],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
        "system_fingerprint": "axiom-native",
    }


def _streaming_response(
    request: OpenAIChatCompletionRequest,
    model: dict[str, Any],
    http_request: Request,
) -> StreamingResponse:
    args = _generation_args(request, model)
    cancelled = Event()
    output: Queue = Queue(maxsize=_STREAM_QUEUE_SIZE)
    iterator = generate_local_stream(**args, include_token_events=True, cancel_event=cancelled)
    worker = Thread(target=_produce_stream, args=(iterator, output, cancelled), name="axiom-openai-chat-stream", daemon=True)
    stream_id = "chatcmpl-" + uuid.uuid4().hex
    created = int(time.time())

    async def events() -> AsyncIterator[str]:
        previous = ""
        completed = False
        yield "data: " + json.dumps({
            "id": stream_id, "object": "chat.completion.chunk", "created": created, "model": request.model,
            "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
        }, ensure_ascii=False) + "\n\n"
        worker.start()
        try:
            while True:
                if await http_request.is_disconnected():
                    cancelled.set()
                    return
                try:
                    item = await asyncio.to_thread(output.get, True, 0.1)
                except Empty:
                    continue
                if item is _STREAM_END:
                    break
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "error":
                    yield "data: " + json.dumps({
                        "error": {"message": item.get("message", "Native inference failed."), "type": "server_error", "code": "native_engine_error"}
                    }) + "\n\n"
                    yield "data: [DONE]\n\n"
                    return
                if item.get("type") == "token":
                    cumulative = str(item.get("response", ""))
                    delta = cumulative[len(previous):] if cumulative.startswith(previous) else cumulative
                    previous = cumulative
                    if delta:
                        yield "data: " + json.dumps({
                            "id": stream_id, "object": "chat.completion.chunk", "created": created, "model": request.model,
                            "choices": [{"index": 0, "delta": {"content": delta}, "finish_reason": None}],
                        }, ensure_ascii=False) + "\n\n"
                if item.get("type") == "complete":
                    result = item.get("result", {})
                    yield "data: " + json.dumps({
                        "id": stream_id, "object": "chat.completion.chunk", "created": created, "model": request.model,
                        "choices": [{"index": 0, "delta": {}, "finish_reason": _finish_reason(str(result.get("stop_reason", "stop")))}],
                    }, ensure_ascii=False) + "\n\n"
                    completed = True
                    break
            yield "data: [DONE]\n\n"
        finally:
            cancelled.set()
    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/v1/chat/completions")
async def openai_chat_completions(request: OpenAIChatCompletionRequest, http_request: Request) -> Any:
    """Create OpenAI-compatible native chat completions, either JSON or SSE."""
    auth_error = _authorization_error(http_request)
    if auth_error is not None:
        return auth_error
    model = _resolve_model(request.model)
    if model is None:
        return _openai_error(f"Native model {request.model!r} was not found or its ID is ambiguous.", 404, code="model_not_found")
    if request.stream:
        return _streaming_response(request, model, http_request)
    return await asyncio.to_thread(_run_nonstream, request, model)
