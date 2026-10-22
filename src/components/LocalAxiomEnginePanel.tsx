import { useEffect, useState, type FormEvent } from "react";
import { Activity, Cpu, Play, RefreshCcw } from "lucide-react";
import { axiomApi, type AxiomEngineResult, type AxiomEngineStatus } from "../api/client";

export default function LocalAxiomEnginePanel() {
  const [status, setStatus] = useState<AxiomEngineStatus | null>(null);
  const [modelPath, setModelPath] = useState("");
  const [adapterPath, setAdapterPath] = useState("");
  const [prompt, setPrompt] = useState("");
  const [maxNewTokens, setMaxNewTokens] = useState("256");
  const [temperature, setTemperature] = useState("0.7");
  const [result, setResult] = useState<AxiomEngineResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");

  const refresh = async () => {
    setLoading(true);
    setError("");
    try {
      setStatus(await axiomApi.axiomEngineStatus());
    } catch (cause) {
      setStatus(null);
      setError(cause instanceof Error ? cause.message : "AXIOM Engine status is unavailable.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void refresh(); }, []);

  const run = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setResult(null);
    const tokenLimit = Number(maxNewTokens);
    const temp = Number(temperature);
    if (!modelPath.trim()) { setError("Enter the path to a local Transformers model directory."); return; }
    if (!prompt.trim()) { setError("Enter a prompt first."); return; }
    if (!Number.isInteger(tokenLimit) || tokenLimit < 1 || tokenLimit > 2048) { setError("Maximum generated tokens must be between 1 and 2048."); return; }
    if (!Number.isFinite(temp) || temp < 0 || temp > 2) { setError("Temperature must be between 0 and 2."); return; }
    setRunning(true);
    try {
      setResult(await axiomApi.runAxiomEngine({
        model_path: modelPath.trim(),
        adapter_path: adapterPath.trim() || undefined,
        prompt,
        max_new_tokens: tokenLimit,
        temperature: temp,
      }));
      void refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "AXIOM Engine generation failed.");
    } finally {
      setRunning(false);
    }
  };

  return <section className="surface axiom-engine-panel" aria-label="AXIOM local engine">
    <div className="surface-head">
      <div><p className="surface-eyebrow">AXIOM ENGINE · DIRECT LOCAL INFERENCE</p><h2>AXIOM Local Engine</h2></div>
      <button type="button" className="button secondary-button" onClick={() => void refresh()} disabled={loading || running}><RefreshCcw size={14} /> {loading ? "Checking" : "Check engine"}</button>
    </div>
    <p>Run a local Llama-architecture or other compatible Transformers causal model directly through AXIOM's own runtime. Ollama is not required for this panel. Model weights must already exist on this computer; AXIOM will not download weights or execute remote model code.</p>
    <div className="status-strip" aria-label="AXIOM Engine status">
      <div className="status-strip-item">
        <span className={`status-pill ${status?.ready ? "success" : "warning"}`}><i />{loading ? "CHECKING" : status?.ready ? "ENGINE READY" : "SETUP REQUIRED"}</span>
        <div><b>{status?.loaded ? `Loaded: ${status.architecture || "local model"}` : "Direct Transformers runtime"}</b><span>{status?.setup_note || error || "Checking local PyTorch and Transformers availability."}</span></div>
      </div>
    </div>
    {status && !status.ready && <div className="inline-alert warning" role="status">{status.setup_note}</div>}
    <form onSubmit={(event) => void run(event)}>
      <label className="field">
        <span className="field-label-row"><span>Local Llama / Transformers model directory</span></span>
        <input value={modelPath} onChange={(event) => setModelPath(event.target.value)} required maxLength={4096} placeholder="/home/user/models/my-llama-model" autoComplete="off" />
        <small>Existing directory with config.json, local weights, and tokenizer files. GGUF files and Ollama tags are not accepted here.</small>
      </label>
      <label className="field">
        <span className="field-label-row"><span>Optional LoRA adapter directory</span></span>
        <input value={adapterPath} onChange={(event) => setAdapterPath(event.target.value)} maxLength={4096} placeholder="/home/user/runs/my-lora-adapter" autoComplete="off" />
        <small>Use the output directory from Training; it must contain adapter_config.json and adapter weights.</small>
      </label>
      <label className="field">
        <span className="field-label-row"><span>Prompt</span><span>{prompt.length.toLocaleString()} / 12,000 characters</span></span>
        <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} maxLength={12000} rows={5} required placeholder="Ask the local model to do something…" />
      </label>
      <div className="two-column-grid">
        <label className="field"><span className="field-label-row"><span>Maximum generated tokens</span></span><input type="number" min={1} max={2048} step={1} value={maxNewTokens} onChange={(event) => setMaxNewTokens(event.target.value)} required /></label>
        <label className="field"><span className="field-label-row"><span>Temperature (0 = deterministic)</span></span><input type="number" min={0} max={2} step={0.1} value={temperature} onChange={(event) => setTemperature(event.target.value)} required /></label>
      </div>
      <div className="integration-form-actions">
        <button type="submit" className="button primary-button" disabled={!status?.ready || loading || running || !modelPath.trim() || !prompt.trim()}><Play size={15} /> {running ? "Generating locally…" : "Run with AXIOM Engine"}</button>
        {result && <span className="quiet-note"><Activity size={14} /> {result.completion_tokens} tokens · {result.elapsed_ms} ms</span>}
      </div>
    </form>
    {error && <div className="inline-alert warning" role="alert">{error}</div>}
    {result && <section className="local-inference-result" aria-label="AXIOM Engine generated response">
      <div className="surface-head"><div><p className="surface-eyebrow">GENERATED ON THIS MACHINE · {result.architecture}</p><h3>{result.model}{result.adapter ? ` + ${result.adapter}` : ""}</h3></div><span className="status-pill success"><i />COMPLETED</span></div>
      <pre data-testid="axiom-engine-output" className="local-inference-output">{result.response || "(The model returned an empty response.)"}</pre>
    </section>}
    <p className="quiet-note"><Cpu size={14} /> AXIOM owns this runtime and the LoRA training loop; the underlying pretrained base weights retain their original model licence.</p>
  </section>;
}
