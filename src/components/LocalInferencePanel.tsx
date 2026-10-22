import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Activity, Play, RefreshCcw } from "lucide-react";
import { axiomApi, type LocalInferenceResult, type LocalInferenceStatus } from "../api/client";
import LocalAxiomEnginePanel from "./LocalAxiomEnginePanel";

export default function LocalInferencePanel() {
  const [status, setStatus] = useState<LocalInferenceStatus | null>(null);
  const [model, setModel] = useState("");
  const [prompt, setPrompt] = useState("");
  const [numPredict, setNumPredict] = useState("256");
  const [temperature, setTemperature] = useState("0.7");
  const [result, setResult] = useState<LocalInferenceResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");

  const refresh = async () => {
    setLoading(true);
    setError("");
    try {
      const next = await axiomApi.inferenceStatus();
      setStatus(next);
      setModel((current) => current && next.models.includes(current) ? current : next.models[0] || current);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Local inference status is unavailable.");
      setStatus(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void refresh(); }, []);

  const run = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setResult(null);
    if (!model.trim()) { setError("Enter the name of a model that is already available in Ollama."); return; }
    if (!prompt.trim()) { setError("Enter a prompt first."); return; }
    const tokenLimit = Number(numPredict);
    const temperatureValue = Number(temperature);
    if (!Number.isInteger(tokenLimit) || tokenLimit < 1 || tokenLimit > 2048) { setError("Maximum generated tokens must be between 1 and 2048."); return; }
    if (!Number.isFinite(temperatureValue) || temperatureValue < 0 || temperatureValue > 2) { setError("Temperature must be between 0 and 2."); return; }
    setRunning(true);
    try {
      setResult(await axiomApi.runLocalInference({ model: model.trim(), prompt, num_predict: tokenLimit, temperature: temperatureValue }));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Local generation failed.");
    } finally {
      setRunning(false);
    }
  };

  const online = status?.status === "online";
  return <><section className="surface local-inference-panel">
    <div className="surface-head">
      <div>
        <p className="surface-eyebrow">REAL GENERATION · LOOPBACK ONLY</p>
        <h2>Local model inference</h2>
      </div>
      <button type="button" className="button secondary-button" onClick={() => void refresh()} disabled={loading || running}>
        <RefreshCcw size={14} /> {loading ? "Checking" : "Check runtime"}
      </button>
    </div>
    <p>Generate text with a model already installed in Ollama. AXIOM sends requests only to <code>127.0.0.1:11434</code>; it does not download models or call a cloud inference API.</p>
    <div className="status-strip" aria-label="Local inference status">
      <div className="status-strip-item">
        <span className={`status-pill ${online ? "success" : "warning"}`}><i />{loading ? "CHECKING" : online ? "OLLAMA ONLINE" : "OLLAMA OFFLINE"}</span>
        <div><b>{online ? `${status?.models.length ?? 0} local models` : "Runtime unavailable"}</b><span>{status?.runtime_installed ? "Ollama executable detected" : "Ollama executable not detected"}</span></div>
      </div>
    </div>
    {!loading && !online && <div className="inline-alert warning" role="status">{status?.error || error || "Start the local Ollama service, then check the runtime again."} Install a model separately, for example <code>ollama pull qwen2.5:0.5b</code>.</div>}
    <form onSubmit={(event) => void run(event)}>
      <label className="field">
        <span className="field-label-row"><span>Model name</span></span>
        <input list="axiom-local-model-options" value={model} onChange={(event) => setModel(event.target.value)} maxLength={120} placeholder="e.g. qwen2.5:0.5b" autoComplete="off" />
        <datalist id="axiom-local-model-options">{(status?.models || []).map((name) => <option key={name} value={name} />)}</datalist>
        <small>{status?.models.length ? "Suggestions come from the local model inventory." : "Enter an exact model name that has already been pulled locally."}</small>
      </label>
      <label className="field">
        <span className="field-label-row"><span>Prompt</span><span>{prompt.length.toLocaleString()} / 12,000 characters</span></span>
        <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} maxLength={12000} rows={6} required placeholder="Ask your local model to do something…" />
      </label>
      <div className="two-column-grid">
        <label className="field"><span className="field-label-row"><span>Maximum generated tokens</span></span><input type="number" min={1} max={2048} step={1} value={numPredict} onChange={(event) => setNumPredict(event.target.value)} required /></label>
        <label className="field"><span className="field-label-row"><span>Temperature</span></span><input type="number" min={0} max={2} step={0.1} value={temperature} onChange={(event) => setTemperature(event.target.value)} required /></label>
      </div>
      <div className="integration-form-actions">
        <button type="submit" className="button primary-button" disabled={!online || loading || running || !model.trim() || !prompt.trim()}><Play size={15} /> {running ? "Generating locally…" : "Run locally"}</button>
        {result && <span className="quiet-note"><Activity size={14} /> {result.eval_count ?? "—"} generated tokens{result.total_duration_ms !== null ? ` · ${result.total_duration_ms} ms` : ""}</span>}
      </div>
    </form>
    {error && <div className="inline-alert warning" role="alert">{error}</div>}
    {result && <section className="local-inference-result" aria-label="Generated response">
      <div className="surface-head"><div><p className="surface-eyebrow">GENERATED ON THIS MACHINE</p><h3>{result.model}</h3></div><span className="status-pill success"><i />COMPLETED</span></div>
      <pre data-testid="local-inference-output" className="local-inference-output">{result.response || "(The model returned an empty response.)"}</pre>
    </section>}
  </section><LocalAxiomEnginePanel /></>;
}
