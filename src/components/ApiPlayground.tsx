import { useState } from "react";
import { axiomApi, playgroundEndpoints, type PlaygroundEndpoint } from "../api/client";

export default function ApiPlayground() {
  const [selected, setSelected] = useState<PlaygroundEndpoint>(
    playgroundEndpoints[0].path,
  );
  const [response, setResponse] = useState<unknown>(null);
  const [hasResponse, setHasResponse] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const endpoint = playgroundEndpoints.find((item) => item.path === selected)
    ?? playgroundEndpoints[0];

  async function runRequest() {
    setLoading(true);
    setError("");
    setHasResponse(false);

    try {
      const result = await axiomApi.playgroundRead(selected);
      setResponse(result);
      setHasResponse(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The API request failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="surface api-playground">
      <div className="surface-head">
        <div>
          <p className="surface-eyebrow">API INSPECTION / ALLOWLISTED GET</p>
          <h2>Choose an endpoint</h2>
        </div>
      </div>

      <p className="quiet-note">
        Requests are restricted to the predefined read-only endpoint allowlist.
        Responses are bounded by the API client's timeout.
      </p>

      <div className="field">
        <label htmlFor="api-endpoint">Endpoint</label>
        <div className="input-shell">
          <select
            id="api-endpoint"
            aria-label="Endpoint"
            value={selected}
            onChange={(event) => {
              setSelected(event.target.value as PlaygroundEndpoint);
              setHasResponse(false);
              setError("");
            }}
          >
            {playgroundEndpoints.map((item) => (
              <option key={item.path} value={item.path}>
                {item.path} — {item.label}
              </option>
            ))}
          </select>
        </div>
        <small>{endpoint.description}</small>
      </div>

      <div className="page-actions">
        <button
          type="button"
          className="button primary-button"
          onClick={() => void runRequest()}
          disabled={loading}
        >
          {loading ? "Requesting…" : "Run read-only request"}
        </button>
      </div>

      {error && <div className="inline-alert danger" role="alert">{error}</div>}

      {loading && <p role="status">Waiting for the local API…</p>}

      {hasResponse && (
        <div>
          <p className="surface-eyebrow">RESPONSE / JSON</p>
          <pre className="api-playground-json">
            {JSON.stringify(response, null, 2)}
          </pre>
        </div>
      )}

      <p className="quiet-note">
        Only allowlisted GET requests are supported. Mutating methods and
        arbitrary endpoint URLs are not exposed.
      </p>
    </section>
  );
}
