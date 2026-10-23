"""HTTP API for AXIOM's direct local model engine."""
from __future__ import annotations

import asyncio
import json
import logging
from queue import Empty, Full, Queue
from threading import Event, Thread
from typing import Any, Iterator

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from starlette.responses import StreamingResponse

from axiom.core.engine import (
    AxiomEngineError,
    discover_local_engine_assets,
    generate_local,
    generate_local_stream,
    resolve_local_model_directory,
    runtime_status,
    unload_local_model,
)

router = APIRouter(prefix="/api/engine", tags=["axiom-engine"])


def _validated_path(value: Any, label: str) -> Any:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Path must be a string.")
    candidate = value.strip()
    if not candidate:
        raise ValueError("Path must not be blank.")
    # The core matches user input against filesystem-discovered directories
    # under explicitly configured trusted roots before returning a usable path.
    return resolve_local_model_directory(candidate, label)


class GenerateRequest(BaseModel):
    model_path: str = Field(min_length=1, max_length=4096)
    adapter_path: str | None = Field(default=None, max_length=4096)
    prompt: str = Field(min_length=1, max_length=12000)
    max_new_tokens: int = Field(default=256, ge=1, le=2048)
    temperature: float = Field(default=0.7, ge=0, le=2)

    @field_validator("model_path", mode="before")
    @classmethod
    def base_model_path_must_be_trusted(cls, value: Any) -> Any:
        return _validated_path(value, "Base model")

    @field_validator("adapter_path", mode="before")
    @classmethod
    def adapter_path_must_be_trusted(cls, value: Any) -> Any:
        return _validated_path(value, "LoRA adapter")

    @field_validator("prompt")
    @classmethod
    def prompt_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Prompt must contain at least one non-whitespace character.")
        return value


@router.get("/models")
def engine_models() -> dict[str, Any]:
    """List metadata-only native-compatible models and LoRA adapters under trusted roots."""
    return discover_local_engine_assets()


@router.get("/status")
def engine_status() -> dict[str, Any]:
    return runtime_status()


@router.post("/unload")
def engine_unload() -> dict[str, Any]:
    """Release AXIOM's currently loaded local model and its cache references."""
    return unload_local_model()


@router.post("/generate")
def engine_generate(request: GenerateRequest) -> dict[str, Any]:
    try:
        return generate_local(
            request.model_path,
            request.prompt,
            adapter_path=request.adapter_path,
            max_new_tokens=request.max_new_tokens,
            temperature=request.temperature,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except AxiomEngineError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None


_STREAM_END = object()
_STREAM_QUEUE_SIZE = 2
_LOG = logging.getLogger(__name__)


def _enqueue_stream_item(output: Queue, item: object, cancel_event: Event) -> bool:
    while not cancel_event.is_set():
        try:
            output.put(item, timeout=0.1)
            return True
        except Full:
            continue
    return False


def _produce_native_stream(
    iterator: Iterator[dict[str, Any]],
    output: Queue,
    cancel_event: Event,
) -> None:
    """Advance a model stream on one dedicated thread and apply backpressure."""
    try:
        for event in iterator:
            if not _enqueue_stream_item(output, event, cancel_event):
                break
    except ValueError as exc:
        _enqueue_stream_item(output, {
            "type": "error",
            "code": "invalid_request",
            "message": str(exc),
        }, cancel_event)
    except AxiomEngineError as exc:
        _enqueue_stream_item(output, {
            "type": "error",
            "code": "native_engine_error",
            "message": str(exc),
        }, cancel_event)
    except Exception:
        _LOG.exception("Unexpected failure in AXIOM Native Engine stream producer.")
        _enqueue_stream_item(output, {
            "type": "error",
            "code": "native_engine_error",
            "message": "AXIOM Native Engine stream failed unexpectedly.",
        }, cancel_event)
    finally:
        close = getattr(iterator, "close", None)
        if callable(close):
            try:
                close()
            except (RuntimeError, ValueError):
                _LOG.debug("Native stream iterator cleanup was already in progress.")
        # Do not block a disconnecting client on a full buffer. The consumer
        # exits as soon as it observes the shared cancellation event.
        try:
            output.put_nowait(_STREAM_END)
        except Full:
            pass


@router.post("/generate/stream")
async def engine_generate_stream(
    request: GenerateRequest,
    http_request: Request,
) -> StreamingResponse:
    """Stream native token snapshots while detecting disconnects cooperatively."""
    cancel_event = Event()
    output: Queue = Queue(maxsize=_STREAM_QUEUE_SIZE)
    iterator = generate_local_stream(
        request.model_path,
        request.prompt,
        adapter_path=request.adapter_path,
        max_new_tokens=request.max_new_tokens,
        temperature=request.temperature,
        cancel_event=cancel_event,
    )
    producer = Thread(
        target=_produce_native_stream,
        args=(iterator, output, cancel_event),
        name="axiom-native-inference-stream",
        daemon=True,
    )

    async def events() -> Iterator[str]:
        async def watch_disconnect() -> None:
            while not cancel_event.is_set():
                if await http_request.is_disconnected():
                    cancel_event.set()
                    return
                await asyncio.sleep(0.1)

        monitor = asyncio.create_task(watch_disconnect())
        producer.start()
        try:
            while True:
                item = await asyncio.to_thread(output.get)
                if item is _STREAM_END:
                    break
                if cancel_event.is_set():
                    break
                yield json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\\n"
        finally:
            cancel_event.set()
            monitor.cancel()
            try:
                await monitor
            except asyncio.CancelledError:
                pass
            # The model checks cancellation between transformer layers/tokens.
            # Never wait indefinitely for a slow device kernel during disconnect.
            await asyncio.to_thread(producer.join, 2.0)

    return StreamingResponse(
        events(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )
