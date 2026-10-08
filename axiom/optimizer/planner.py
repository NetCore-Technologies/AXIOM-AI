from __future__ import annotations

def _quant(vram_mb, preference):
    if vram_mb is None:
        return "int4" if preference == "speed" else "int8"
    if vram_mb < 6000:
        return "int4"
    if vram_mb < 10000:
        return "int4" if preference != "quality" else "int8"
    if vram_mb < 16000:
        return "int8" if preference == "quality" else "int4"
    return "bf16" if preference == "quality" else "int8"

def build_plan(model, answers, hardware):
    q = _quant(hardware.get("vram_mb"), answers["preference"])
    return {
        "model": model,
        "agent_type": answers["agent_type"],
        "preference": answers["preference"],
        "target_tps": answers["target_tps"],
        "context": answers["context"],
        "hardware": hardware,
        "quantization": q,
        "status": "ready_for_benchmark",
        "note": "Target throughput must be verified by an actual device benchmark.",
    }
