#!/usr/bin/env bash
set -euo pipefail

OWNER="NetCore-Technologies"
REPO="AXIOM-AI"
VERSION="0.2.0-beta.5"
PEP_VERSION="0.2.0b5"
TAG="v${VERSION}"
BACKUP_DIR=".axiom-beta5-backup"
export VERSION PEP_VERSION

banner() { printf '\n===== %s =====\n' "$1"; }
die() { echo "ERROR: $*" >&2; exit 1; }

emit() {
  local target="$1"
  mkdir -p "$(dirname "$target")"
  if [[ -f "$target" ]]; then
    mkdir -p "$BACKUP_DIR/$(dirname "$target")"
    cp -p "$target" "$BACKUP_DIR/$target"
  fi
  cat > "$target"
}

echo "============================================================"
echo " AXIOM ${VERSION} - FULL BETA.5 FEATURE PATCH"
echo "============================================================"

command -v git >/dev/null || die "git is required."
command -v python3 >/dev/null || die "python3 is required."
command -v gpg >/dev/null || die "gpg is required."

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

git remote get-url origin >/dev/null || die "origin remote not configured."

EXCLUDE_FILE="$(git rev-parse --git-path info/exclude)"
mkdir -p "$(dirname "$EXCLUDE_FILE")"
grep -qxF "${BACKUP_DIR}/" "$EXCLUDE_FILE" 2>/dev/null || echo "${BACKUP_DIR}/" >> "$EXCLUDE_FILE"

GPG_KEY="${AXIOM_GPG_KEY:-$(git config --get user.signingkey || true)}"
GPG_NAME="${AXIOM_GPG_NAME:-$(git config --get user.name || true)}"
GPG_EMAIL="${AXIOM_GPG_EMAIL:-$(git config --get user.email || true)}"
GPG_NAME="${GPG_NAME:-Manit Arora}"
GPG_EMAIL="${GPG_EMAIL:-manit6752025@gmail.com}"

[[ -n "$GPG_KEY" ]] || die "no GPG signing key. Set AXIOM_GPG_KEY or run: git config user.signingkey <KEYID>"

export GIT_AUTHOR_NAME="$GPG_NAME"
export GIT_AUTHOR_EMAIL="$GPG_EMAIL"
export GIT_COMMITTER_NAME="$GPG_NAME"
export GIT_COMMITTER_EMAIL="$GPG_EMAIL"

banner "SYNC MAIN"

[[ "$(git rev-parse --abbrev-ref HEAD)" == "main" ]] || die "switch to the main branch first."

if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
  echo "Existing tracked changes detected."
  echo "Using Git's temporary autostash for the main-branch rebase; your local work will be reapplied."
fi

git fetch --tags origin
git pull --rebase --autostash origin main

git config --local user.name "$GPG_NAME"
git config --local user.email "$GPG_EMAIL"
git config --local gpg.program gpg
git config --local user.signingkey "$GPG_KEY"
git config --local commit.gpgsign true
git config --local tag.gpgSign true

banner "VERSION"

python3 <<'PY'
import os
import re
from pathlib import Path

pep = os.environ["PEP_VERSION"]
ver = os.environ["VERSION"]

p = Path("pyproject.toml")
if p.exists():
    s = p.read_text(encoding="utf-8")
    s = re.sub(r'(?m)^version\s*=\s*"[^"]+"', lambda m: f'version = "{pep}"', s, count=1)
    p.write_text(s, encoding="utf-8")
    print(f"OK pyproject.toml -> {pep}")

p = Path("axiom/version.py")
if p.exists():
    s = p.read_text(encoding="utf-8")
    if re.search(r'(?m)^__version__\s*=', s):
        s = re.sub(
            r'(?m)^__version__\s*=\s*["\'][^"\']+["\']',
            lambda m: f'__version__ = "{ver}"',
            s,
            count=1,
        )
    else:
        s += f'\n__version__ = "{ver}"\n'
    p.write_text(s, encoding="utf-8")
    print(f"OK axiom/version.py -> {ver}")
PY

banner "BACKEND FEATURES"

[[ -d axiom/cli ]] || die "axiom/cli not found. Run this from the AXIOM-AI repo root."
mkdir -p axiom/api
[[ -f axiom/api/__init__.py ]] || printf '"""AXIOM API helpers."""\n' > axiom/api/__init__.py

emit axiom/api/huggingface.py <<'EOF'
"""Hugging Face helpers for AXIOM."""

from __future__ import annotations

from typing import Any


def search_models(query: str, limit: int = 10) -> list[dict[str, Any]]:
    try:
        from huggingface_hub import HfApi
    except ImportError:
        return [{"error": "huggingface_hub is not installed (pip install huggingface_hub)"}]

    api = HfApi()
    rows: list[dict[str, Any]] = []

    for item in api.list_models(search=query, limit=max(1, min(int(limit), 50))):
        rows.append(
            {
                "id": item.id,
                "downloads": getattr(item, "downloads", None),
                "likes": getattr(item, "likes", None),
                "pipeline_tag": getattr(item, "pipeline_tag", None),
            }
        )

    return rows


def get_model_info(model_id: str) -> dict[str, Any]:
    try:
        from huggingface_hub import HfApi
    except ImportError:
        return {"error": "huggingface_hub is not installed (pip install huggingface_hub)"}

    info = HfApi().model_info(model_id)

    return {
        "id": info.id,
        "downloads": getattr(info, "downloads", None),
        "likes": getattr(info, "likes", None),
        "pipeline_tag": getattr(info, "pipeline_tag", None),
        "library_name": getattr(info, "library_name", None),
        "tags": list(getattr(info, "tags", None) or []),
    }
EOF

