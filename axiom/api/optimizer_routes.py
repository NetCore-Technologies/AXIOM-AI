from __future__ import annotations

from dataclasses import asdict
from typing import Any

from axiom.optimizer.engine import OptimizationRequest, detect_hardware, optimize_model


def register_optimizer_routes(app: Any) -> None:
    """Register routes on FastAPI/compatible app without imposing an API framework dependency."""
    if hasattr(app, "get"):
        @app.get("/api/optimizer/hardware")
        def optimizer_hardware():
            return detect_hardware()

    if hasattr(app, "post"):
        @app.post("/api/optimizer/plan")
        def optimizer_plan(payload: dict):
            result = optimize_model(OptimizationRequest(
                model=payload["model"],
                agent_type=payload.get("agent_type", "general"),
                target_tokens_per_second=float(payload.get("target_tokens_per_second", 10)),
                context_length=int(payload.get("context_length", 4096)),
                quality=payload.get("quality", "balanced"),
                output_dir=payload.get("output_dir", "optimized-model"),
                quantization=payload.get("quantization", "auto"),
            ))
            return asdict(result)
