"""Local inference API. Requests are served only through the loopback Ollama adapter."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from time import perf_counter
from typing import Any

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field, field_validator

from axiom.core.inference import (
    InferenceRuntimeError,
    run_local_inference,
    run_local_inference_benchmark,
    runtime_status,
    validate_model_name,
)
from axiom.core.runtime_traces import record_runtime_trace

router = APIRouter(prefix="/api/inference", tags=["local-inference"])


class GenerateRequest(BaseModel):
    model: str = Field(min_length=1, max_length=120)
    prompt: str = Field(min_length=1, max_length=12_000)
    num_predict: int = Field(default=256, ge=1, le=2_048)
    temperature: float = Field(default=0.7, ge=0, le=2)

    @field_validator("model")
    @classmethod
    def model_must_be_a_name_not_a_url(cls, value: str) -> str:
        return validate_model_name(value)

    @field_validator("prompt")
    @classmethod
    def prompt_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Prompt must contain at least one non-whitespace character.")
        return value


class BenchmarkRequest(BaseModel):
    model: str = Field(min_length=1, max_length=120)
    prompt: str = Field(min_length=1, max_length=12_000)
    num_predict: int = Field(default=128, ge=1, le=512)
    temperature: float = Field(default=0.2, ge=0, le=2)
    warmup_runs: int = Field(default=1, ge=0, le=2)
    iterations: int = Field(default=3, ge=1, le=10)
    concurrency: int = Field(default=1, ge=1, le=4)

    @field_validator("model")
    @classmethod
    def model_must_be_a_name_not_a_url(cls, value: str) -> str:
        return validate_model_name(value)

    @field_validator("prompt")
    @classmethod
    def prompt_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Prompt must contain at least one non-whitespace character.")
        return value

@router.get("/status")
def inference_status() -> dict[str, Any]:
    return runtime_status()


@router.post("/benchmark")
def inference_benchmark(request: BenchmarkRequest, response: Response) -> dict[str, Any]:
    request_id = uuid.uuid4().hex
    response.headers["X-Request-ID"] = request_id
    started_at = datetime.now(UTC).isoformat()
    started = perf_counter()
    if request.iterations * request.concurrency > 10:
        record_runtime_trace(
            request_id=request_id, operation="inference.benchmark", model=request.model,
            status="error", started_at=started_at, duration_ms=(perf_counter() - started) * 1000.0,
            prompt_characters=len(request.prompt), requested_output_tokens=request.num_predict,
            temperature=request.temperature, warmup_runs=request.warmup_runs,
            iterations=request.iterations, concurrency=request.concurrency,
            error_code="request_limit_exceeded",
        )
        raise HTTPException(
            status_code=422,
            detail="Benchmark iterations × concurrency may not exceed 10 measured requests.",
        )
    try:
        result = run_local_inference_benchmark(
            request.model,
            request.prompt,
            num_predict=request.num_predict,
            temperature=request.temperature,
            warmup_runs=request.warmup_runs,
            iterations=request.iterations,
            concurrency=request.concurrency,
        )
        measurements = result.get("measurements", {})
        configuration = result.get("configuration", {})
        record_runtime_trace(
            request_id=request_id,
            operation="inference.benchmark",
            model=request.model,
            status="success",
            started_at=started_at,
            duration_ms=(perf_counter() - started) * 1000.0,
            prompt_characters=len(request.prompt),
            requested_output_tokens=request.num_predict,
            temperature=request.temperature,
            warmup_runs=request.warmup_runs,
            iterations=request.iterations,
            concurrency=request.concurrency,
            measured_requests=configuration.get("measured_requests"),
            prompt_tokens=None,
            completion_tokens=measurements.get("total_completion_tokens"),
            completion_tokens_known=measurements.get("completion_tokens_known"),
            completion_tokens_per_second=measurements.get("completion_tokens_per_second"),
        )
        return {**result, "request_id": request_id}
    except ValueError as exc:
        record_runtime_trace(
            request_id=request_id, operation="inference.benchmark", model=request.model,
            status="error", started_at=started_at, duration_ms=(perf_counter() - started) * 1000.0,
            prompt_characters=len(request.prompt), requested_output_tokens=request.num_predict,
            temperature=request.temperature, warmup_runs=request.warmup_runs,
            iterations=request.iterations, concurrency=request.concurrency,
            error_code="invalid_benchmark_configuration",
        )
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except InferenceRuntimeError:
        record_runtime_trace(
            request_id=request_id, operation="inference.benchmark", model=request.model,
            status="error", started_at=started_at, duration_ms=(perf_counter() - started) * 1000.0,
            prompt_characters=len(request.prompt), requested_output_tokens=request.num_predict,
            temperature=request.temperature, warmup_runs=request.warmup_runs,
            iterations=request.iterations, concurrency=request.concurrency,
            error_code="runtime_unavailable",
        )
        raise HTTPException(status_code=503, detail="Local inference benchmark failed because the runtime did not complete the request.") from None


@router.post("/generate")
def inference_generate(request: GenerateRequest, response: Response) -> dict[str, Any]:
    request_id = uuid.uuid4().hex
    response.headers["X-Request-ID"] = request_id
    started_at = datetime.now(UTC).isoformat()
    started = perf_counter()
    try:
        result = run_local_inference(
            request.model,
            request.prompt,
            num_predict=request.num_predict,
            temperature=request.temperature,
        )
        record_runtime_trace(
            request_id=request_id, operation="inference.generate", model=request.model,
            status="success", started_at=started_at, duration_ms=(perf_counter() - started) * 1000.0,
            prompt_characters=len(request.prompt), requested_output_tokens=request.num_predict,
            temperature=request.temperature, prompt_tokens=result.get("prompt_eval_count"),
            completion_tokens=result.get("eval_count"),
        )
        return {**result, "request_id": request_id}
    except ValueError:
        record_runtime_trace(
            request_id=request_id, operation="inference.generate", model=request.model,
            status="error", started_at=started_at, duration_ms=(perf_counter() - started) * 1000.0,
            prompt_characters=len(request.prompt), requested_output_tokens=request.num_predict,
            temperature=request.temperature, error_code="invalid_generation_request",
        )
        raise HTTPException(status_code=422, detail="Local inference request could not be validated.") from None
    except InferenceRuntimeError:
        record_runtime_trace(
            request_id=request_id, operation="inference.generate", model=request.model,
            status="error", started_at=started_at, duration_ms=(perf_counter() - started) * 1000.0,
            prompt_characters=len(request.prompt), requested_output_tokens=request.num_predict,
            temperature=request.temperature, error_code="runtime_unavailable",
        )
        raise HTTPException(status_code=503, detail="Local inference runtime did not complete the request.") from None
