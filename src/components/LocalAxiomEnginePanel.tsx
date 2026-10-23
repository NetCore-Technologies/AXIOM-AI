import { useEffect, useRef, useState, type FormEvent } from "react";
import { Activity, Cpu, Play, RefreshCcw, Unplug } from "lucide-react";
import { axiomApi, type AxiomEngineAdapterCompatibility, type AxiomEngineAssets, type AxiomEngineResult, type AxiomEngineStatus, type AxiomEngineStreamEvent } from "../api/client";

export default function LocalAxiomEnginePanel() {
  const [status, setStatus] = useState<AxiomEngineStatus | null>(null);
  const [assets, setAssets] = useState<AxiomEngineAssets | null>(null);
  const [adapterCompatibility, setAdapterCompatibility] = useState<AxiomEngineAdapterCompatibility | null>(null);
  const [checkingAdapter, setCheckingAdapter] = useState(false);
  const [modelPath, setModelPath] = useState("");
  const [selectedModelPath, setSelectedModelPath] = useState("");
  const [adapterPath, setAdapterPath] = useState("");
  const [selectedAdapterPath, setSelectedAdapterPath] = useState("");
  const [prompt, setPrompt] = useState("");
  const [maxNewTokens, setMaxNewTokens] = useState("256");
  const [temperature, setTemperature] = useState("0.7");
  const [result, setResult] = useState<AxiomEngineResult | null>(null);
  const [streamResponse, setStreamResponse] = useState("");
  const [streamTokenCount, setStreamTokenCount] = useState(0);
  const activeStreamRef = useRef<AbortController | null>(null);
  const streamTokenCountRef = useRef(0);
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
      setError(cause instanceof Error ? cause.message : "AXIOM Native Engine status is unavailable.");
    }
    try {
      setAssets(await axiomApi.axiomEngineModels());
    } catch {
      // Manual trusted-root path entry remains available if discovery is unavailable.
      setAssets(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
    return () => activeStreamRef.current?.abort();
  }, []);

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

  const checkAdapterCompatibility = async () => {
    if (!modelPath.trim() || !adapterPath.trim()) {
      setError("Select both a native base model and a LoRA adapter before checking compatibility.");
      return;
    }
    setCheckingAdapter(true);
    setError("");
    setAdapterCompatibility(null);
    try {
      setAdapterCompatibility(await axiomApi.checkAxiomEngineAdapterCompatibility({
        model_path: modelPath.trim(),
        adapter_path: adapterPath.trim(),
      }));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Adapter compatibility preflight failed.");
    } finally {
      setCheckingAdapter(false);
    }
  };

  const run = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setLifecycleNotice("");
    setResult(null);
    setStreamResponse("");
    setStreamTokenCount(0);
    streamTokenCountRef.current = 0;
    const tokenLimit = Number(maxNewTokens);
    const temp = Number(temperature);
    if (!modelPath.trim()) { setError("Choose a discovered native model or enter a trusted local Llama/Mistral model path."); return; }
    if (!prompt.trim()) { setError("Enter a prompt first."); return; }
    if (!Number.isInteger(tokenLimit) || tokenLimit < 1 || tokenLimit > 2048) { setError("Maximum generated tokens must be between 1 and 2048."); return; }
    if (!Number.isFinite(temp) || temp < 0 || temp > 2) { setError("Temperature must be between 0 and 2."); return; }
    const controller = new AbortController();
    activeStreamRef.current = controller;
    setRunning(true);
    try {
      const completed = await axiomApi.streamAxiomEngine({
        model_path: modelPath.trim(),
        adapter_path: adapterPath.trim() || undefined,
        prompt,
        max_new_tokens: tokenLimit,
        temperature: temp,
      }, (event: AxiomEngineStreamEvent) => {
        if (event.type === "token") {
          streamTokenCountRef.current = event.completion_tokens;
          setStreamTokenCount(event.completion_tokens);
          setStreamResponse(event.response);
        } else if (event.type === "complete") {
          streamTokenCountRef.current = event.result.completion_tokens;
          setStreamTokenCount(event.result.completion_tokens);
          setStreamResponse(event.result.response);
        }
      }, controller.signal);
      setResult(completed);
      void refresh();
    } catch (cause) {
      if (controller.signal.aborted) {
        setError(`Generation cancelled after ${streamTokenCountRef.current} token(s). Partial output remains visible.`);
      } else {
        setError(cause instanceof Error ? cause.message : "AXIOM Native Engine generation failed.");
      }
    } finally {
      if (activeStreamRef.current === controller) activeStreamRef.current = null;
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
        <div><b>{status?.loaded ? `Loaded: ${status.architecture || "local model"}` : "AXIOM-native decoder ready"}</b><span>{status?.setup_note || error || "Checking local PyTorch and Transformers availability."}</span></div>
      </div>
    </div>
    {status && !status.ready && <div className="inline-alert warning" role="status">{status.setup_note}</div>}
    {lifecycleNotice && <div className="inline-alert success" role="status">{lifecycleNotice}</div>}
    <form onSubmit={(event) => void run(event)}>
      <label className="field">
        <span className="field-label-row"><span>Discovered native model</span><span>{assets?.models.length ?? 0} found</span></span>
        <select aria-label="Select discovered native model" value={selectedModelPath} onChange={(event) => { setSelectedModelPath(event.target.value); if (event.target.value) setModelPath(event.target.value); }}>
          <option value="">{assets?.models.length ? "Choose a discovered model or enter a path below" : "No supported local models discovered"}</option>
          {(assets?.models ?? []).map((model) => <option key={model.path} value={model.path}>{model.name} · {model.model_type} · {model.weight_format}</option>)}
        </select>
        <small>{assets?.scope_note ?? "Model discovery is unavailable; the API still accepts validated paths under trusted roots."}</small>
      </label>
      <label className="field">
        <span className="field-label-row"><span>Local Llama / Mistral model directory</span></span>
        <input value={modelPath} onChange={(event) => { setModelPath(event.target.value); if (event.target.value !== selectedModelPath) setSelectedModelPath(""); setAdapterCompatibility(null); }} required maxLength={4096} placeholder="/home/user/models/my-llama-model" autoComplete="off" />
        <small>Existing directory with config.json, tokenizer.json and model.safetensors (or the safetensors shard index). GGUF, quantized formats and pickle .bin weights are not supported by this native path. Paths must match a directory discovered under a trusted root; set AXIOM_MODEL_ROOTS for additional locations.</small>
      </label>
      <label className="field">
        <span className="field-label-row"><span>Discovered LoRA adapter (optional)</span><span>{assets?.adapters.length ?? 0} found</span></span>
        <select aria-label="Select discovered LoRA adapter" value={selectedAdapterPath} onChange={(event) => { setSelectedAdapterPath(event.target.value); if (event.target.value) setAdapterPath(event.target.value); setAdapterCompatibility(null); }}>
          <option value="">No adapter</option>
          {(assets?.adapters ?? []).map((adapter) => <option key={adapter.path} value={adapter.path}>{adapter.name} · {adapter.weight_format}</option>)}
        </select>
      </label>
      <label className="field">
        <span className="field-label-row"><span>Optional LoRA adapter directory</span></span>
        <input value={adapterPath} onChange={(event) => { setAdapterPath(event.target.value); if (event.target.value !== selectedAdapterPath) setSelectedAdapterPath(""); setAdapterCompatibility(null); }} maxLength={4096} placeholder="/home/user/runs/my-lora-adapter" autoComplete="off" />
        <small>Use a standard bias-free CAUSAL_LM adapter with adapter_config.json and adapter_model.safetensors. Compatibility is checked during model loading; unsupported adapter options are rejected.</small>
      </label>
      <div className="integration-form-actions">
        <button type="button" className="button secondary-button" onClick={() => void checkAdapterCompatibility()} disabled={checkingAdapter || running || !modelPath.trim() || !adapterPath.trim()}>
          {checkingAdapter ? "Checking adapter…" : "Check adapter compatibility"}
        </button>
      </div>
      {adapterCompatibility && <section className="panel-surface" aria-label="LoRA device compatibility report" style={{ padding: 14, marginBottom: 14 }}>
        <div className="surface-head">
          <div><p className="surface-eyebrow">NATIVE ADAPTER PREFLIGHT</p><h3>{adapterCompatibility.structurally_compatible ? "Adapter structure supported" : "Adapter incompatible"}</h3></div>
          <span className={"status-pill " + (adapterCompatibility.structurally_compatible ? "success" : "warning")}>{adapterCompatibility.structurally_compatible ? "STRUCTURE OK" : "ISSUES FOUND"}</span>
        </div>
        <p className="quiet-note">{adapterCompatibility.adapter_tensor_count} adapter tensors · {adapterCompatibility.checked_layers} model layers checked · rank {adapterCompatibility.adapter.rank ?? "unknown"} · alpha {adapterCompatibility.adapter.alpha ?? "unknown"}</p>
        <div className="two-column-grid">
          {adapterCompatibility.devices.map((device) => <div key={device.name} className="panel-surface" style={{ padding: 10 }}>
            <strong>{device.name}</strong>
            <span className={"status-pill " + (device.compatible ? "success" : device.available ? "warning" : "neutral")}>{device.status.toUpperCase()}</span>
            <p className="quiet-note">{device.reason}</p>
          </div>)}
        </div>
        {adapterCompatibility.issues.length > 0 && <div className="inline-alert warning" role="alert"><strong>Compatibility blockers</strong><ul>{adapterCompatibility.issues.map((issue) => <li key={issue}>{issue}</li>)}</ul></div>}
        <p className="quiet-note">{adapterCompatibility.scope_note}</p>
      </section>}
      <label className="field">
        <span className="field-label-row"><span>AXIOM Native Engine prompt</span><span>{prompt.length.toLocaleString()} / 12,000 characters</span></span>
        <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} maxLength={12000} rows={5} required placeholder="Ask the local model to do something…" />
      </label>
      <div className="two-column-grid">
        <label className="field"><span className="field-label-row"><span>Maximum generated tokens</span></span><input type="number" min={1} max={2048} step={1} value={maxNewTokens} onChange={(event) => setMaxNewTokens(event.target.value)} required /></label>
        <label className="field"><span className="field-label-row"><span>Temperature (0 = deterministic)</span></span><input type="number" min={0} max={2} step={0.1} value={temperature} onChange={(event) => setTemperature(event.target.value)} required /></label>
      </div>
      <div className="integration-form-actions">
        <button type="submit" className="button primary-button" disabled={!status?.ready || loading || running || !modelPath.trim() || !prompt.trim()}><Play size={15} /> {running ? "Generating locally…" : "Run with AXIOM Engine"}</button>
        {running && <button type="button" className="button secondary-button" onClick={() => activeStreamRef.current?.abort()}><Unplug size={14} /> Stop generation</button>}
        {result && <span className="quiet-note"><Activity size={14} /> {result.completion_tokens} tokens · {result.elapsed_ms} ms</span>}
        {!result && streamTokenCount > 0 && <span className="quiet-note"><Activity size={14} /> {streamTokenCount} token(s) streamed</span>}
      </div>
    </form>
    {error && <div className="inline-alert warning" role="alert">{error}</div>}
    {(result || streamResponse) && <section className="local-inference-result" aria-label="AXIOM Engine generated response">
      <div className="surface-head"><div>
        <p className="surface-eyebrow">{result ? `GENERATED ON THIS MACHINE · ${result.architecture}` : running ? "STREAMING TOKEN OUTPUT · LOCAL ONLY" : "PARTIAL LOCAL OUTPUT"}</p>
        <h3>{result ? `${result.model}${result.adapter ? ` + ${result.adapter}` : ""}` : (assets?.models.find((model) => model.path === modelPath)?.name || "AXIOM Native Engine")}</h3>
      </div><span className={`status-pill ${result ? "success" : running ? "warning" : "neutral"}`}><i />{result ? "COMPLETED" : running ? "GENERATING" : "CANCELLED"}</span></div>
      <pre data-testid={result ? "axiom-engine-output" : "axiom-engine-live-output"} className="local-inference-output">{(result ? result.response : streamResponse) || "(The model has not emitted printable text yet.)"}</pre>
      {!result && <p className="quiet-note">Cumulative text snapshots update as the native decoder emits tokens. {streamTokenCount} token(s) received.</p>}
    </section>}
    <p className="quiet-note"><Cpu size={14} /> AXIOM owns this runtime and the LoRA training loop; the underlying pretrained base weights retain their original model licence.</p>
  </section>;
}
