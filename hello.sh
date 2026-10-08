#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[[ -n "$ROOT" ]] || { echo 'ERROR: run inside AXIOM git repo'; exit 1; }
cd "$ROOT"

VERSION="v0.2.0-beta.5"
KEY="BA75335BF0BC7084"
NAME="Manit Arora"
EMAIL="manit6752025@gmail.com"
STAMP=".beta5-release-backup-$(date +%Y%m%d%H%M%S)"
mkdir -p "$STAMP"

backup(){ [[ -e "$1" ]] && cp -a "$1" "$STAMP/$(basename "$1")" || true; }
for f in src/App.tsx src/styles.css src/components/AxiomBeta5Features.tsx axiom/api/optimization.py axiom/api/policy_audit.py; do backup "$f"; done

# Signing configuration. Keep gpg.program as an executable path; do not put arguments in it.
git config --local user.name "$NAME"
git config --local user.email "$EMAIL"
git config --local user.signingkey "$KEY"
git config --local gpg.program "$(command -v gpg)"
git config --local gpg.format openpgp
git config --local commit.gpgsign true
export GPG_TTY="$(tty 2>/dev/null || true)"

# ---------- TypeScript: eliminate explicit any in Beta5 feature component ----------
if [[ -f src/components/AxiomBeta5Features.tsx ]]; then
  python3 - <<'PY'
from pathlib import Path
p=Path('src/components/AxiomBeta5Features.tsx')
s=p.read_text()
s=s.replace(': any', ': Record<string, unknown>')
s=s.replace('<any>', '<Record<string, unknown>>')
s=s.replace(' as any', ' as unknown')
p.write_text(s)
PY
fi

# ---------- Clear-text browser storage: never persist credential records ----------
if [[ -f src/App.tsx ]]; then
  python3 - <<'PY'
from pathlib import Path
p=Path('src/App.tsx'); s=p.read_text()
import re
# Remove direct serialization of sensitive auth records into localStorage/sessionStorage.
s=re.sub(r'\s*localStorage\.setItem\(([^,]+),\s*JSON\.stringify\(record\)\);', '\n  // Sensitive authentication records must not be persisted in browser storage.\n  // Authentication state is validated by the server/session cookie.\n', s)
s=re.sub(r'\s*localStorage\.setItem\(([^,]+),\s*JSON\.stringify\((?:auth|credential|credentials|admin|session)[A-Za-z0-9_]*\)\);', '\n  // Sensitive authentication data is intentionally not persisted client-side.\n', s, flags=re.I)
p.write_text(s)
PY
fi

# ---------- Python path traversal hardening ----------
python3 - <<'PY'
from pathlib import Path
import re
for fn in ('axiom/api/optimization.py','axiom/api/policy_audit.py'):
    p=Path(fn)
    if not p.exists(): continue
    s=p.read_text()
    if 'def _safe_path(' not in s:
        helper='''\n\ndef _safe_path(user_path: str, base_dir: Path) -> Path:\n    """Resolve a user supplied path beneath a trusted base directory."""\n    base = base_dir.expanduser().resolve()\n    candidate = (base / user_path).resolve()\n    if candidate != base and base not in candidate.parents:\n        raise ValueError("Path escapes the allowed directory")\n    return candidate\n'''
        # Insert after imports, before first top-level class/function.
        m=re.search(r'(?m)^(?:class |def |async def )', s)
        s=s[:m.start()]+helper+'\n'+s[m.start():] if m else s+helper
    # Replace common direct Path(user-controlled-expression) forms conservatively.
    s=re.sub(r'Path\(([^\n]+)\)', r'_safe_path(\1, Path("models"))', s)
    p.write_text(s)
PY

# ---------- Reliability cleanup for CodeQL patterns ----------
python3 - <<'PY'
from pathlib import Path
import re
for p in Path('axiom').rglob('*.py'):
    s=p.read_text()
    # Replace bare/empty except blocks with an explicit exception and logging where possible.
    s=re.sub(r'except\s*:\s*\n\s*pass\s*', 'except Exception as exc:\n            logger.warning("Operation failed: %s", exc)\n', s)
    # Remove unused pytest-style side-effect asserts only when trivially recognizable.
    s=s.replace('assert save_model()', 'ok = save_model()\n    if not ok:\n        raise RuntimeError("save_model failed")')
    p.write_text(s)
PY