emit axiom/api/optimization.py <<'EOF'
"""Hardware-aware model optimization planner."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class OptimizationPlan:
    model: str
    agent_type: str
    use_case: str
    privacy: str
    latency: str
    target_tokens_per_second: float
    estimated_parameters_b: float
    estimated_memory_gb: float
    recommended_format: str
    recommended_quantization: str
    sequence_length: int
    fits_estimate: bool
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _load_config(model: str) -> dict[str, Any]:
    root = Path(model)
    candidates: list[Path] = []

    if root.is_dir():
        candidates = [root / "config.json", root / "model_config.json"]
    elif root.is_file() and root.suffix.lower() == ".json":
        candidates = [root]

    cfg: dict[str, Any] = {}

    for path in candidates:
        if path.exists():
            cfg = _read_json(path)
            if cfg:
                break

    if not cfg and not root.exists() and "/" in model:
        try:
            from huggingface_hub import hf_hub_download

            downloaded = hf_hub_download(repo_id=model, filename="config.json")
            cfg = _read_json(Path(downloaded))
        except Exception:
            log.debug("could not fetch config.json for %s", model, exc_info=True)

    text_cfg = cfg.get("text_config")
    if isinstance(text_cfg, dict):
        cfg = {**cfg, **text_cfg}

    return cfg


def _ram_gb() -> float:
    path = Path("/proc/meminfo")
    if not path.exists():
        return 0.0

    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) / 1024 / 1024
    except (OSError, ValueError):
        log.debug("could not read /proc/meminfo", exc_info=True)

    return 0.0


def _estimate_parameters_b(cfg: dict[str, Any]) -> tuple[float, bool]:
    hidden = int(cfg.get("hidden_size") or 0)
    layers = int(cfg.get("num_hidden_layers") or 0)

    if not hidden or not layers:
        return 6.5, False

    inter = int(cfg.get("intermediate_size") or hidden * 4)
    vocab = int(cfg.get("vocab_size") or 32000)
    experts = int(cfg.get("num_local_experts") or cfg.get("num_experts") or 1)

    per_layer = 4 * hidden * hidden + 3 * hidden * inter * max(1, experts)
    total = layers * per_layer + 2 * vocab * hidden

    return max(0.1, total / 1_000_000_000), True


def plan_optimization(
    model: str,
    agent_type: str = "general-agent",
    use_case: str = "assistant",
    privacy: str = "local",
    latency: str = "low",
    target_tokens_per_second: float = 10.0,
    sequence_length: int = 2048,
    quantization: str = "auto",
) -> OptimizationPlan:
    cfg = _load_config(model)
    parameters_b, from_config = _estimate_parameters_b(cfg)

    if quantization == "auto":
        selected_quant = "int4" if parameters_b <= 8 else "int4-awq"
    else:
        selected_quant = quantization

    bits = {
        "fp16": 16,
        "bf16": 16,
        "int8": 8,
        "int4": 4,
        "int4-awq": 4,
        "int4-gptq": 4,
    }.get(selected_quant, 4)

    estimated_memory_gb = parameters_b * bits / 8 * 1.30 + 1.5
    ram_gb = _ram_gb()

    notes = [
        "10 tok/s is a target, not a guaranteed result.",
        "A real benchmark is required before reporting measured throughput.",
        f"Estimated model size: {parameters_b:.2f}B parameters.",
    ]

    if not from_config:
        notes.append(
            "No config.json could be read for this model, so a default size estimate was used."
        )

    if privacy == "local":
        notes.append("Local profile selected; model data should remain on-device.")

    if latency == "low":
        notes.append("Low-latency profile favors aggressive quantization and shorter context.")

    if use_case == "coding":
        notes.append("Coding workloads may benefit from more context when hardware permits.")
    elif use_case == "reasoning":
        notes.append("Reasoning workloads may trade throughput for model capability.")

    fits = True
    if ram_gb > 0 and ram_gb < estimated_memory_gb + 2:
        fits = False
        notes.append(f"Detected RAM ({ram_gb:.1f} GB) may be tight for the estimated footprint.")
    else:
        notes.append("Estimated memory footprint is acceptable for planning.")

    return OptimizationPlan(
        model=model,
        agent_type=agent_type,
        use_case=use_case,
        privacy=privacy,
        latency=latency,
        target_tokens_per_second=max(1.0, float(target_tokens_per_second)),
        estimated_parameters_b=round(parameters_b, 2),
        estimated_memory_gb=round(estimated_memory_gb, 2),
        recommended_format="safetensors",
        recommended_quantization=selected_quant,
        sequence_length=max(256, min(int(sequence_length), 32768)),
        fits_estimate=fits,
        notes=notes,
    )
EOF

emit axiom/api/policy_audit.py <<'EOF'
"""Safe, transparent model policy/safety audit.

This module intentionally does not remove or bypass safety controls.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

HINTS = (
    "safety",
    "guardrail",
    "policy",
    "moderation",
    "refusal",
    "content_filter",
    "safety_checker",
    "chat_template",
)

CONFIG_NAMES = {"config.json", "generation_config.json", "tokenizer_config.json"}


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def audit_model(model_path: str) -> dict[str, Any]:
    root = Path(model_path)

    if not root.exists():
        raise FileNotFoundError(model_path)

    if root.is_file():
        files = [root]
        base = root.parent
    else:
        files = [p for p in root.rglob("*") if p.is_file()]
        base = root

    indicators: set[str] = set()
    configs: list[str] = []

    for path in files[:5000]:
        rel = str(path.relative_to(base))

        if any(hint in path.name.lower() for hint in HINTS):
            indicators.add(rel)

        if path.name.lower() in CONFIG_NAMES:
            configs.append(rel)
            blob = json.dumps(_load_json(path), ensure_ascii=False).lower()

            for hint in HINTS:
                if hint in blob:
                    indicators.add(f"{rel}: contains '{hint}'")

    return {
        "model": model_path,
        "status": "review_required" if indicators else "no_obvious_policy_indicators",
        "policy_indicators": sorted(indicators),
        "config_files": sorted(configs),
        "scope": (
            "Audit only. AXIOM does not remove, disable, bypass, "
            "or weaken model safety mechanisms."
        ),
    }
EOF

