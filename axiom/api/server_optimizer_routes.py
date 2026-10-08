from __future__ import annotations

from typing import Any


def register_optimizer_routes(app: Any) -> None:
    from pydantic import BaseModel

    from axiom.api.optimizer import build_plan, optimizer_profiles

    class OptimizeRequest(BaseModel):
        model: str
        profile: int
        target_tokens_per_second: float = 10.0

    @app.get("/api/optimizer/profiles")
    def profiles():
        return {"profiles": optimizer_profiles()}

    @app.post("/api/optimizer/plan")
    def plan(req: OptimizeRequest):
        return build_plan(
            model=req.model,
            profile=req.profile,
            target_tps=req.target_tokens_per_second,
        )
