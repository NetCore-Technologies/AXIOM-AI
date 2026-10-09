from __future__ import annotations

import os
from typing import Any

from axiom.api.server_optimizer_routes import register_optimizer_routes
from axiom.api.workspace import router as workspace_router
from axiom.version import __version__


def create_app() -> Any:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel

    from axiom.api.optimization import plan_optimization
    from axiom.api.policy_audit import audit_model

    app = FastAPI(title="AXIOM API", version=__version__)
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
    )

    register_optimizer_routes(app)
    app.include_router(workspace_router)

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

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

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

    return app
