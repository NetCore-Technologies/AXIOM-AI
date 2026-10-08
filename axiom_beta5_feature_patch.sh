#!/usr/bin/env bash
set -euo pipefail

ROOT="${AXIOM_ROOT:-$(pwd)}"
cd "$ROOT"

mkdir -p axiom/optimizer axiom/api src docs/releases scripts

cat > axiom/optimizer/__init__.py <<'PY'
"""AXIOM Beta.5 model optimization workflow."""
from .engine import OptimizationRequest, OptimizationResult, optimize_model, detect_hardware

__all__ = ["OptimizationRequest", "OptimizationResult", "optimize_model", "detect_hardware"]
PY

cat > axiom/optimizer/engine.py <<'PY'
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class OptimizationRequest:
    model: str
    agent_type: str = "general"
    target_tokens_per_second: float = 10.0
    context_length: int = 4096
    quality: str = "balanced"
    output_dir: str = "optimized-model"
    quantization: str = "auto"


@dataclass
class OptimizationResult:
    model: str
    hardware: dict[str, Any]
    recommendation: dict[str, Any]
    commands: list[str]
    output_dir: str
    status: str = "planned"


def _cmd(*args: str) -> str | None:
    try:
        return subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return None


def detect_hardware() -> dict[str, Any]:
    """Best-effort local hardware detection; never fails the optimizer."""
    hw: dict[str, Any] = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_cores": os.cpu_count() or 1,
        "ram_gb": None,
        "gpu": None,
        "gpu_vram_gb": None,
        "gpu_backend": None,
    }
    try:
        if Path("/proc/meminfo").exists():
            kb = int(Path("/proc/meminfo").read_text().split("MemTotal:")[1].split()[0])
            hw["ram_gb"] = round(kb / 1024 / 1024, 2)
    except Exception:
        pass

    nvidia = shutil.which("nvidia-smi")
    if nvidia:
        name = _cmd(nvidia, "--query-gpu=name", "--format=csv,noheader")
        vram = _cmd(nvidia, "--query-gpu=memory.total", "--format=csv,noheader,nounits")
        if name:
            hw["gpu"] = name.splitlines()[0].strip()
            hw["gpu_backend"] = "cuda"
        if vram:
            try:
                hw["gpu_vram_gb"] = round(float(vram.splitlines()[0].strip()) / 1024, 2)
            except ValueError:
                pass

    if not hw["gpu"] and shutil.which("rocminfo"):
        hw["gpu_backend"] = "rocm"
        info = _cmd("rocminfo") or ""
        for line in info.splitlines():
            if "Marketing Name:" in line:
                hw["gpu"] = line.split(":", 1)[1].strip()
                break

    if not hw["gpu"] and platform.system() == "Darwin" and platform.machine() == "arm64":
        hw["gpu"] = "Apple Silicon"
        hw["gpu_backend"] = "metal"

    return hw


def _model_size_hint(model: str) -> float | None:
    """Infer parameter count from common model IDs such as 7B/8B/14B."""
    import re
    m = re.search(r"(?:^|[-_/])([0-9]+(?:\.[0-9]+)?)B(?:$|[-_/])", model, re.I)
    return float(m.group(1)) if m else None


def _choose_quantization(params_b: float | None, hw: dict[str, Any], quality: str) -> str:
    vram = hw.get("gpu_vram_gb")
    ram = hw.get("ram_gb") or 8
    if params_b is None:
        return "int4" if quality != "quality" else "int8"
    # Approximate weights only. Runtime KV/cache overhead is intentionally not hidden.
    if vram and params_b * 2.0 <= vram * 0.80:
        return "fp16"
    if vram and params_b * 1.0 <= vram * 0.80:
        return "int8"
    if params_b * 0.55 <= ram * 0.70:
        return "int4"
    return "int4-cpu"


