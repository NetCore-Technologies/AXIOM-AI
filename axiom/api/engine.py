"""HTTP API for AXIOM's direct local model engine."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from axiom.core.engine import AxiomEngineError, generate_local, resolve_local_model_directory, runtime_status, unload_local_model

router = APIRouter(prefix="/api/engine", tags=["axiom-engine"])


class GenerateRequest(BaseModel):
    model_path: str = Field(min_length=1, max_length=4096)
    adapter_path: str | None = Field(default=None, max_length=4096)
    prompt: str = Field(min_length=1, max_length=12000)
    max_new_tokens: int = Field(default=256, ge=1, le=2048)
    temperature: float = Field(default=0.7, ge=0, le=2)

    @field_validator("model_path", "adapter_path", mode="before")
    @classmethod
    def paths_must_resolve_inside_allowed_model_roots(cls, value: Any) -> Any:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("Path must be a string.")
        candidate = value.strip()
        if not candidate:
            raise ValueError("Path must not be blank.")
        # The shared resolver validates absolute and relative inputs against
        # configured trusted roots and rejects symlink escapes.
        return resolve_local_model_directory(candidate, "Model/adapter directory")

    @field_validator("prompt")
    @classmethod
    def prompt_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Prompt must contain at least one non-whitespace character.")
        return value


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