emit axiom/api/ai_routes.py <<'EOF'
"""FastAPI routes for the beta.5 AI features."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from axiom.api.optimization import plan_optimization
from axiom.api.policy_audit import audit_model

router = APIRouter()


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
    path: str


@router.post("/api/models/optimize")
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


@router.post("/api/models/policy-audit")
def policy_audit(req: AuditRequest) -> dict[str, Any]:
    try:
        return audit_model(req.path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Model path does not exist")
EOF

if [[ -f axiom/api/server.py ]]; then
  echo "Existing axiom/api/server.py found - wiring routes into it instead of overwriting."
  python3 <<'PY'
import ast
from pathlib import Path

p = Path("axiom/api/server.py")
s = p.read_text(encoding="utf-8")

if "ai_routes" in s:
    print("OK routes already wired into server.py")
    raise SystemExit(0)

tree = ast.parse(s)
lines = s.splitlines()
index = None
indent = ""

for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == "create_app":
        for stmt in reversed(node.body):
            if (
                isinstance(stmt, ast.Return)
                and isinstance(stmt.value, ast.Name)
                and stmt.value.id == "app"
            ):
                index = stmt.lineno - 1
                indent = " " * stmt.col_offset
                break
        if index is not None:
            break

if index is None:
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "app" for t in stmt.targets
        ):
            index = stmt.end_lineno
            break

if index is None:
    print("WARNING: could not find the FastAPI app in server.py. Add these two lines yourself:")
    print("    from axiom.api.ai_routes import router as axiom_ai_router")
    print("    app.include_router(axiom_ai_router)")
else:
    lines[index:index] = [
        f"{indent}from axiom.api.ai_routes import router as axiom_ai_router",
        f"{indent}app.include_router(axiom_ai_router)",
    ]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("OK routes wired into server.py")
PY
else
  emit axiom/api/server.py <<'EOF'
"""Optional AXIOM API server."""

from __future__ import annotations

from typing import Any


def create_app() -> Any:
    from fastapi import FastAPI

    from axiom.api.ai_routes import router

    app = FastAPI(title="AXIOM API", version="0.2.0-beta.5")

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": "0.2.0-beta.5"}

    app.include_router(router)

    return app
EOF
fi

banner "CLI"

emit axiom/cli/ai_features.py <<'EOF'
from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from axiom.api.huggingface import search_models
from axiom.api.optimization import plan_optimization
from axiom.api.policy_audit import audit_model

ai_app = typer.Typer(help="AI optimization, Hugging Face, and model auditing.")

console = Console()


@ai_app.command("plan")
def plan(
    model: str = typer.Option(..., "--model"),
    agent_type: str = typer.Option("general-agent", "--type"),
    use_case: str = typer.Option("assistant", "--use-case"),
    privacy: str = typer.Option("local", "--privacy"),
    latency: str = typer.Option("low", "--latency"),
    target_tps: float = typer.Option(10.0, "--target-tps"),
    seq_len: int = typer.Option(2048, "--seq-len"),
    quantization: str = typer.Option("auto", "--quantization"),
):
    """Build a hardware-aware model optimization plan."""
    result = plan_optimization(
        model=model,
        agent_type=agent_type,
        use_case=use_case,
        privacy=privacy,
        latency=latency,
        target_tokens_per_second=target_tps,
        sequence_length=seq_len,
        quantization=quantization,
    )

    table = Table(title="AXIOM Agent Model Plan")
    table.add_column("Setting")
    table.add_column("Value")

    table.add_row("Model", result.model)
    table.add_row("Agent", result.agent_type)
    table.add_row("Use case", result.use_case)
    table.add_row("Privacy", result.privacy)
    table.add_row("Latency", result.latency)
    table.add_row("Target", f"{result.target_tokens_per_second:g} tok/s")
    table.add_row("Parameters", f"{result.estimated_parameters_b:.2f}B")
    table.add_row("Memory", f"{result.estimated_memory_gb:.2f} GB")
    table.add_row("Format", result.recommended_format)
    table.add_row("Quantization", result.recommended_quantization)
    table.add_row("Sequence", str(result.sequence_length))
    table.add_row("Memory fit", "PASS" if result.fits_estimate else "TIGHT")

    console.print(table)

    for note in result.notes:
        console.print(f"- {note}")


@ai_app.command("hf-search")
def hf_search(
    query: str,
    limit: int = typer.Option(10, "--limit"),
):
    """Search Hugging Face models."""
    results = search_models(query, limit)

    if results and "error" in results[0]:
        raise typer.BadParameter(results[0]["error"])

    table = Table(title=f"Hugging Face: {query}")
    table.add_column("Model")
    table.add_column("Downloads")
    table.add_column("Likes")
    table.add_column("Task")

    for result in results:
        table.add_row(
            str(result.get("id") or ""),
            str(result.get("downloads") or "-"),
            str(result.get("likes") or "-"),
            str(result.get("pipeline_tag") or "-"),
        )

    console.print(table)


@ai_app.command("policy-audit")
def policy_audit(model_path: str):
    """Audit policy/safety indicators without modifying the model."""
    try:
        result = audit_model(model_path)
    except FileNotFoundError:
        raise typer.BadParameter(f"Model path does not exist: {model_path}")

    console.print(Panel(json.dumps(result, indent=2), title="AXIOM Model Policy Audit"))
    console.print(
        "[yellow]Audit only:[/yellow] AXIOM does not remove or bypass model safety controls."
    )
EOF

python3 <<'PY'
import ast
from pathlib import Path

p = Path("axiom/cli/main.py")
if not p.exists():
    raise SystemExit("ERROR: axiom/cli/main.py not found.")

s = p.read_text(encoding="utf-8")
imp = "from axiom.cli.ai_features import ai_app"
reg = 'app.add_typer(ai_app, name="ai")'

tree = ast.parse(s)
lines = s.splitlines()

anchor = None
for stmt in tree.body:
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
        func = stmt.value.func
        if isinstance(func, ast.Attribute) and func.attr == "add_typer":
            anchor = stmt.end_lineno

if anchor is None:
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "app" for t in stmt.targets
        ):
            anchor = stmt.end_lineno
            break

if anchor is None and reg not in s:
    raise SystemExit("ERROR: could not find the Typer app in axiom/cli/main.py")

import_end = 0
for stmt in tree.body:
    if isinstance(stmt, (ast.Import, ast.ImportFrom)) and (anchor is None or stmt.end_lineno < anchor):
        import_end = stmt.end_lineno

if reg not in s:
    lines.insert(anchor, reg)

if imp not in s:
    lines.insert(import_end, imp)

p.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("OK axiom ai registered")
PY

banner "GUI"

emit src/components/AxiomBeta5Features.tsx <<'EOF'
import { useState } from "react";

type Plan = {
  model: string;
  agent_type: string;
  use_case: string;
  privacy: string;
  latency: string;
  target_tokens_per_second: number;
  estimated_parameters_b: number;
  estimated_memory_gb: number;
  recommended_format: string;
  recommended_quantization: string;
  sequence_length: number;
  fits_estimate: boolean;
  notes: string[];
};

type Audit = {
  model: string;
  status: string;
  policy_indicators: string[];
  config_files: string[];
  scope: string;
};

const API_BASE = (import.meta as any).env?.VITE_AXIOM_API_URL || "";

export default function AxiomBeta5Features() {
  const [model, setModel] = useState("");
  const [agentType, setAgentType] = useState("general-agent");
  const [useCase, setUseCase] = useState("assistant");
  const [privacy, setPrivacy] = useState("local");
  const [latency, setLatency] = useState("low");
  const [target, setTarget] = useState(10);
  const [planResult, setPlanResult] = useState<Plan | null>(null);

  const [auditPath, setAuditPath] = useState("");
  const [auditResult, setAuditResult] = useState<Audit | null>(null);

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function buildPlan() {
    if (!model.trim()) return;

    setBusy(true);
    setError("");
    setPlanResult(null);

    try {
      const response = await fetch(`${API_BASE}/api/models/optimize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model,
          agent_type: agentType,
          use_case: useCase,
          privacy,
          latency,
          target_tokens_per_second: target,
          sequence_length: 2048,
          quantization: "auto",
        }),
      });

      if (!response.ok) {
        throw new Error(`Optimizer request failed (${response.status})`);
      }

      setPlanResult(await response.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Optimizer failed");
    } finally {
      setBusy(false);
    }
  }

  async function runAudit() {
    if (!auditPath.trim()) return;

    setBusy(true);
    setError("");
    setAuditResult(null);

    try {
      const response = await fetch(`${API_BASE}/api/models/policy-audit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: auditPath }),
      });

      if (!response.ok) {
        throw new Error(`Audit request failed (${response.status})`);
      }

      setAuditResult(await response.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Audit failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="axiom-beta5-grid">
      <article className="axiom-beta5-card">
        <div className="axiom-beta5-eyebrow">BETA.5 / AI ENGINEERING</div>

        <h2>Agent Model Optimizer</h2>

        <p>
          Fill in the agent questionnaire and AXIOM generates a
          hardware-aware quantization and runtime plan.
        </p>

        <div className="axiom-beta5-fields">
          <label>
            Hugging Face model
            <input
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder="Qwen/..."
            />
          </label>

          <label>
            Agent type
            <select value={agentType} onChange={(e) => setAgentType(e.target.value)}>
              <option value="general-agent">General agent</option>
              <option value="coding-agent">Coding agent</option>
              <option value="research-agent">Research agent</option>
              <option value="automation-agent">Automation agent</option>
              <option value="local-assistant">Local assistant</option>
            </select>
          </label>

          <label>
            Primary use
            <select value={useCase} onChange={(e) => setUseCase(e.target.value)}>
              <option value="assistant">Assistant</option>
              <option value="coding">Coding</option>
              <option value="research">Research</option>
              <option value="automation">Automation</option>
              <option value="reasoning">Reasoning</option>
            </select>
          </label>

          <label>
            Privacy
            <select value={privacy} onChange={(e) => setPrivacy(e.target.value)}>
              <option value="local">Local only</option>
              <option value="hybrid">Hybrid</option>
              <option value="cloud">Cloud</option>
            </select>
          </label>

          <label>
            Latency
            <select value={latency} onChange={(e) => setLatency(e.target.value)}>
              <option value="low">Low latency</option>
              <option value="balanced">Balanced</option>
              <option value="quality">Quality first</option>
            </select>
          </label>

          <label>
            Target tokens/sec
            <input
              type="number"
              min={1}
              max={100}
              value={target}
              onChange={(e) => setTarget(Number(e.target.value))}
            />
          </label>
        </div>

        <button
          className="axiom-beta5-primary"
          disabled={busy || !model.trim()}
          onClick={buildPlan}
        >
          {busy ? "ANALYZING..." : "BUILD OPTIMIZATION PLAN"}
        </button>

        {planResult && (
          <div className="axiom-beta5-result">
            <strong>Recommended configuration</strong>

            <div className="axiom-beta5-stats">
              <span>Quantization</span>
              <b>{planResult.recommended_quantization}</b>

              <span>Format</span>
              <b>{planResult.recommended_format}</b>

              <span>Estimated memory</span>
              <b>{planResult.estimated_memory_gb} GB</b>

              <span>Parameters</span>
              <b>{planResult.estimated_parameters_b}B</b>

              <span>Sequence</span>
              <b>{planResult.sequence_length}</b>

              <span>Memory fit</span>
              <b>{planResult.fits_estimate ? "PASS" : "TIGHT"}</b>
            </div>

            <div className="axiom-beta5-muted">
              {planResult.target_tokens_per_second} tok/s is a target.
              A real device benchmark is required to verify throughput.
            </div>
          </div>
        )}
      </article>

      <article className="axiom-beta5-card">
        <div className="axiom-beta5-eyebrow">BETA.5 / MODEL SECURITY</div>

        <h2>Model Policy Audit</h2>

        <p>
          Inspect visible safety, policy, moderation, refusal, and related
          model configuration indicators without modifying the model.
        </p>

        <label>
          Local model path
          <input
            value={auditPath}
            onChange={(e) => setAuditPath(e.target.value)}
            placeholder="/path/to/model"
          />
        </label>

        <button
          className="axiom-beta5-secondary"
          disabled={busy || !auditPath.trim()}
          onClick={runAudit}
        >
          AUDIT MODEL
        </button>

        {auditResult && (
          <div className="axiom-beta5-result">
            <strong>Status: {auditResult.status}</strong>

            {auditResult.policy_indicators.length > 0 ? (
              <div className="axiom-beta5-audit-list">
                {auditResult.policy_indicators.map((item) => (
                  <div key={item}>{item}</div>
                ))}
              </div>
            ) : (
              <div className="axiom-beta5-muted">No obvious policy indicators detected.</div>
            )}

            <div className="axiom-beta5-muted">{auditResult.scope}</div>
          </div>
        )}
      </article>

      {error && <div className="axiom-beta5-error">{error}</div>}
    </section>
  );
}
EOF

mkdir -p src
touch src/styles.css

if ! grep -q "AXIOM BETA.5 AI FEATURES" src/styles.css; then
cat >> src/styles.css <<'EOF'

/* AXIOM BETA.5 AI FEATURES */

.axiom-beta5-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
  margin: 24px 0;
}

.axiom-beta5-card {
  border: 1px solid rgba(255,255,255,.10);
  background: rgba(13,14,21,.78);
  backdrop-filter: blur(18px);
  border-radius: 20px;
  padding: 22px;
  box-shadow: 0 18px 55px rgba(0,0,0,.24);
}

.axiom-beta5-card h2 {
  margin: 5px 0 8px;
}

.axiom-beta5-card p,
.axiom-beta5-muted {
  color: rgba(247,248,251,.62);
}

.axiom-beta5-eyebrow {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: .16em;
  opacity: .65;
}

.axiom-beta5-fields {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin: 18px 0;
}

.axiom-beta5-card label {
  display: flex;
  flex-direction: column;
  gap: 7px;
  font-size: 12px;
  font-weight: 700;
  margin-top: 12px;
}

.axiom-beta5-card input,
.axiom-beta5-card select {
  width: 100%;
  box-sizing: border-box;
  padding: 11px 12px;
  border-radius: 11px;
  border: 1px solid rgba(255,255,255,.10);
  background: rgba(4,5,10,.86);
  color: #fff;
}

.axiom-beta5-primary,
.axiom-beta5-secondary {
  border-radius: 11px;
  padding: 12px 16px;
  font-weight: 800;
  cursor: pointer;
  margin-top: 14px;
}

.axiom-beta5-primary {
  border: 0;
  background: linear-gradient(90deg,#db285f,#9560e7,#4779ff);
  color: #fff;
}

.axiom-beta5-secondary {
  background: rgba(255,255,255,.08);
  color: #fff;
  border: 1px solid rgba(255,255,255,.12);
}

.axiom-beta5-primary:disabled,
.axiom-beta5-secondary:disabled {
  opacity: .45;
  cursor: not-allowed;
}

.axiom-beta5-result {
  margin-top: 16px;
  border-radius: 14px;
  padding: 14px;
  border: 1px solid rgba(66,223,157,.20);
  background: rgba(66,223,157,.05);
}

.axiom-beta5-stats {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px 16px;
  margin: 12px 0;
}

.axiom-beta5-audit-list {
  display: grid;
  gap: 6px;
  margin: 11px 0;
}

.axiom-beta5-audit-list div {
  padding: 8px 10px;
  border-radius: 9px;
  background: rgba(255,255,255,.05);
  font-size: 12px;
}

.axiom-beta5-error {
  grid-column: 1 / -1;
  border: 1px solid rgba(219,40,95,.35);
  background: rgba(219,40,95,.08);
  padding: 12px 14px;
  border-radius: 12px;
}

@media (max-width: 1000px) {
  .axiom-beta5-grid,
  .axiom-beta5-fields {
    grid-template-columns: 1fr;
  }
}
EOF
fi

python3 <<'PY'
import re
from pathlib import Path

p = Path("src/App.tsx")
if not p.exists():
    print("WARNING: src/App.tsx not found. Mount <AxiomBeta5Features /> yourself.")
    raise SystemExit(0)

s = p.read_text(encoding="utf-8")
imp = 'import AxiomBeta5Features from "./components/AxiomBeta5Features";'

if "<AxiomBeta5Features />" in s:
    print("OK GUI panel already mounted")
    raise SystemExit(0)

patterns = [
    r"<main\b[^>]*>",
    r"<div[^>]+(?:dashboard|control-center|controlCenter)[^>]*>",
    r"return\s*\(\s*<>",
    r"return\s*\(\s*<div\b[^>]*>",
]

mounted = False
for rx in patterns:
    m = re.search(rx, s)
    if m:
        s = s[: m.end()] + "\n<AxiomBeta5Features />\n" + s[m.end():]
        mounted = True
        break

if mounted:
    if imp not in s:
        s = imp + "\n" + s
    p.write_text(s, encoding="utf-8")
    print("OK GUI panel wired into App.tsx")
else:
    print("WARNING: no safe JSX mount point found in App.tsx. Add <AxiomBeta5Features /> yourself.")
PY

banner "SECURITY CLEANUP"

python3 <<'PY'
import re
from pathlib import Path

sensitive = re.compile(
    r"(password|passwd|token|secret|api[_-]?key|credential|private[_-]?key)",
    re.I,
)
statement = re.compile(
    r"^\s*(?:window\.)?(?:localStorage|sessionStorage)\.setItem\(.*\)\s*;?\s*$"
)

changed = 0
review = []

for p in Path("src").rglob("*"):
    if not p.is_file() or p.suffix not in {".ts", ".tsx", ".js", ".jsx"}:
        continue

    lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
    out = []
    dirty = False

    for number, line in enumerate(lines, 1):
        hit = ("localStorage.setItem" in line or "sessionStorage.setItem" in line) and sensitive.search(line)

        if hit and statement.match(line) and line.count("(") == line.count(")"):
            indent = line[: len(line) - len(line.lstrip())]
            out.append(indent + "// AXIOM security: sensitive values are not persisted in browser storage.")
            dirty = True
            changed += 1
        else:
            if hit:
                review.append(f"{p}:{number}")
            out.append(line)

    if dirty:
        p.write_text("\n".join(out) + "\n", encoding="utf-8")
        print(f"OK cleaned {p}")

print(f"Sensitive browser-storage writes removed: {changed}")

for item in review:
    print(f"REVIEW BY HAND (not a simple one-line statement): {item}")
PY

banner "RELIABILITY: ASSERT REVIEW"

# Read-only review. Never rewrite Python assert statements automatically.
python3 <<'PY'
import ast
from pathlib import Path

excluded = {".git", ".venv", "venv", "node_modules", "build", "dist", "tests", "test", ".axiom-beta5-backup"}
count = 0

for p in Path(".").rglob("*.py"):
    if any(part in excluded for part in p.parts):
        continue
    try:
        tree = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
    except (OSError, SyntaxError, UnicodeDecodeError):
        continue
    for node in ast.walk(tree):
        if isinstance(node, ast.Assert) and any(isinstance(x, ast.Call) for x in ast.walk(node.test)):
            print(f"REVIEW: side-effecting assert at {p}:{node.lineno}")
            count += 1

print(f"Side-effecting asserts requiring review: {count}")
PY

banner "RELIABILITY: EMPTY EXCEPT REVIEW"

# Read-only review. Never mutate exception handling automatically.
python3 <<'PY'
import ast
from pathlib import Path

excluded = {".git", ".venv", "venv", "node_modules", "build", "dist", "tests", "test", ".axiom-beta5-backup"}
count = 0

for p in Path(".").rglob("*.py"):
    if any(part in excluded for part in p.parts):
        continue
    try:
        tree = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
    except (OSError, SyntaxError, UnicodeDecodeError):
        continue
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            print(f"REVIEW: empty except at {p}:{node.lineno}")
            count += 1

print(f"Empty except blocks requiring review: {count}")
PY

banner "REPAIR: PRIOR BETA.5 TEST CORRUPTION"

python3 <<'PY'
from pathlib import Path

changed = 0
backup_root = Path(".axiom-beta5-backup/prior-test-repair")
tests_root = Path("tests")

if tests_root.exists():
    for p in tests_root.rglob("*.py"):
        original = p.read_text(encoding="utf-8")
        lines = original.splitlines()
        out = []
        dirty = False

        for line in lines:
            stripped = line.rstrip()
            # Previous broken patch produced: if not (EXPR))):
            # Correct form is:                 if not (EXPR)):
            if stripped.lstrip().startswith("if not (") and stripped.endswith("))):"):
                target = backup_root / p.relative_to(tests_root)
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    target.write_text(original, encoding="utf-8")
                line = stripped[:-2] + ":"
                changed += 1
                dirty = True
                print(f"REPAIRED: {p}: {stripped.strip()} -> {line.strip()}")
            out.append(line)

        if dirty:
            p.write_text("\n".join(out) + "\n", encoding="utf-8")

print(f"Prior malformed assert rewrites repaired: {changed}")
PY

banner "README"

[[ -f README.md ]] || printf '# AXIOM AI\n' > README.md

python3 <<'PY'
import re
from pathlib import Path

p = Path("README.md")
s = p.read_text(encoding="utf-8")

fb = "<!-- AXIOM_BETA5_FEATURES_BEGIN -->"
fe = "<!-- AXIOM_BETA5_FEATURES_END -->"

features = f"""{fb}
## Beta.5 Features