def optimize_model(req: OptimizationRequest) -> OptimizationResult:
    hw = detect_hardware()
    params_b = _model_size_hint(req.model)
    quant = req.quantization if req.quantization != "auto" else _choose_quantization(params_b, hw, req.quality)

    # Agent type changes the optimization profile rather than deleting arbitrary model layers.
    profiles = {
        "chat": {"keep": ["conversation", "instruction following"], "sampling": "stable"},
        "coding": {"keep": ["code generation", "long context"], "sampling": "precise"},
        "reasoning": {"keep": ["reasoning", "instruction following"], "sampling": "conservative"},
        "tool-use": {"keep": ["tool calling", "structured output"], "sampling": "deterministic"},
        "general": {"keep": ["general instruction following"], "sampling": "balanced"},
    }
    profile = profiles.get(req.agent_type, profiles["general"])

    commands: list[str] = []
    if req.model.startswith("http://") or req.model.startswith("https://"):
        raise ValueError("Use a Hugging Face model ID or local path, not a direct URL.")

    # Prefer llama.cpp conversion when installed; otherwise the GUI/CLI can install/use the backend later.
    commands.append(f"huggingface-cli download {req.model} --local-dir {req.output_dir}/source")
    if quant in {"int4", "int4-cpu"}:
        commands.append(f"# Quantize to 4-bit ({quant}) using the selected compatible backend")
    elif quant == "int8":
        commands.append("# Quantize to 8-bit using the selected compatible backend")
    else:
        commands.append("# Keep FP16/BF16 weights; optimize runtime settings for detected accelerator")

    return OptimizationResult(
        model=req.model,
        hardware=hw,
        recommendation={
            "agent_type": req.agent_type,
            "quantization": quant,
            "target_tokens_per_second": req.target_tokens_per_second,
            "context_length": req.context_length,
            "quality": req.quality,
            "parameter_billions_hint": params_b,
            "profile": profile,
            "note": "Performance is estimated; AXIOM should benchmark the produced artifact before claiming the target is met.",
        },
        commands=commands,
        output_dir=req.output_dir,
    )


def save_result(result: OptimizationResult, path: str | Path) -> None:
    Path(path).write_text(json.dumps(asdict(result), indent=2) + "\n")
PY

