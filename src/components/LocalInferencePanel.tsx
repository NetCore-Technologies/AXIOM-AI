import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Activity, BarChart3, Play, RefreshCcw } from "lucide-react";
import { axiomApi, type LocalInferenceBenchmark, type LocalInferenceResult, type LocalInferenceStatus } from "../api/client";
import LocalAxiomEnginePanel from "./LocalAxiomEnginePanel";

export default function LocalInferencePanel() {
  const [status, setStatus] = useState<LocalInferenceStatus | null>(null);
  const [model, setModel] = useState("");
  const [prompt, setPrompt] = useState("");
  const [numPredict, setNumPredict] = useState("256");
  const [temperature, setTemperature] = useState("0.7");
  const [result, setResult] = useState<LocalInferenceResult | null>(null);
  const [benchmark, setBenchmark] = useState<LocalInferenceBenchmark | null>(null);
  const [warmupRuns, setWarmupRuns] = useState("1");
  const [benchmarkIterations, setBenchmarkIterations] = useState("3");
  const [concurrency, setConcurrency] = useState("1");
  const [benchmarkBusy, setBenchmarkBusy] = useState(false);
  const [benchmarkError, setBenchmarkError] = useState("");
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

  const benchmarkLocalModel = async () => {
    setBenchmarkError("");
    setBenchmark(null);
    if (!online) { setBenchmarkError("Start the local Ollama runtime and check its status before benchmarking."); return; }
    if (!model.trim()) { setBenchmarkError("Choose an installed local Ollama model."); return; }
    if (!prompt.trim()) { setBenchmarkError("Enter a prompt before benchmarking."); return; }
    const tokenLimit = Number(numPredict);
    const temperatureValue = Number(temperature);
    const warmupCount = Number(warmupRuns);
    const repetitions = Number(benchmarkIterations);
    const parallel = Number(concurrency);
    if (!Number.isInteger(tokenLimit) || tokenLimit < 1 || tokenLimit > 512) {
      setBenchmarkError("Benchmark token limit must be between 1 and 512. Lower the existing generation token setting first.");
      return;
    }
    if (!Number.isFinite(temperatureValue) || temperatureValue < 0 || temperatureValue > 2) {
      setBenchmarkError("Temperature must be between 0 and 2.");
      return;
    }
    if (!Number.isInteger(warmupCount) || warmupCount < 0 || warmupCount > 2) {
      setBenchmarkError("Warm-up generations must be between 0 and 2.");
      return;
    }
    if (!Number.isInteger(repetitions) || repetitions < 1 || repetitions > 10) {
      setBenchmarkError("Measured iterations must be between 1 and 10.");
      return;
    }
    if (!Number.isInteger(parallel) || parallel < 1 || parallel > 4 || repetitions * parallel > 10) {
      setBenchmarkError("Concurrency must be 1–4 and iterations × concurrency must not exceed 10 requests.");
      return;
    }
    setBenchmarkBusy(true);
    try {
      setBenchmark(await axiomApi.runLocalInferenceBenchmark({
        model: model.trim(),
        prompt,
        num_predict: tokenLimit,
        temperature: temperatureValue,
        warmup_runs: warmupCount,
        iterations: repetitions,
        concurrency: parallel,
      }));
    } catch (cause) {
      setBenchmarkError(cause instanceof Error ? cause.message : "The local inference benchmark failed.");
    } finally {
      setBenchmarkBusy(false);
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
    <section className="surface" aria-labelledby="inference-benchmark-title" style={{ marginTop: 18, padding: 18, border: "1px solid var(--line-strong)", borderRadius: 2, background: "var(--surface)" }}>
      <div className="surface-head">
        <div><p className="surface-eyebrow">MEASURED RUNS · LOCAL OLLAMA</p><h3 id="inference-benchmark-title"><BarChart3 size={17} style={{ verticalAlign: "middle", marginRight: 8 }} />Inference benchmark</h3></div>
        <button type="button" className="button primary-button" onClick={() => void benchmarkLocalModel()} disabled={!online || loading || running || benchmarkBusy || !model.trim() || !prompt.trim()}>
          <Activity size={15} /> {benchmarkBusy ? "Measuring local runtime…" : "Benchmark this prompt"}
        </button>
      </div>
      <p className="quiet-note">Uses your selected local model, prompt, output-token limit and temperature. Warm-ups are excluded from reported timings. No result text is returned or saved; runs are bounded to 10 measured generations.</p>
      <div className="two-column-grid">
        <label className="field"><span className="field-label-row"><span>Warm-up generations</span></span><select aria-label="Benchmark warm-up generations" value={warmupRuns} onChange={(event) => setWarmupRuns(event.target.value)} disabled={benchmarkBusy}><option value="0">0</option><option value="1">1</option><option value="2">2</option></select></label>
        <label className="field"><span className="field-label-row"><span>Measured iterations</span></span><select aria-label="Benchmark iterations" value={benchmarkIterations} onChange={(event) => setBenchmarkIterations(event.target.value)} disabled={benchmarkBusy}>{[1,2,3,4,5,6,7,8,9,10].map((count) => <option key={count} value={count}>{count}</option>)}</select></label>
        <label className="field"><span className="field-label-row"><span>Concurrency</span></span><select aria-label="Benchmark concurrency" value={concurrency} onChange={(event) => setConcurrency(event.target.value)} disabled={benchmarkBusy}>{[1,2,3,4].map((count) => <option key={count} value={count}>{count} simultaneous request{count === 1 ? "" : "s"}</option>)}</select></label>
      </div>
      {Number(benchmarkIterations) * Number(concurrency) > 10 && <div className="inline-alert warning" role="status">Reduce iterations or concurrency: the benchmark permits at most 10 measured requests per run.</div>}
      {benchmarkError && <div className="inline-alert warning" role="alert">{benchmarkError}</div>}
      {benchmark && <div className="local-inference-benchmark-result" aria-label="Inference benchmark result" style={{ marginTop: 18 }}>
        <div className="status-strip" aria-label="Benchmark status">
          <div className="status-strip-item"><span className="status-pill success"><i />MEASURED</span><div><b>{benchmark.model}</b><span>{benchmark.configuration.measured_requests} requests · concurrency {benchmark.configuration.concurrency} · {benchmark.configuration.num_predict} max tokens</span></div></div>
        </div>
        <div className="info-grid">
          {[
            { label: "Completion throughput", value: benchmark.measurements.completion_tokens_per_second === null ? "Unavailable" : `${benchmark.measurements.completion_tokens_per_second} tokens/s`, detail: `${benchmark.measurements.total_completion_tokens ?? "Unknown"} completion tokens measured` },
            { label: "Median request latency", value: benchmark.measurements.latency_ms.median === null ? "Unavailable" : `${benchmark.measurements.latency_ms.median} ms`, detail: `P95 ${benchmark.measurements.latency_ms.p95 ?? "—"} ms` },
            { label: "Elapsed wall time", value: `${benchmark.measurements.wall_time_ms} ms`, detail: `${benchmark.measurements.requests_per_second} completed requests/s` },
            { label: "Token-count coverage", value: `${benchmark.measurements.completion_tokens_known}/${benchmark.configuration.measured_requests}`, detail: "Responses with runtime token counts" },
          ].map((metric) => <div className="panel-surface" key={metric.label} style={{ padding: 14, minWidth: 0 }}><p className="surface-eyebrow">{metric.label}</p><strong style={{ display: "block", fontSize: 21, margin: "8px 0", overflowWrap: "anywhere" }}>{metric.value}</strong><p className="quiet-note">{metric.detail}</p></div>)}
        </div>
        <div style={{ overflowX: "auto", marginTop: 14 }}>
          <table className="data-table" aria-label="Per-request benchmark timings">
            <thead><tr><th>Request</th><th>Latency</th><th>Prompt tokens</th><th>Completion tokens</th><th>Finished</th></tr></thead>
            <tbody>{benchmark.measurements.requests.map((request, index) => <tr key={index}><td>{index + 1}</td><td>{request.latency_ms} ms</td><td>{request.prompt_tokens ?? "—"}</td><td>{request.completion_tokens ?? "—"}</td><td>{request.done ? "Yes" : "No"}</td></tr>)}</tbody>
          </table>
        </div>
        <p className="quiet-note" style={{ marginTop: 12 }}>{benchmark.scope_note}</p>
      </div>}
    </section>
  </section><LocalAxiomEnginePanel /></>;
}