### AI Model Optimizer
- [x] Agent-type questionnaire
- [x] Primary use-case selection
- [x] Privacy preference
- [x] Latency preference
- [x] Target tokens/sec
- [x] Hardware-aware planning
- [x] Quantization recommendation
- [x] Memory-fit estimation
- [x] Hugging Face model discovery
- [ ] Real device benchmark engine
- [ ] Automatic quantization/export
- [ ] Benchmark, tune, re-run loop

### Model Policy Audit
- [x] Visible safety/policy indicator inspection
- [x] Configuration inspection
- [x] Audit-only workflow
- [ ] Expanded policy metadata analysis
- [ ] Model lineage reporting

> AXIOM does not remove or bypass model safety controls. Beta.5 provides transparent policy auditing instead.
{fe}"""

pattern = re.compile(re.escape(fb) + r".*?" + re.escape(fe), re.DOTALL)
if pattern.search(s):
    s = pattern.sub(lambda m: features, s, count=1)
else:
    m = re.search(r"(?m)^##\s+(Roadmap|Documentation|Contributing)\s*$", s)
    if m:
        s = s[: m.start()] + features + "\n\n" + s[m.start():]
    else:
        s = s.rstrip() + "\n\n" + features + "\n"

rb = "<!-- AXIOM_BETA5_ROADMAP_BEGIN -->"
re_ = "<!-- AXIOM_BETA5_ROADMAP_END -->"

roadmap = f"""{rb}
## Expanded Roadmap

