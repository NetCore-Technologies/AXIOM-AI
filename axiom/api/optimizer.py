from __future__ import annotations

from axiom.optimizer.agent_optimizer import build_plan, policy_audit


def register_optimizer_routes(app):
    try:
        from fastapi import HTTPException
    except ImportError:
        return

    @app.post("/api/v1/optimizer/plan")
    def optimizer_plan(payload: dict):
        if not payload.get("agent_type"):
            raise HTTPException(status_code=400, detail="agent_type is required")
        return build_plan(
            agent_type=payload["agent_type"],
            target_tokens_per_second=float(payload.get("target_tokens_per_second", 10)),
            model_id=payload.get("model_id"),
            model_size_b=float(payload["model_size_b"]) if payload.get("model_size_b") else None,
            context_length=int(payload.get("context_length", 2048)),
        ).to_dict()

    @app.post("/api/v1/optimizer/policy-audit")
    def optimizer_policy_audit(payload: dict):
        return policy_audit(payload.get("model_path"))
