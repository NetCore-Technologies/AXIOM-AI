import { useEffect, useState, type FormEvent } from "react";
import { Activity, Cpu, Play, RefreshCcw, Unplug } from "lucide-react";
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
  const [unloading, setUnloading] = useState(false);
  const [lifecycleNotice, setLifecycleNotice] = useState("");
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

  const unload = async () => {
    setUnloading(true);
    setError("");
    setLifecycleNotice("");
    try {
      const outcome = await axiomApi.unloadAxiomEngine();
      setResult(null);
      setLifecycleNotice(outcome.unloaded
        ? "AXIOM released its loaded model and tokenizer references. Framework or OS allocators may retain reserved memory."
        : "No AXIOM model was loaded; the engine state is already clear.");
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The local model could not be unloaded.");
    } finally {
      setUnloading(false);
    }
  };

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
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button type="button" className="button secondary-button" onClick={() => void refresh()} disabled={loading || running || unloading}><RefreshCcw size={14} /> {loading ? "Checking" : "Check engine"}</button>
        {status?.loaded && <button type="button" className="button secondary-button" onClick={() => void unload()} disabled={loading || running || unloading}><Unplug size={14} /> {unloading ? "Unloading…" : "Unload model"}</button>}
      </div>
    </div>
    <p>AXIOM Native Engine runs its own PyTorch Llama/Mistral forward pass and autoregressive KV-cache decoder, including RMSNorm, RoPE, grouped-query attention and LoRA deltas. Tokenization uses the local tokenizer.json; weights are loaded from local floating-point safetensors. This panel does not call Transformers model.generate or Ollama. Weights must already exist on this computer; model downloads and training are separate workflows.</p>
    <div className="status-strip" aria-label="AXIOM Engine status">
      <div className="status-strip-item">
        <span className={`status-pill ${status?.ready ? "success" : "warning"}`}><i />{loading ? "CHECKING" : status?.ready ? "ENGINE READY" : "SETUP REQUIRED"}</span>
        <div><b>{status?.loaded ? `Loaded: ${status.architecture || "local model"}` : "Direct Transformers runtime"}</b><span>{status?.setup_note || error || "Checking local PyTorch and Transformers availability."}</span></div>
      </div>
    </div>
    {status && !status.ready && <div className="inline-alert warning" role="status">{status.setup_note}</div>}
    {lifecycleNotice && <div className="inline-alert success" role="status">{lifecycleNotice}</div>}
    <form onSubmit={(event) => void run(event)}>
      <label className="field">
        <span className="field-label-row"><span>Local Llama / Transformers model directory</span></span>
        <input value={modelPath} onChange={(event) => setModelPath(event.target.value)} required maxLength={4096} placeholder="/home/user/models/my-llama-model" autoComplete="off" />
        <small>Existing Llama/Mistral directory with config.json, tokenizer.json and model.safetensors (or the safetensors shard index). GGUF, quantized formats and pickle .bin weights are not supported by this native execution path. Paths must stay inside a trusted root; set AXIOM_MODEL_ROOTS for additional locations.</small>
      </label>
      <label className="field">
        <span className="field-label-row"><span>Optional LoRA adapter directory</span></span>
        <input value={adapterPath} onChange={(event) => setAdapterPath(event.target.value)} maxLength={4096} placeholder="/home/user/runs/my-lora-adapter" autoComplete="off" />
        <small>Use a standard bias-free CAUSAL_LM LoRA output with adapter_config.json and adapter_model.safetensors. Unsupported adapter options are rejected rather than silently ignored.</small>
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