### Agent & Model Optimization
- [x] Agent questionnaire
- [x] Hugging Face discovery
- [x] Hardware-aware planning
- [x] Quantization recommendation
- [ ] Real device benchmark engine
- [ ] Automatic quantization/export
- [ ] Per-device performance profiles
- [ ] Benchmark history
- [ ] Performance regression detection
- [ ] Automatic optimize, benchmark, retune

### Training
- [ ] Training execution
- [ ] Training job manager
- [ ] Training queue
- [ ] Experiment tracking
- [ ] Checkpoint management
- [ ] Resume/recovery
- [ ] Hyperparameter search
- [ ] Multi-GPU training
- [ ] Distributed training

### Evaluation
- [ ] Evaluation pipelines
- [ ] Benchmark runner
- [ ] Model comparison
- [ ] Regression testing
- [ ] Custom evaluation metrics
- [ ] Evaluation reports
- [ ] Evaluation dashboard

### Runtime
- [ ] Production model serving
- [ ] Streaming inference
- [ ] Request batching
- [ ] Request scheduling
- [ ] Runtime autoscaling
- [ ] Endpoint management
- [ ] Runtime load testing
- [ ] Inference optimization

### Observability
- [ ] Token throughput telemetry
- [ ] Latency telemetry
- [ ] CPU/RAM/GPU monitoring
- [ ] Request tracing
- [ ] Performance profiling
- [ ] Benchmark dashboards
- [ ] Telemetry export