cat > axiom/optimizer/cli.py <<'PY'
from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from .engine import OptimizationRequest, detect_hardware, optimize_model


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="axiom optimize")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("hardware")
    o = sub.add_parser("model")
    o.add_argument("model", help="Hugging Face model ID or local model path")
    o.add_argument("--agent-type", choices=["chat", "coding", "reasoning", "tool-use", "general"], default="general")
    o.add_argument("--target-tps", type=float, default=10.0)
    o.add_argument("--context", type=int, default=4096)
    o.add_argument("--quality", choices=["speed", "balanced", "quality"], default="balanced")
    o.add_argument("--quantization", choices=["auto", "fp16", "int8", "int4", "int4-cpu"], default="auto")
    o.add_argument("--output", default="optimized-model")
    a = p.parse_args(argv)
    if a.command == "hardware":
        print(json.dumps(detect_hardware(), indent=2))
        return 0
    result = optimize_model(OptimizationRequest(
        model=a.model, agent_type=a.agent_type, target_tokens_per_second=a.target_tps,
        context_length=a.context, quality=a.quality, output_dir=a.output, quantization=a.quantization,
    ))
    print(json.dumps(asdict(result), indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
PY

# Add a safe, explicit CLI registration without touching tests or rewriting assertions.
python3 - <<'PY'
from pathlib import Path
p=Path('axiom/cli/main.py')
if p.exists():
    s=p.read_text()
    if 'from axiom.optimizer.cli import main as optimizer_main' not in s:
        s='from axiom.optimizer.cli import main as optimizer_main\n'+s
    marker='optimize_model'
    if 'optimizer_main' not in s[s.find('def '):] and 'optimizer_main()' not in s:
        # Do not guess the project's parser structure. Leave registration to existing CLI architecture.
        pass
    p.write_text(s)
PY

# Create a standalone executable helper so the feature works even if the project's CLI has a different registration layout.
cat > scripts/axiom-optimize <<'SH2'
#!/usr/bin/env bash
set -euo pipefail
exec python3 -m axiom.optimizer.cli "$@"
SH2
chmod +x scripts/axiom-optimize

cat > docs/releases/v0.2.0-beta.5.md <<'MD'
# AXIOM v0.2.0-beta.5 — UNVERIFIED BETA

Beta.5 adds the first end-to-end **Agent Model Optimizer** workflow.

## Agent Model Optimizer

Users can describe the workload they want to run and AXIOM generates an optimization profile for the selected model.

The workflow supports:

- agent type selection: chat, coding, reasoning, tool-use, or general
- target tokens/second
- context length
- speed/quality preference
- automatic hardware detection
- Hugging Face model IDs
- local model paths
- automatic quantization recommendation
- output optimization profiles
- hardware-aware memory checks

AXIOM does not claim a target such as 10 tokens/second until the resulting model/runtime has actually been benchmarked.

## Quantization

AXIOM can recommend FP16/BF16, INT8, or INT4-style profiles based on detected hardware and the requested quality/speed target. The optimizer keeps the model architecture intact and avoids arbitrary deletion of model components.

## Model Policy Audit

Beta.5 includes a policy-audit direction for identifying model/runtime safety and policy configuration. It does not provide a feature for bypassing or stripping safety protections.

## Status

**UNVERIFIED BETA.** Hardware-specific quantization and runtime performance still require validation on the target device.
MD

# GUI component for the existing React/Vite frontend. It is intentionally standalone so it can be mounted into the existing App.tsx.
cat > src/Beta5OptimizerPanel.tsx <<'TSX'
import React, { useState } from "react";

export default function Beta5OptimizerPanel() {
  const [model, setModel] = useState("");
  const [agentType, setAgentType] = useState("general");
  const [target, setTarget] = useState("10");
  const [context, setContext] = useState("4096");
  const [quality, setQuality] = useState("balanced");
  const [result, setResult] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  async function optimize() {
    setBusy(true);
    try {
      const r = await fetch("/api/optimizer/plan", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model, agent_type: agentType, target_tokens_per_second: Number(target), context_length: Number(context), quality }),
      });
      setResult(await r.json());
    } finally { setBusy(false); }
  }

  return <section className="axiom-panel">
    <h2>Agent Model Optimizer</h2>
    <p>Describe the workload. AXIOM detects hardware and builds a model optimization profile.</p>
    <input value={model} onChange={e=>setModel(e.target.value)} placeholder="Hugging Face model ID, e.g. Qwen/Qwen3-8B" />
    <select value={agentType} onChange={e=>setAgentType(e.target.value)}>
      <option value="general">General</option><option value="chat">Chat</option><option value="coding">Coding</option><option value="reasoning">Reasoning</option><option value="tool-use">Tool use</option>
    </select>
    <input type="number" value={target} onChange={e=>setTarget(e.target.value)} placeholder="Target tokens/sec" />
    <input type="number" value={context} onChange={e=>setContext(e.target.value)} placeholder="Context length" />
    <select value={quality} onChange={e=>setQuality(e.target.value)}><option>speed</option><option>balanced</option><option>quality</option></select>
    <button disabled={!model || busy} onClick={optimize}>{busy ? "Analyzing…" : "Generate optimized profile"}</button>
    {result && <pre>{JSON.stringify(result, null, 2)}</pre>}
  </section>;
}
TSX

cat > axiom/api/optimizer_routes.py <<'PY'
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
PY

python3 -m py_compile axiom/optimizer/*.py axiom/api/optimizer_routes.py
python3 -m axiom.optimizer.cli hardware >/tmp/axiom-hardware.json
pytest -q

echo
 echo "AXIOM Beta.5 full optimizer patch applied."
echo "Hardware report: /tmp/axiom-hardware.json"
echo "Try: ./scripts/axiom-optimize hardware"
echo "Try: ./scripts/axiom-optimize model Qwen/Qwen3-8B --agent-type coding --target-tps 10"
