import { useState } from "react";
import { Activity, Check, Copy, Play, ShieldCheck } from "lucide-react";
import {
  axiomApi,
  playgroundEndpoints,
  type PlaygroundEndpoint,
} from "../api/client";

const MAX_DISPLAY_CHARS = 100_000;

type QueryResult = {
  endpoint: PlaygroundEndpoint;
  elapsedMs: number;
  response: string;
  truncated: boolean;
};

export default function ApiPlayground() {
  const [endpoint, setEndpoint] = useState<PlaygroundEndpoint>("/api/health");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<QueryResult | null>(null);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  const runRequest = async () => {
    setBusy(true);
    setError("");
    setResult(null);
    setCopied(false);
    const started = performance.now();
    try {
      const payload = await axiomApi.playgroundRead(endpoint);
      const serialized = JSON.stringify(payload, null, 2) ?? "null";
      const truncated = serialized.length > MAX_DISPLAY_CHARS;
      setResult({
        endpoint,
        elapsedMs: Math.round(performance.now() - started),
        response: truncated
          ? `${serialized.slice(0, MAX_DISPLAY_CHARS)}\n\n[Display truncated at ${MAX_DISPLAY_CHARS.toLocaleString()} characters.]`
          : serialized,
        truncated,
      });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The read-only request failed.");
    } finally {
      setBusy(false);
    }
  };

  const copyResponse = async () => {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(result.response);
      setCopied(true);
    } catch {
      setError("Clipboard access was denied by the browser.");
    }
  };

  const selectedDescription = playgroundEndpoints.find((item) => item.path === endpoint)?.description ?? "Choose a read-only endpoint.";

  return (
    <div className="api-playground-layout">
      <section className="surface api-playground-control">
        <div className="surface-head">
          <div>
            <p className="surface-eyebrow">SAFE REQUEST CONSOLE</p>
            <h2>Choose an endpoint</h2>
          </div>
          <ShieldCheck size={18} aria-hidden="true" />
        </div>
        <p className="api-playground-intro">
          Browse a fixed catalog of read-only API endpoints. Requests use the shared 15-second client timeout;
          methods, arbitrary URLs, request bodies, and mutation endpoints are not exposed here.
        </p>
        <label className="field api-playground-field" htmlFor="api-playground-endpoint">
          <span className="field-label-row">Endpoint</span>
          <select
            id="api-playground-endpoint"
            value={endpoint}
            onChange={(event) => setEndpoint(event.target.value as PlaygroundEndpoint)}
          >
            {playgroundEndpoints.map((item) => (
              <option key={item.path} value={item.path}>{item.label} — {item.path}</option>
            ))}
          </select>
        </label>
        <p className="api-playground-description">{selectedDescription}</p>
        <div className="api-playground-facts">
          <div><span>METHOD</span><b>GET only</b></div>
          <div><span>TIMEOUT</span><b>15 seconds</b></div>
          <div><span>DISPLAY LIMIT</span><b>100,000 chars</b></div>
        </div>
        <button type="button" className="button primary-button" onClick={() => void runRequest()} disabled={busy}>
          <Play size={15} /> {busy ? "Requesting…" : "Run read-only request"}
        </button>
        <p className="quiet-note">Responses may include local workspace metadata. Review output before sharing it.</p>
      </section>

      <section className="surface api-playground-response" aria-labelledby="api-playground-response-title">
        <div className="surface-head">
          <div>
            <p className="surface-eyebrow">RESPONSE</p>
            <h2 id="api-playground-response-title">Request output</h2>
          </div>
          {result && <span className="status-pill success"><i />{result.elapsedMs} ms</span>}
        </div>
        {error && <div className="inline-alert warning" role="alert">{error}</div>}
        {busy && <div className="loading-state" role="status"><Activity size={15} /> Waiting for the local API…</div>}
        {!busy && !error && !result && (
          <div className="empty-state api-playground-empty">
            <div className="empty-icon"><Activity size={20} /></div>
            <h3>No response yet</h3>
            <p>Select a safe endpoint and run a GET request to inspect its JSON response.</p>
          </div>
        )}
        {result && (
          <>
            <div className="api-playground-result-meta">
              <code>{result.endpoint}</code>
              <span>{result.truncated ? "Display truncated" : "Complete response"}</span>
              <button type="button" className="text-button" onClick={() => void copyResponse()}>
                {copied ? <Check size={14} /> : <Copy size={14} />} {copied ? "Copied" : "Copy JSON"}
              </button>
            </div>
            <pre className="api-playground-json" tabIndex={0} aria-label="JSON response">{result.response}</pre>
            {result.truncated && <p className="quiet-note">Only the displayed preview is truncated; choose a paginated endpoint to inspect smaller results.</p>}
          </>
        )}
      </section>
    </div>
  );
}
