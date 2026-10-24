import { useEffect, useState, type FormEvent } from "react";
import { Activity, Gauge, RefreshCcw, Rocket } from "lucide-react";
import { axiomApi, type EngineFabricProfile, type EngineFabricReport, type EngineFabricChatResult } from "../api/client";

const formatStatus = (status: string) => status.replaceAll("_", " ").toUpperCase();

export default function LocalEngineFabricPanel() {
  const [profile, setProfile] = useState<EngineFabricProfile>("balanced");
  const [report, setReport] = useState<EngineFabricReport | null>(null);
  const [selectedBackend, setSelectedBackend] = useState("ollama");
  const [model, setModel] = useState("");
  const [prompt, setPrompt] = useState("");
  const [maxTokens, setMaxTokens] = useState("256");
  const [temperature, setTemperature] = useState("0.7");
  const [result, setResult] = useState<EngineFabricChatResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");

  const refresh = async (nextProfile = profile) => {
    setLoading(true);
    setError("");
    try {
      const next = await axiomApi.engineBackends(nextProfile);
      setReport(next);
      setSelectedBackend((current) => {
        const existing = next.backends.find((item) => item.id === current && item.supports_chat && item.status === "ready");
        if (existing) return current;
        const recommended = next.backends.find((item) => item.id === next.recommendation.backend_id && item.supports_chat);
        const firstReady = next.backends.find((item) => item.supports_chat && item.status === "ready");
        return recommended?.id || firstReady?.id || "ollama";
      });
      const backend = next.backends.find((item) => item.id === selectedBackend);
      const preferred = next.backends.find((item) => item.id === next.recommendation.backend_id);
      const active = backend?.supports_chat ? backend : preferred;
      if (active && active.supports_chat && active.models.length > 0) {
        setModel((current) => active.models.includes(current) ? current : active.models[0]);
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Local engine discovery could not be completed.");
      setReport(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void refresh("balanced"); }, []);

  const selected = report?.backends.find((item) => item.id === selectedBackend) ?? null;
  const choices = report?.backends.filter((item) => item.supports_chat) ?? [];

  const run = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setResult(null);
    if (!selected || selected.status !== "ready") {
      setError("Select a local backend whose loopback API is ready.");
      return;
    }
    if (!model.trim()) {
      setError("Enter a model ID reported by this server or the exact model name configured in it.");
      return;
    }
    if (!prompt.trim()) {
      setError("Enter a prompt first.");
      return;
    }
    const tokenLimit = Number(maxTokens);
    const temperatureValue = Number(temperature);
    if (!Number.isInteger(tokenLimit) || tokenLimit < 1 || tokenLimit > 2048) {
      setError("Maximum output tokens must be between 1 and 2,048.");
      return;
    }
    if (!Number.isFinite(temperatureValue) || temperatureValue < 0 || temperatureValue > 2) {
      setError("Temperature must be between 0 and 2.");
      return;
    }
    setRunning(true);
    try {
      const response = await axiomApi.engineBackendChat({
        backend_id: selected.id as EngineFabricChatResult["backend_id"],
        model: model.trim(),
        messages: [{ role: "user", content: prompt }],
        max_new_tokens: tokenLimit,
        temperature: temperatureValue,
      });
      setResult(response);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Local backend generation failed.");
    } finally {
      setRunning(false);
    }
  };

  return <section className="surface local-inference-panel" aria-labelledby="engine-fabric-title">
    <div className="surface-head">
      <div>
        <p className="surface-eyebrow">AXIOM ENGINE FABRIC · LOCAL ROUTING</p>
        <h2 id="engine-fabric-title">Choose the right local engine</h2>
      </div>
      <button type="button" className="button secondary-button" onClick={() => void refresh()} disabled={loading || running}>
        <RefreshCcw size={14} /> {loading ? "Checking" : "Refresh engines"}
      </button>
    </div>
    <p>AXIOM Native Engine is independent of external runtimes. Fabric compares it with Ollama, llama.cpp, LM Studio, vLLM and llama-cpp-python, then routes a local chat request to a compatible service when you choose one.</p>
    <div className="two-column-grid">
      <label className="field">
        <span className="field-label-row"><span>Optimization profile</span></span>
        <select value={profile} onChange={(event) => { const next = event.target.value as EngineFabricProfile; setProfile(next); void refresh(next); }} disabled={loading || running}>
          {(report?.profiles ?? [{ id: "balanced", label: "Balanced" }, { id: "low-memory", label: "Low memory" }, { id: "throughput", label: "High throughput" }, { id: "easy-setup", label: "Easy setup" }, { id: "portable", label: "Portable / quantized" }, { id: "minimal-daemons", label: "Minimal background services" }]).map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
        </select>
      </label>
      <div className="panel-surface" style={{ padding: 14, alignSelf: "end" }}>
        <p className="surface-eyebrow"><Gauge size={13} style={{ verticalAlign: "middle", marginRight: 5 }} />AXIOM RECOMMENDATION</p>
        <strong>{report?.recommendation.name ?? "Checking local engines…"}</strong>
        <p className="quiet-note">{report?.recommendation.reason ?? "The recommendation is based on local runtime readiness and your selected profile, not synthetic speed claims."}</p>
        {report?.recommendation.status === "setup_required" && <span className="status-pill warning"><i />SETUP REQUIRED</span>}
      </div>
    </div>
    {error && <div className="inline-alert warning" role="alert">{error}</div>}
    <div className="info-grid" aria-label="Local engine inventory">
      {(report?.backends ?? []).map((backend) => <article className="panel-surface" key={backend.id} style={{ padding: 14, minWidth: 0 }}>
        <div className="surface-head">
          <div><p className="surface-eyebrow">{backend.kind === "native" ? "AXIOM-OWNED RUNTIME" : "OPTIONAL LOCAL ADAPTER"}</p><h3>{backend.name}</h3></div>
          <span className={"status-pill " + (backend.status === "ready" ? "success" : "warning")}><i />{formatStatus(backend.status)}</span>
        </div>
        <p className="quiet-note">{backend.endpoint ? backend.endpoint : "In-process · trusted local model roots"}</p>
        <p className="quiet-note">{backend.model_count} model{backend.model_count === 1 ? "" : "s"} discovered{backend.installed ? " · runtime installed" : ""}</p>
        <p><strong>Strengths</strong></p>
        <ul>{backend.strengths.slice(0, 3).map((strength) => <li key={strength}>{strength}</li>)}</ul>
        <p><strong>Trade-offs</strong></p>
        <ul>{backend.tradeoffs.slice(0, 2).map((tradeoff) => <li key={tradeoff}>{tradeoff}</li>)}</ul>
        {backend.error && <p className="quiet-note">{backend.error}</p>}
        {backend.id === report?.recommendation.backend_id && <p className="quiet-note"><Rocket size={13} style={{ verticalAlign: "middle", marginRight: 5 }} />Recommended for this profile</p>}
      </article>)}
    </div>
    <section className="surface" aria-labelledby="fabric-chat-title" style={{ marginTop: 18, padding: 18, border: "1px solid var(--line-strong)", borderRadius: 2, background: "var(--surface)" }}>
      <div className="surface-head"><div><p className="surface-eyebrow">LOCAL EXECUTION · NO CLOUD ROUTING</p><h3 id="fabric-chat-title">Run a local chat</h3></div><span className="quiet-note"><Activity size={14} style={{ verticalAlign: "middle", marginRight: 5 }} />Bounded request</span></div>
      <p className="quiet-note">Only loopback APIs are contacted; AXIOM sends no API keys and does not start services or download models. The Native Engine uses its own trusted model-path form above this adapter section.</p>
      <form onSubmit={(event) => void run(event)}>
        <div className="two-column-grid">
          <label className="field"><span className="field-label-row"><span>External local backend</span></span>
            <select value={selectedBackend} onChange={(event) => { const id = event.target.value; setSelectedBackend(id); setResult(null); const target = report?.backends.find((item) => item.id === id); setModel(target?.models[0] ?? ""); }} disabled={loading || running}>
              {choices.map((item) => <option key={item.id} value={item.id}>{item.name} — {formatStatus(item.status)}</option>)}
            </select>
          </label>
          <label className="field"><span className="field-label-row"><span>Model ID</span></span>
            <input list="axiom-fabric-model-options" value={model} onChange={(event) => setModel(event.target.value)} maxLength={120} required placeholder="Model ID reported by the local server" disabled={!selected || selected.status !== "ready" || running} />
            <datalist id="axiom-fabric-model-options">{(selected?.models ?? []).map((name) => <option key={name} value={name} />)}</datalist>
            <small>{selected?.status === "ready" ? "Choose an ID from this service or enter its exact configured alias." : "Start the selected service and refresh discovery to enable local chat."}</small>
          </label>
        </div>
        <label className="field"><span className="field-label-row"><span>Prompt</span><span>{prompt.length.toLocaleString()} / 12,000 characters</span></span>
          <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} maxLength={12000} rows={4} required placeholder="Ask the selected local model to do something…" />
        </label>
        <div className="two-column-grid">
          <label className="field"><span className="field-label-row"><span>Maximum generated tokens</span></span><input type="number" value={maxTokens} onChange={(event) => setMaxTokens(event.target.value)} min={1} max={2048} step={1} required /></label>
          <label className="field"><span className="field-label-row"><span>Temperature</span></span><input type="number" value={temperature} onChange={(event) => setTemperature(event.target.value)} min={0} max={2} step={0.1} required /></label>
        </div>
        <div className="integration-form-actions">
          <button type="submit" className="button primary-button" disabled={loading || running || !selected || selected.status !== "ready" || !model.trim() || !prompt.trim()}><PlayIcon />{running ? "Generating locally…" : "Run on selected engine"}</button>
          {result && <span className="quiet-note">{result.eval_count ?? "—"} completion tokens · {result.total_duration_ms} ms · {result.backend_name}</span>}
        </div>
      </form>
      {result && <section className="local-inference-result" aria-label="Engine Fabric response"><div className="surface-head"><div><p className="surface-eyebrow">GENERATED LOCALLY</p><h3>{result.model}</h3><small className="quiet-note">{result.backend_name} · {result.generated_at}</small></div><span className="status-pill success"><i />COMPLETED</span></div><pre className="local-inference-output">{result.response || "(The model returned an empty response.)"}</pre></section>}
    </section>
    {report?.scope_note && <p className="quiet-note" style={{ marginTop: 12 }}>{report.scope_note}</p>}
  </section>;
}

function PlayIcon() {
  return <Rocket size={15} aria-hidden="true" />;
}