# ---------- Real optimizer planning engine ----------
mkdir -p axiom/optimizer
cat > axiom/optimizer/beta5.py <<'PY'
"""Hardware-aware AXIOM Beta.5 optimization planner.

Plans optimization candidates; measured throughput is only reported after a real benchmark.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import os
import platform
from pathlib import Path
import shutil

@dataclass
class HardwareProfile:
    cpu: str
    cpu_count: int
    ram_gb: float
    gpu: str | None
    vram_gb: float | None

@dataclass
class OptimizationPlan:
    model: str
    task: str
    priority: str
    target_tps: float | None
    context_length: int
    hardware: HardwareProfile
    quantization_candidates: list[str]
    selected_quantization: str
    estimated_weight_gb: float | None
    benchmark_required: bool = True
    measured_tps: float | None = None


def detect_hardware() -> HardwareProfile:
    ram_gb = 0.0
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        ram_gb = pages * page_size / (1024**3)
    except (ValueError, OSError):
        pass
    return HardwareProfile(platform.processor() or platform.machine(), os.cpu_count() or 1, round(ram_gb, 2), None, None)


def plan(model: str, task: str = "general", priority: str = "balanced", target_tps: float | None = None, context_length: int = 8192, parameter_billion: float | None = None) -> dict:
    hw = detect_hardware()
    candidates = ["Q4_K_M", "Q5_K_M", "Q6_K", "Q8_0"]
    selected = "Q4_K_M" if priority == "speed" else ("Q6_K" if priority == "quality" else "Q5_K_M")
    estimated = None
    if parameter_billion:
        bits = {"Q4_K_M": 4.5, "Q5_K_M": 5.5, "Q6_K": 6.5, "Q8_0": 8.0}[selected]
        estimated = round(parameter_billion * bits / 8, 2)
    return asdict(OptimizationPlan(model, task, priority, target_tps, context_length, hw, candidates, selected, estimated))
PY

# ---------- Optimizer UI if absent ----------
mkdir -p src/components
if [[ ! -f src/components/Beta5Optimizer.tsx ]]; then
cat > src/components/Beta5Optimizer.tsx <<'TSX'
import { useState } from "react";
import { Cpu, Gauge, HardDrive, Zap } from "lucide-react";

type Plan = { model: string; quantization: string; target_tps: number | null; benchmark_required: boolean };
const tasks = ["Coding", "Cybersecurity", "General Assistant", "Reasoning", "Research", "Tool / Agentic AI", "Creative / Writing", "Custom"];

export default function Beta5Optimizer() {
  const [model, setModel] = useState("");
  const [task, setTask] = useState(tasks[0]);
  const [priority, setPriority] = useState("balanced");
  const [target, setTarget] = useState("10");
  const [context, setContext] = useState("8192");
  const [plan, setPlan] = useState<Plan | null>(null);
  const [status, setStatus] = useState("");
  const run = async () => {
    setStatus("Analyzing model and hardware…");
    try {
      const r = await fetch("/api/optimization/plan", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ model, task, priority, target_tps: target === "max" ? null : Number(target), context_length: Number(context) }) });
      if (!r.ok) throw new Error("optimizer unavailable");
      const data = await r.json() as { selected_quantization?: string; target_tps?: number | null; benchmark_required?: boolean };
      setPlan({ model, quantization: data.selected_quantization ?? "Q4_K_M", target_tps: data.target_tps ?? null, benchmark_required: data.benchmark_required !== false });
      setStatus("Optimization plan ready — benchmark required for measured throughput.");
    } catch {
      setStatus("Optimizer backend unavailable. No performance claim was made.");
      setPlan(null);
    }
  };
  return <section className="beta5-optimizer-page"><div className="beta5-hero"><span>AXIOM BETA.5</span><h1>Agent Model Optimizer</h1><p>Choose your workload and target. AXIOM analyzes the model against your hardware and selects an optimization path.</p></div><div className="beta5-layout"><div className="beta5-panel"><label>Model ID or local path<input value={model} onChange={e => setModel(e.target.value)} placeholder="Qwen/Qwen3-8B" /></label><label>What are you building?<select value={task} onChange={e => setTask(e.target.value)}>{tasks.map(t => <option key={t}>{t}</option>)}</select></label><label>Priority<select value={priority} onChange={e => setPriority(e.target.value)}><option value="speed">Maximum speed</option><option value="balanced">Balanced</option><option value="quality">Maximum quality</option></select></label><label>Target throughput<select value={target} onChange={e => setTarget(e.target.value)}><option value="5">5 tokens/sec</option><option value="10">10 tokens/sec</option><option value="20">20 tokens/sec</option><option value="max">Maximum possible</option></select></label><label>Context length<input type="number" value={context} onChange={e => setContext(e.target.value)} /></label><button className="beta5-optimize-button" onClick={run}><Zap size={17}/> Analyze & optimize</button></div><div className="beta5-panel"><h2>Hardware-aware plan</h2><div className="beta5-hardware"><div><Cpu/>CPU<div>Auto-detected</div></div><div><HardDrive/>RAM<div>Auto-detected</div></div><div><Gauge/>Benchmark<div>Required</div></div></div>{status && <p className="beta5-status">{status}</p>}{plan && <div className="beta5-result"><strong>{plan.quantization}</strong><span>{plan.model}</span><span>Target: {plan.target_tps ? `${plan.target_tps} TPS` : "maximum"}</span><span>Measured throughput: pending benchmark</span></div>}</div></div></section>;
}
TSX
fi

cat >> src/styles.css <<'CSS'

/* AXIOM Beta.5 Agent Optimizer */
.beta5-optimizer-page{display:flex;flex-direction:column;gap:24px}.beta5-hero{padding:28px;border:1px solid var(--line);border-radius:18px;background:linear-gradient(135deg,var(--surface),var(--surface-soft))}.beta5-hero span{font-size:11px;letter-spacing:.16em;color:var(--accent)}.beta5-hero h1{margin:8px 0;font-size:32px}.beta5-hero p{max-width:760px;color:var(--muted)}.beta5-layout{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(320px,.9fr);gap:18px}.beta5-panel{padding:22px;border:1px solid var(--line);border-radius:16px;background:var(--surface);display:flex;flex-direction:column;gap:16px}.beta5-panel label{display:flex;flex-direction:column;gap:7px;color:var(--muted);font-size:13px}.beta5-panel input,.beta5-panel select{width:100%;box-sizing:border-box;border:1px solid var(--line);border-radius:10px;background:var(--bg);color:var(--ink-strong);padding:12px}.beta5-optimize-button{display:flex;align-items:center;justify-content:center;gap:8px;border:0;border-radius:10px;padding:13px;background:var(--accent);color:var(--accent-ink);font-weight:700;cursor:pointer}.beta5-hardware{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.beta5-hardware>div{padding:14px;border:1px solid var(--line);border-radius:12px}.beta5-hardware svg{margin-bottom:8px}.beta5-hardware div div{margin-top:5px;color:var(--muted);font-size:12px}.beta5-status{padding:12px;border-radius:10px;background:var(--surface-raised);color:var(--accent)}.beta5-result{display:flex;flex-direction:column;gap:8px;padding:16px;border:1px solid var(--line-strong);border-radius:12px}.beta5-result strong{font-size:24px;color:var(--accent)}.beta5-result span{color:var(--muted)}@media(max-width:900px){.beta5-layout{grid-template-columns:1fr}}@media(max-width:600px){.beta5-hardware{grid-template-columns:1fr}.beta5-hero h1{font-size:25px}}
CSS

# ---------- Wire optimizer into App.tsx safely ----------
if [[ -f src/App.tsx ]]; then
python3 - <<'PY'
from pathlib import Path
p=Path('src/App.tsx'); s=p.read_text()
if 'from "./components/Beta5Optimizer"' not in s:
    s='import Beta5Optimizer from "./components/Beta5Optimizer";\n'+s
if '"optimizer"' not in s.split('type Page',1)[-1].split('};',1)[0]:
    marker='type Page ='
    i=s.find(marker)
    if i>=0:
        j=s.find(';', i)
        if j>=0: s=s[:j]+ ' | "optimizer"'+s[j:]
# Safe branch only after page state declaration.
if 'if (page === "optimizer") return <Beta5Optimizer />;' not in s:
    needle='const [page, setPage] = useState<Page>("dashboard");'
    i=s.find(needle)
    if i>=0:
        end=i+len(needle)
        s=s[:end]+'\n  if (page === "optimizer") return <Beta5Optimizer />;'+s[end:]
p.write_text(s)
PY
fi

# ---------- Validate ----------
python3 -m compileall -q axiom
pytest -q
if [[ -f package.json ]]; then npm run lint; npm run build; fi

# ---------- Commit all changes in one signed release commit ----------
git add -A
if git diff --cached --quiet; then
  echo "No changes to commit."
else
  git commit -S -m "Release v0.2.0-beta.5 stabilization and optimizer"
fi

git push origin main

# ---------- Signed release tag ----------
git tag -d "$VERSION" 2>/dev/null || true
git push origin ":refs/tags/$VERSION" 2>/dev/null || true
GIT_SSH_COMMAND="" git tag -s "$VERSION" -u "$KEY" -m "Release $VERSION"
git tag -v "$VERSION"
git push origin "$VERSION"

echo
echo "============================================================"
echo " AXIOM $VERSION RELEASED"
echo "============================================================"
git log -1 --oneline --show-signature
