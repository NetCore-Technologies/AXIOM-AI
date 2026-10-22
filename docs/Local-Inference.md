# Local inference

AXIOM's first executable inference adapter uses an Ollama service bound to the local machine. The adapter does not download models, start Ollama, or use a cloud inference endpoint. Runtime status and model names are read from `http://127.0.0.1:11434/api/tags`; generation is sent to `http://127.0.0.1:11434/api/generate` with streaming disabled.

## Requirements

1. Install Ollama for your operating system using the official instructions.
2. Start its local service if it is not already running.
3. Pull a model you have sufficient memory to run. A small starting example is:

   ```bash
   ollama pull qwen2.5:0.5b
   ```

Model download is an explicit user command, not an AXIOM side effect. The exact model available depends on your hardware and the models you've downloaded.

## Runtime request traces

The **Runtime** page includes a request history for local generation and benchmark calls. The API returns an `X-Request-ID` header and the response body carries the same identifier, allowing a call to be correlated with its trace. The in-process buffer keeps at most 200 records, newest first. It stores model name, operation, status, durations, token counts when available, bounded benchmark settings, and safe error codes. It does not accept or store prompt bodies, generated response text, credentials, or raw exception messages. Traces are memory-only and are lost when the API process restarts.

Use **Refresh traces** to reload the history, **Export JSON** to download the displayed metadata, and **Clear history** to clear the current process's buffer after explicit confirmation. Clear affects only this process; it does not remove files because trace history is not written to disk. See the runtime diagnostics API routes `GET /api/diagnostics/runtime-traces` and `DELETE /api/diagnostics/runtime-traces`.

## Benchmarking

The Runtime page can run a bounded benchmark against the same local Ollama service. It supports up to two excluded warm-up generations, up to ten measured requests across configurable concurrency, output limits up to 512 tokens per benchmark request, per-request latency statistics, wall time, and completion-token throughput when Ollama supplies token counts. The benchmark neither saves prompts/responses nor returns generated text in its result payload. See the [Inference Benchmarking guide](Inference-Benchmarking.md) for endpoint fields, limits, and measurement caveats.

## CLI

Run commands from the AXIOM environment:

```bash
axiom --no-banner infer status
axiom --no-banner infer models
axiom --no-banner infer run qwen2.5:0.5b --prompt "Explain local inference in one sentence." --num-predict 128
axiom --no-banner infer run qwen2.5:0.5b --prompt-file ./prompt.txt --json
```

Use `axiom --no-banner infer --help` and `axiom --no-banner infer run --help` for all options. The prompt limit is 12,000 characters, generation is bounded to 1–2,048 tokens, and the request timeout is finite.

## GUI

Start AXIOM's local API and open **Runtime** in Control Center. The **Local model inference** panel checks the local Ollama API, suggests model names reported by Ollama, and sends prompts through AXIOM's inference API. Generation can take time on CPU; the request timeout is bounded to five minutes. Output is displayed in the GUI and is not saved to workspace logs by this feature.

## Scope and limitations

- This is real text generation when the local Ollama API and chosen model are available; it is not a simulated output or a planning report.
- Runtime discovery remains a separate passive inventory and is not treated as proof of an active connection.
- AXIOM connects only to the constant IPv4 loopback endpoint `127.0.0.1:11434` and explicitly disables proxy use for these requests.
- This first adapter does not execute training/fine-tuning, download models, or automatically start/stop external runtime services. Those remain separate capabilities.
- If the service is offline or the model name is unknown, AXIOM reports the failure instead of substituting a fake response.
