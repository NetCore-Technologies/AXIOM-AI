"""Local inference API. Requests are served only through the loopback Ollama adapter."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from axiom.core.inference import (
    InferenceRuntimeError,
    run_local_inference,
    run_local_inference_benchmark,
    runtime_status,
    validate_model_name,
)

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
def inference_benchmark(request: BenchmarkRequest) -> dict[str, Any]:
    if request.iterations * request.concurrency > 10:
        raise HTTPException(
            status_code=422,
            detail="Benchmark iterations × concurrency may not exceed 10 measured requests.",
        )
    try:
        return run_local_inference_benchmark(
            request.model,
            request.prompt,
            num_predict=request.num_predict,
            temperature=request.temperature,
            warmup_runs=request.warmup_runs,
            iterations=request.iterations,
            concurrency=request.concurrency,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except InferenceRuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None


@router.post("/generate")
def inference_generate(request: GenerateRequest) -> dict[str, Any]:
    try:
        return run_local_inference(
            request.model,
            request.prompt,
            num_predict=request.num_predict,
            temperature=request.temperature,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except InferenceRuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