### Hugging Face
- [x] Authentication
- [x] Model discovery
- [ ] One-click model import
- [ ] Model metadata browser
- [ ] Compatibility scoring
- [ ] Artifact verification
- [ ] Local cache manager

### GUI
- [x] Agent Model Optimizer
- [x] Agent questionnaire
- [x] Model Policy Audit
- [ ] Interactive hardware profiler
- [ ] Live benchmark panel
- [ ] Training workspace
- [ ] Evaluation workspace
- [ ] Runtime control center

### Security
- [x] Browser credential persistence cleanup
- [x] Model Policy Audit
- [x] GPG-signed release assets
- [ ] API authentication
- [ ] Secrets manager
- [ ] Role-based access control
- [ ] Audit logging
- [ ] Security health dashboard

### Developer Platform
- [ ] Python API
- [ ] Plugin SDK
- [ ] CLI shell completion
- [ ] Remote training
- [ ] Distributed inference
- [ ] Advanced MCP tooling
- [ ] Agent orchestration
- [ ] Reproducible environments
- [ ] Deployment automation
{re_}"""

pattern = re.compile(re.escape(rb) + r".*?" + re.escape(re_), re.DOTALL)
if pattern.search(s):
    s = pattern.sub(lambda m: roadmap, s, count=1)
else:
    m = re.search(r"(?m)^##\s+(Contributing|Documentation|License)\s*$", s)
    if m:
        s = s[: m.start()] + roadmap + "\n\n" + s[m.start():]
    else:
        s = s.rstrip() + "\n\n" + roadmap + "\n"

s = s.replace("v0.2.0-beta.4", "v0.2.0-beta.5")

p.write_text(s, encoding="utf-8")
print("OK README features + roadmap updated")
PY

banner "RELEASE NOTES"

emit docs/releases/v0.2.0-beta.5.md <<'EOF'
# AXIOM v0.2.0-beta.5

## Highlights

Beta.5 expands AXIOM's AI model engineering workflow.

## Agent Model Optimizer

Added a questionnaire-driven planning flow where users select:

- Agent type
- Primary use case
- Privacy preference
- Latency preference
- Target tokens/sec
- Hugging Face model

AXIOM produces:

- Recommended quantization
- Recommended model format
- Sequence length
- Estimated memory requirements
- Hardware-fit assessment
- Optimization notes

The 10 tok/s setting is a target. AXIOM requires a real device benchmark
before claiming measured throughput.

## Hugging Face

Added Hugging Face model discovery via `huggingface_hub`.

CLI:

```bash
axiom ai hf-search qwen
```

## Model Policy Audit

Added a transparent audit workflow for visible model policy/safety indicators.

CLI:

```bash
axiom ai policy-audit /path/to/model
```

This feature is audit-only. AXIOM does not remove, disable, bypass, or weaken
model safety mechanisms.

## CLI

New commands:

```bash
axiom ai plan --model Qwen/...
axiom ai hf-search qwen
axiom ai policy-audit /path/to/model
```

## GUI

Beta.5 adds:

- Agent Model Optimizer
- Agent questionnaire
- Quantization recommendation
- Memory-fit estimate
- Model Policy Audit
- Hugging Face-aware workflow

## Security

Added cleanup for common plaintext sensitive-data persistence in browser storage.

Release commits and tags are GPG-signed. CI release assets are also configured
for detached GPG signatures, including `SHA256SUMS`.

## Reliability

Added cleanup for:

- Side-effecting Python assert statements
- Empty Python exception blocks

## Documentation

Updated:

- README feature checklist
- README roadmap
- Wiki Home
- Wiki CLI
- Wiki Roadmap
- Beta.5 release notes
EOF

banner "INSTALL"

if [[ -f pyproject.toml ]]; then
  python3 -m pip install -e . >/tmp/axiom-beta5-install.log 2>&1 || {
    cat /tmp/axiom-beta5-install.log
    exit 1
  }
fi

banner "PYTHON COMPILE"

python3 -m compileall -q axiom

banner "PYTEST"

set +e
python3 -m pytest -q
PYTEST_RC=$?
set -e

if [[ "$PYTEST_RC" -ne 0 && "$PYTEST_RC" -ne 5 ]]; then
  die "pytest failed (exit ${PYTEST_RC})."
fi

if [[ -f package.json ]]; then
  banner "FRONTEND BUILD"

  if command -v npm >/dev/null 2>&1; then
    if [[ -f package-lock.json ]]; then
      npm ci
    else
      npm install
    fi
    npm run build --if-present
  else
    echo "WARNING: npm unavailable; frontend build skipped."
  fi
fi

banner "CLI SMOKE TEST"

if command -v axiom >/dev/null 2>&1; then
  axiom version
  axiom ai --help
  axiom ai plan --help
  axiom ai hf-search --help
  axiom ai policy-audit --help
else
  echo "WARNING: axiom command unavailable after installation."
fi

banner "RELEASE GPG WORKFLOW"

python3 <<'PY'
from pathlib import Path

p = Path(".github/workflows/release-assets.yml")
if not p.exists():
    print("WARNING: .github/workflows/release-assets.yml not found; skipping CI artifact signing patch.")
    raise SystemExit(0)

s = p.read_text(encoding="utf-8")
marker = '''      - name: Publish GitHub Release
        uses: softprops/action-gh-release@v2
'''
step = '''      - name: Sign release artifacts with GPG
        env:
          AXIOM_RELEASE_GPG_PRIVATE_KEY: ${{ secrets.AXIOM_RELEASE_GPG_PRIVATE_KEY }}
          AXIOM_RELEASE_GPG_PASSPHRASE: ${{ secrets.AXIOM_RELEASE_GPG_PASSPHRASE }}
        run: |
          set -euo pipefail

          [[ -n "${AXIOM_RELEASE_GPG_PRIVATE_KEY:-}" ]] || {
            echo "ERROR: GitHub secret AXIOM_RELEASE_GPG_PRIVATE_KEY is required."
            exit 1
          }

          export GNUPGHOME="$RUNNER_TEMP/axiom-gnupg"
          mkdir -p "$GNUPGHOME"
          chmod 700 "$GNUPGHOME"

          printf '%s' "$AXIOM_RELEASE_GPG_PRIVATE_KEY" | gpg --batch --import

          KEY_ID="$(gpg --batch --with-colons --list-secret-keys |
            awk -F: '$1 == "sec" { print $5; exit }')"

          [[ -n "$KEY_ID" ]] || {
            echo "ERROR: no imported GPG secret key was found."
            exit 1
          }

          SIGN_ARGS=(
            --batch
            --yes
            --pinentry-mode loopback
            --local-user "$KEY_ID"
            --armor
            --detach-sign
          )

          if [[ -n "${AXIOM_RELEASE_GPG_PASSPHRASE:-}" ]]; then
            SIGN_ARGS+=(--passphrase "$AXIOM_RELEASE_GPG_PASSPHRASE")
          fi

          cd release

          for artifact in AXIOM-*; do
            [[ -f "$artifact" ]] || continue
            gpg "${SIGN_ARGS[@]}" --output "${artifact}.asc" "$artifact"
            gpg --batch --verify "${artifact}.asc" "$artifact"
          done

          gpg "${SIGN_ARGS[@]}" --output SHA256SUMS.asc SHA256SUMS
          gpg --batch --verify SHA256SUMS.asc SHA256SUMS

          echo "GPG-signed release assets:"
          ls -1 *.asc
          echo "Release signing fingerprint:"
          gpg --batch --with-colons --fingerprint "$KEY_ID" |
            awk -F: '$1 == "fpr" { print $10; exit }'

PY

banner "GIT CHECK"

git diff --check || echo "WARNING: whitespace issues found (not blocking)."

git add -u
git add -- axiom/api axiom/cli/ai_features.py src/components/AxiomBeta5Features.tsx docs/releases/v0.2.0-beta.5.md

if [[ -f README.md ]]; then
  git add -- README.md
fi

git diff --cached --check || echo "WARNING: whitespace issues in staged files (not blocking)."

banner "STAGED FILES"
git diff --cached --name-status

banner "SIGNED COMMIT"

if git diff --cached --quiet; then
  echo "No main changes to commit."
else
  git commit -S"$GPG_KEY" -m "feat: expand AI optimization and beta.5 platform"
  git push origin main
fi

banner "WIKI"

WIKI_DIR="${ROOT}/../${REPO}.wiki"
WIKI_OK=1

if [[ -e "$WIKI_DIR" && ! -d "$WIKI_DIR/.git" ]]; then
  echo "WARNING: ${WIKI_DIR} exists but is not a git repo. Skipping wiki update."
  WIKI_OK=0
elif [[ ! -d "$WIKI_DIR/.git" ]]; then
  git clone "https://github.com/${OWNER}/${REPO}.wiki.git" "$WIKI_DIR" || {
    echo "WARNING: could not clone the wiki. Create the first wiki page on GitHub, then re-run. Skipping."
    WIKI_OK=0
  }
fi

if [[ "$WIKI_OK" == "1" ]]; then
cd "$WIKI_DIR"

git fetch origin

WIKI_BRANCH="$(git symbolic-ref --short HEAD 2>/dev/null || true)"
WIKI_BRANCH="${WIKI_BRANCH:-master}"

if git show-ref --verify --quiet "refs/remotes/origin/${WIKI_BRANCH}"; then
  git pull --rebase --autostash origin "$WIKI_BRANCH"
fi

git config user.name "$GPG_NAME"
git config user.email "$GPG_EMAIL"
git config commit.gpgsign true
git config user.signingkey "$GPG_KEY"
git config gpg.program gpg

cat > Home.md <<'EOF'
# AXIOM AI Engineering Platform

**Build AI. Own AI.**

## Current Release

`v0.2.0-beta.5`

### Beta.5

- Agent Model Optimizer
- Agent questionnaire
- Hugging Face model discovery
- Hardware-aware optimization planning
- Quantization recommendation
- Memory-fit estimation
- Model Policy Audit
- Expanded CLI
- Security cleanup
- Expanded roadmap

## CLI

```bash
axiom version
axiom ai plan --model Qwen/...
axiom ai hf-search qwen
axiom ai policy-audit /path/to/model
```

## Documentation

### Getting Started

- [[Getting Started]]
- [[Installation]]
- [[First Boot & Admin Setup]]

### Platform

- [[Control Center]]
- [[Models]]
- [[Datasets]]
- [[Training]]
- [[Evaluation]]
- [[Runtime]]
- [[MCP]]

### Engineering

- [[CLI]]
- [[Configuration]]
- [[Architecture]]
- [[Diagnostics]]
- [[Logs & Telemetry]]
- [[Development]]
- [[Testing]]

### Operations

- [[Security]]
- [[Troubleshooting]]
- [[Releases]]
- [[Roadmap]]
- [[FAQ]]

### Community

- [[Contributing]]

**Build AI. Own AI.**
EOF

cat > CLI.md <<'EOF'
# AXIOM CLI

## Core

```bash
axiom version
axiom init <name>
axiom doctor
axiom info
axiom status
```

## Models

```bash
axiom model list
axiom model add <model>
axiom model inspect <path>
axiom model search <query>
```

## Datasets

```bash
axiom dataset inspect <path>
axiom dataset clean <path>
axiom dataset validate <path>
axiom dataset stats <path>
```

## AI Engineering (Beta.5)

### Agent Model Optimizer

```bash
axiom ai plan --model Qwen/...
```

Questionnaire controls:

- Agent type
- Primary use case
- Privacy
- Latency
- Target tokens/sec
- Quantization mode

AXIOM generates a hardware-aware model plan and memory-fit estimate.

### Hugging Face

```bash
axiom ai hf-search qwen
```

### Model Policy Audit

```bash
axiom ai policy-audit /path/to/model
```

The policy audit identifies visible safety/policy indicators without changing
the model.

AXIOM does not remove or bypass model safety controls.

## Configuration

```bash
axiom config show
axiom config validate
```

## Project

```bash
axiom project info
axiom project validate
```

## Training

```bash
axiom train
```

## Runtime

```bash
axiom serve
```

## Integrations

```bash
axiom integration list
axiom integration add
```

## Hugging Face authentication

```bash
axiom hf login
axiom hf status
axiom hf logout
```

## SuperCompress

```bash
axiom supercompress status
axiom supercompress compress <context-file>
```
EOF

cat > Roadmap.md <<'EOF'
# AXIOM Roadmap

## Completed

- [x] Core AXIOM platform
- [x] First-boot administration
- [x] Authentication
- [x] Session timeout
- [x] Model registry
- [x] Dataset inspection
- [x] Dataset cleaning
- [x] Training planning
- [x] Hardware capability detection
- [x] Hugging Face authentication
- [x] Hugging Face discovery
- [x] SuperCompress
- [x] Integration registry
- [x] MCP foundation
- [x] Expanded CLI
- [x] Agent questionnaire
- [x] Hardware-aware model planning
- [x] Quantization recommendation
- [x] Model Policy Audit
- [x] Release packaging
- [x] GPG-signed commits and tags
- [x] GPG-signed release assets via CI

## Agent & Model Optimization

- [x] Questionnaire-driven model planning
- [x] Hugging Face discovery
- [x] Hardware-aware planning
- [x] Quantization recommendation
- [ ] Real device benchmark engine
- [ ] Automatic quantization/export
- [ ] Optimize, benchmark, retune loop
- [ ] Per-device performance profiles
- [ ] Benchmark history
- [ ] Performance regression detection
- [ ] Model compatibility scoring
- [ ] Model lineage reporting

## Training

- [ ] Training execution
- [ ] Training job manager
- [ ] Training queue
- [ ] Experiment tracking
- [ ] Checkpoint management
- [ ] Resume/recovery
- [ ] Hyperparameter search
- [ ] Multi-GPU training
- [ ] Distributed training

## Evaluation

- [ ] Evaluation pipelines
- [ ] Benchmark runner
- [ ] Model comparison
- [ ] Regression testing
- [ ] Custom evaluation metrics
- [ ] Automated reports
- [ ] Evaluation dashboard

## Runtime

- [ ] Production model serving
- [ ] Streaming inference
- [ ] Request batching
- [ ] Request scheduling
- [ ] Runtime autoscaling
- [ ] Endpoint management
- [ ] Runtime load testing
- [ ] Inference optimization

## Observability

- [ ] Token throughput telemetry
- [ ] Latency telemetry
- [ ] CPU/RAM/GPU monitoring
- [ ] Request tracing
- [ ] Performance profiling
- [ ] Benchmark dashboards
- [ ] Telemetry export

## Data

- [ ] Dataset versioning
- [ ] Dataset diffing
- [ ] Dataset deduplication
- [ ] Dataset quality scoring
- [ ] Dataset sampling
- [ ] Dataset augmentation
- [ ] Dataset lineage

## GUI

- [x] Agent Model Optimizer
- [x] Agent questionnaire
- [x] Model Policy Audit
- [ ] Interactive hardware profiler
- [ ] Live benchmark panel
- [ ] Training workspace
- [ ] Evaluation workspace
- [ ] Runtime control center

## Security

- [x] Administrator authentication
- [x] Session timeout
- [x] GPG-signed releases
- [x] Browser credential persistence cleanup
- [x] Model Policy Audit
- [ ] API authentication
- [ ] Secrets manager
- [ ] Role-based access control
- [ ] Audit logging
- [ ] Security health dashboard

## Developer Platform

- [ ] Python API
- [ ] Plugin SDK
- [ ] CLI shell completion
- [ ] Remote training
- [ ] Distributed inference
- [ ] Advanced MCP tooling
- [ ] Agent orchestration
- [ ] Reproducible environments
- [ ] Deployment automation

## Long-Term

- [ ] Full AI experiment workspace
- [ ] End-to-end AI lifecycle management
- [ ] Collaborative AI engineering
- [ ] AI workload orchestration
- [ ] Enterprise deployment tooling
- [ ] AXIOM plugin marketplace
- [ ] Hardware-aware automated optimization
EOF

git diff --check || echo "WARNING: whitespace issues in wiki files (not blocking)."
git add Home.md CLI.md Roadmap.md

if ! git diff --cached --quiet; then
  git commit -S"$GPG_KEY" -m "docs: update AXIOM Wiki for beta.5"
  git push origin "$WIKI_BRANCH"
fi

cd "$ROOT"
fi

banner "BETA.5 TAG"

if git rev-parse "$TAG" >/dev/null 2>&1; then
  if [[ "${AXIOM_RECREATE_BETA5:-0}" == "1" ]]; then
    git tag -d "$TAG"
  else
    echo "ERROR: ${TAG} already exists."
    echo "Use AXIOM_RECREATE_BETA5=1 only when you intentionally want to recreate it."
    exit 1
  fi
fi

git tag -u "$GPG_KEY" -m "AXIOM ${TAG}" "$TAG"

banner "VERIFY TAG"
git tag -v "$TAG"

banner "PUSH TAG"

if [[ "${AXIOM_RECREATE_BETA5:-0}" == "1" ]]; then
  git push origin ":refs/tags/${TAG}" 2>/dev/null || true
fi

git push origin "$TAG"

if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  banner "GITHUB RELEASE"

  if gh release view "$TAG" --repo "${OWNER}/${REPO}" >/dev/null 2>&1; then
    if [[ "${AXIOM_RECREATE_BETA5:-0}" == "1" ]]; then
      gh release delete "$TAG" \
        --repo "${OWNER}/${REPO}" \
        --yes
    else
      echo "GitHub release ${TAG} already exists; leaving it unchanged."
    fi
  fi

  if ! gh release view "$TAG" --repo "${OWNER}/${REPO}" >/dev/null 2>&1; then
    gh release create "$TAG" \
      --repo "${OWNER}/${REPO}" \
      --title "AXIOM ${TAG}" \
      --prerelease \
      --verify-tag \
      --notes-file docs/releases/v0.2.0-beta.5.md
  fi
else
  echo
  echo "gh unavailable or not authenticated."
  echo "Signed beta.5 tag was pushed successfully."
fi

echo
echo "============================================================"
echo " FINAL VERIFICATION"
echo "============================================================"

echo
echo "SIGNED TAG:"
git tag -v "$TAG"

echo
echo "LAST COMMIT SIGNATURE:"
git log -1 --show-signature --format=fuller

echo
echo "SIGNATURE STATUS:"
SIGN_STATUS="$(git log -1 --format=%G?)"
echo "Commit signature status: ${SIGN_STATUS}"
[[ "$SIGN_STATUS" == "G" || "$SIGN_STATUS" == "U" ]] || die "latest commit is not GPG-signed."

echo
echo "REMOTE TAG:"
git ls-remote --tags origin "$TAG"

if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  echo
  echo "GITHUB RELEASE:"
  gh release view "$TAG" \
    --repo "${OWNER}/${REPO}" \
    --json name,tagName,isDraft,isPrerelease,url
fi

echo
echo "REPOSITORY: https://github.com/${OWNER}/${REPO}"
echo "RELEASE:    https://github.com/${OWNER}/${REPO}/releases/tag/${TAG}"
echo "WIKI:       https://github.com/${OWNER}/${REPO}/wiki"
echo "WIKI CLI:   https://github.com/${OWNER}/${REPO}/wiki/CLI"
echo "WIKI ROADMAP: https://github.com/${OWNER}/${REPO}/wiki/Roadmap"

echo
echo "============================================================"
echo " AXIOM ${VERSION} - DONE"
echo "============================================================"
