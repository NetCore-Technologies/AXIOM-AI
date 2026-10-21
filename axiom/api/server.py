from __future__ import annotations

import os
import logging
import re
import uuid
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from axiom.api.evaluation import router as evaluation_router
from axiom.api.model_studio import router as model_studio_router
from axiom.api.fine_tuning import router as fine_tuning_router
from axiom.api.diagnostics import router as diagnostics_router
from axiom.api.runtime_discovery import router as runtime_discovery_router
from axiom.api.agent_profiles import router as agent_profiles_router
from axiom.api.inference import router as inference_router
from axiom.api.server_optimizer_routes import register_optimizer_routes
from axiom.api.security import router as security_router
from axiom.api.workspace import router as workspace_router
from axiom.api.workflows import router as workflows_router
from axiom.version import __version__

_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_logger = logging.getLogger(__name__)
API_CONTRACT_VERSION = 1


class OptimizeRequest(BaseModel):
    model: str
    agent_type: str = "general-agent"
    use_case: str = "assistant"
    privacy: str = "local"
    latency: str = "low"
    target_tokens_per_second: float = 10.0
    sequence_length: int = 2048
    quantization: str = "auto"


class AuditRequest(BaseModel):
    model_path: str


def create_app() -> Any:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.exceptions import RequestValidationError
    from fastapi.middleware.cors import CORSMiddleware
    from starlette.responses import JSONResponse

    from axiom.api.optimization import plan_optimization
    from axiom.api.policy_audit import audit_model

    app = FastAPI(
        title="AXIOM API",
        version=__version__,
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            origin.strip()
            for origin in os.environ.get(
                "AXIOM_CORS_ORIGINS",
                "http://localhost:4173,http://127.0.0.1:4173,http://localhost:5173,http://127.0.0.1:5173",
            ).split(",")
            if origin.strip()
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next: Any) -> Any:
        supplied = request.headers.get("X-Request-ID", "")
        request_id = supplied if _REQUEST_ID.fullmatch(supplied) else uuid.uuid4().hex
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    def error_response(
        request: Request,
        code: str,
        message: str,
        detail: Any,
        status: int,
        headers: dict[str, str] | None = None,
    ) -> Any:
        request_id = getattr(request.state, "request_id", uuid.uuid4().hex)
        return JSONResponse(
            status_code=status,
            content={
                "error": {"code": code, "message": message, "request_id": request_id},
                "detail": detail,
                "request_id": request_id,
            },
            headers={**(headers or {}), "X-Request-ID": request_id},
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> Any:
        message = exc.detail if isinstance(exc.detail, str) else "Request rejected"
        return error_response(request, "http_error", message, exc.detail, exc.status_code, exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> Any:
        details = [
            {
                "loc": item.get("loc", []),
                "msg": item.get("msg", "Invalid value"),
                "type": item.get("type", "value_error"),
            }
            for item in exc.errors()
        ]
        return error_response(
            request,
            "validation_error",
            "Request validation failed",
            details,
            422,
        )

    @app.exception_handler(Exception)
    async def internal_error(request: Request, exc: Exception) -> Any:
        request_id = getattr(request.state, "request_id", "unknown")
        _logger.error(
            "Unhandled AXIOM API error (request_id=%s)",
            request_id,
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        return error_response(
            request,
            "internal_error",
            "Internal server error",
            "Internal server error",
            500,
        )

    register_optimizer_routes(app)
    app.include_router(workspace_router)
    app.include_router(workflows_router)
    app.include_router(security_router)
    app.include_router(evaluation_router)
    app.include_router(model_studio_router)
    app.include_router(fine_tuning_router)
    app.include_router(diagnostics_router)
    app.include_router(runtime_discovery_router)
    app.include_router(agent_profiles_router)
    app.include_router(inference_router)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/api/meta")
    def api_metadata() -> dict[str, str | int]:
        return {
            "api_contract_version": API_CONTRACT_VERSION,
            "application_version": __version__,
            "openapi_url": "/api/openapi.json",
            "compatibility_policy": "Additive changes stay in v1; breaking changes require a parallel /api/v2 contract.",
        }

    @app.post("/api/models/optimize")
    def optimize(req: OptimizeRequest) -> dict[str, Any]:
        return plan_optimization(
            model=req.model,
            agent_type=req.agent_type,
            use_case=req.use_case,
            privacy=req.privacy,
            latency=req.latency,
            target_tokens_per_second=req.target_tokens_per_second,
            sequence_length=req.sequence_length,
            quantization=req.quantization,
        ).to_dict()

    @app.post("/api/models/policy-audit")
    def policy_audit(req: AuditRequest) -> dict[str, Any]:
        return audit_model(req.model_path)

    webui_dir = Path(__file__).resolve().parent.parent / "webui"
    if (webui_dir / "index.html").is_file():
        from fastapi.staticfiles import StaticFiles

        app.mount("/ui", StaticFiles(directory=webui_dir, html=True), name="ui")

    return app
