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
