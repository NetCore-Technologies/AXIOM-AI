import { useMemo, useState } from "react";

type Tool = {
  id: string;
  title: string;
  kind: string;
  description: string;
  category: string;
  param?: number;
};

type RawTool = readonly [title: string, kind: string, description: string, param?: number];

type ToolkitInput = { a: string; b: string; c: string; textA: string; textB: string };
type JsonRecord = Record<string, unknown>;

const CATEGORIES: { name: string; tools: RawTool[] }[] = [
  { name: "Model sizing", tools: [
    ["FP16 weight footprint", "weight-size", "Estimate decimal GB for a parameter count in billions at 16 bits per parameter. Enter parameter count in A.", 16],
    ["BF16 weight footprint", "weight-size", "Estimate BF16 weights in GB; actual runtime memory is higher than weights alone.", 16],
    ["FP32 weight footprint", "weight-size", "Estimate FP32 weights in GB for a model with A billion parameters.", 32],
    ["8-bit weight footprint", "weight-size", "Estimate 8-bit weight storage before scales and metadata.", 8],
    ["6-bit weight footprint", "weight-size", "Estimate 6-bit packed weight storage before format overhead.", 6],
    ["5-bit weight footprint", "weight-size", "Estimate 5-bit packed weight storage before format overhead.", 5],
    ["4-bit weight footprint", "weight-size", "Estimate 4-bit packed weight storage before format overhead.", 4],
    ["3-bit weight footprint", "weight-size", "Estimate 3-bit packed weight storage before format overhead.", 3],
    ["2-bit weight footprint", "weight-size", "Estimate 2-bit packed weight storage before format overhead.", 2],
    ["KV-cache footprint", "kv-cache", "Estimate a decoder KV cache. A=layers, B=context tokens, C=KV heads; text B may contain head dimension and bytes/value as comma-separated numbers.", 2],
  ]},
  { name: "Quantization lab", tools: [
    ["Q8 versus FP16 savings", "quant-savings", "Compare estimated Q8 weights with FP16. A=model parameters in billions.", 8],
    ["Q6 versus FP16 savings", "quant-savings", "Compare estimated Q6 weights with FP16. A=model parameters in billions.", 6],
    ["Q5 versus FP16 savings", "quant-savings", "Compare estimated Q5 weights with FP16. A=model parameters in billions.", 5],
    ["Q4 versus FP16 savings", "quant-savings", "Compare estimated Q4 weights with FP16. A=model parameters in billions.", 4],
    ["Q3 versus FP16 savings", "quant-savings", "Compare estimated Q3 weights with FP16. A=model parameters in billions.", 3],
    ["Q2 versus FP16 savings", "quant-savings", "Compare estimated Q2 weights with FP16. A=model parameters in billions.", 2],
    ["Compare two bit widths", "quant-compare", "A=parameters in billions, B=source bits per parameter, C=target bits per parameter.", 4],
    ["Quantized model memory fit", "memory-fit", "A=parameters in billions, B=available GB, C=runtime overhead percentage; this is a weight-only estimate.", 4],
    ["Model shard planner", "shard-count", "A=estimated file size in GB, B=target shard size in GB.", 4],
    ["Compression ratio", "compression-ratio", "A=original size in GB, B=compressed size in GB.", 4],
  ]},
  { name: "Training planner", tools: [
    ["Effective batch size", "effective-batch", "A=micro-batch per device, B=gradient accumulation steps, C=device count.", 1],
    ["Steps per epoch", "steps-epoch", "A=training examples, B=per-device batch size, C=device count.", 1],
    ["Total optimizer steps", "total-steps", "A=training examples, B=effective batch size, C=epochs.", 1],
    ["Tokens processed", "tokens-seen", "A=optimizer steps, B=effective batch size, C=sequence length.", 1],
    ["Warmup step count", "warmup-steps", "A=total training steps, B=warmup percentage (0–100).", 1],
    ["Training duration", "training-duration", "A=training steps, B=seconds per step, C=checkpoint overhead percentage.", 1],
    ["Linear learning-rate decay", "linear-lr", "A=initial learning rate, B=current step, C=total steps.", 1],
    ["Cosine learning-rate schedule", "cosine-lr", "A=peak learning rate, B=current step, C=total steps.", 1],
    ["Optimizer-state memory", "optimizer-memory", "A=parameter count in billions, B=bytes per parameter for weights, C=state copies (for example 2 for Adam moments).", 1],
    ["Checkpoint storage budget", "checkpoint-storage", "A=checkpoint GB, B=number of checkpoints, C=extra percentage for temporary writes.", 1],
  ]},
  { name: "Dataset quality", tools: [
    ["JSON record summary", "json-stats", "Paste a JSON array, object, or JSONL into Text A. Reports aggregate shape only.", 1],
    ["JSONL validity check", "jsonl-validate", "Paste JSONL into Text A. Reports malformed lines and non-object records without echoing record content.", 1],
    ["Duplicate-line detector", "duplicate-lines", "Paste one record per line into Text A. Returns duplicate counts, not duplicate values.", 1],
    ["Schema difference", "schema-diff", "Paste training samples in Text A and validation samples in Text B (JSON array or JSONL).", 1],
    ["Null-rate by field", "null-rate", "Paste a JSON array or JSONL in Text A and the field name in Text B.", 1],
    ["Text length profile", "text-stats", "Paste text or one record per line in Text A. Produces aggregate character, word, line, and approximate-token counts.", 1],
    ["Dataset split calculator", "split-size", "A=total rows, B=train fraction (0–1), C=validation fraction (0–1); remainder is test.", 1],
    ["Class balance report", "class-balance", "Paste JSON array/JSONL in Text A and label-field name in Text B. Values are summarized as counts.", 1],
    ["Train/evaluation leakage check", "leakage", "Paste training rows in Text A and evaluation rows in Text B. Checks exact normalized-line overlap only.", 1],
    ["CSV preview", "csv-preview", "Paste CSV into Text A. Returns only the header and first few rows; do not paste secrets.", 1],
  ]},
  { name: "Evaluation", tools: [
    ["Exact-match score", "exact-match", "Paste references one per line in Text A and predictions one per line in Text B.", 1],
    ["Token precision / recall / F1", "token-f1", "Compare reference text in Text A against predicted text in Text B using whitespace-token overlap.", 1],
    ["Token Jaccard similarity", "jaccard", "Compare text A and text B with a set-based token similarity score.", 1],
    ["Wilson score interval", "wilson", "A=successful cases, B=total cases. Computes a 95% Wilson interval for a binomial proportion.", 1],
    ["Regression threshold gate", "threshold", "A=measured score, B=minimum acceptable score. Equality passes.", 1],
    ["Pass-rate calculator", "pass-rate", "Paste one numeric score per line in Text A and threshold in A. Reports aggregate pass rate.", 1],
    ["Relative improvement", "relative-change", "A=baseline score, B=new score. Positive means the new score is higher.", 1],
    ["Absolute score difference", "absolute-difference", "A=baseline score, B=new score.", 1],
    ["Mean absolute error", "mae", "Paste actual numeric values in Text A and predictions in Text B, comma or newline separated.", 1],
    ["Root mean squared error", "rmse", "Paste actual numeric values in Text A and predictions in Text B, comma or newline separated.", 1],
  ]},
  { name: "Inference operations", tools: [
    ["Approximate prompt tokens", "token-estimate", "Paste prompt text in Text A. This is a rough character/4 estimate, not a tokenizer result.", 1],
    ["Context-window budget", "context-budget", "A=context tokens, B=prompt tokens, C=reserved output tokens.", 1],
    ["Measured tokens per second", "throughput", "A=generated tokens, B=elapsed seconds.", 1],
    ["Latency percentile summary", "percentiles", "Paste latency measurements in milliseconds into Text A, separated by comma or newline.", 95],
    ["Request timeout budget", "timeout-budget", "A=connect timeout ms, B=first-token timeout ms, C=stream idle timeout ms.", 1],
    ["Parallel request slots", "parallel-slots", "A=available memory GB, B=estimated extra memory per in-flight request GB.", 1],
    ["Stop-sequence checker", "stop-check", "Paste generated output in Text A and one stop sequence per line in Text B.", 1],
    ["Prompt template renderer", "template-render", "Paste a template with {{key}} placeholders in Text A and a JSON object of replacements in Text B.", 1],
    ["Output truncation estimator", "truncation", "A=context limit tokens, B=prompt tokens, C=requested output tokens.", 1],
    ["Request latency summary", "latency-summary", "Paste latency samples in milliseconds into Text A. Summarizes min, median, p95, and max.", 1],
  ]},
  { name: "Hardware planning", tools: [
    ["Memory fit with reserve", "memory-fit", "A=model parameters in billions, B=physical memory GB, C=reserve percentage. Uses the selected tool's bit width.", 4],
    ["Available memory after reserve", "memory-reserve", "A=installed memory GB, B=reserve percentage for OS and other workloads.", 1],
    ["CPU worker recommendation", "cpu-workers", "A=logical CPU cores, B=cores reserved for other work.", 1],
    ["Bandwidth-limited token rate", "bandwidth-rate", "A=memory bandwidth GB/s, B=bytes read per generated token in GB-equivalent bytes.", 1],
    ["Unified-memory allocation", "unified-memory", "A=unified memory GB, B=usable percentage, C=model footprint GB.", 1],
    ["PCIe transfer time", "pcie-time", "A=transfer size GB, B=effective transfer rate GB/s.", 1],
    ["Thermal headroom", "thermal-headroom", "A=thermal limit °C, B=current temperature °C.", 1],
    ["Throughput per watt", "performance-per-watt", "A=measured tokens per second, B=measured watts.", 1],
    ["Estimate uncertainty band", "uncertainty", "A=estimated value, B=uncertainty percentage. Reported range is illustrative, not a confidence interval.", 1],
    ["Power budget fit", "power-budget", "A=device power budget W, B=other system load W, C=accelerator load W.", 1],
  ]},
  { name: "Security and privacy", tools: [
    ["Redact likely secrets", "redact", "Paste text in Text A. Redacts common API-token, password, bearer, and private-key patterns locally.", 1],
    ["PII heuristic scan", "pii-scan", "Paste text in Text A. Returns counts only for email/phone-like patterns; false positives are possible.", 1],
    ["Path traversal guard", "path-check", "Paste a relative path in Text A. Checks lexical traversal/absolute-path hazards only; filesystem symlinks need server-side checks.", 1],
    ["URL safety review", "url-check", "Paste a URL in Text A. Flags non-HTTPS, embedded credentials, and unusual schemes.", 1],
    ["Default-deny tool policy", "tool-policy", "Paste a JSON array of tools with name and optional allowed/read/write/network/execute fields in Text A.", 1],
    ["Environment-file redactor", "env-redact", "Paste environment-style KEY=value lines in Text A. Sensitive values are masked before display.", 1],
    ["Secret-pattern scanner", "secret-scan", "Paste text in Text A. Reports types and counts of likely secret patterns without echoing matched values.", 1],
    ["Prompt-injection heuristic", "injection-scan", "Paste text in Text A. Flags common override/exfiltration phrases; this is not a security boundary.", 1],
    ["Input size bound", "bounded-input", "Paste text in Text A and maximum allowed characters in A. Reports accepted/truncated counts.", 1],
    ["Local-address validator", "local-address", "Paste a local host or URL in Text A. Reports whether it appears loopback/private; not a network probe.", 1],
  ]},
  { name: "Workflow utilities", tools: [
    ["Workflow graph validation", "dag-validate", "Paste JSON in Text A with nodes and edges arrays, for example: nodes are a and b; edge is a to b. Validates references and cycles.", 1],
    ["Workflow topological order", "dag-order", "Use the JSON nodes/edges format described in Workflow graph validation.", 1],
    ["Missing workflow inputs", "missing-inputs", "Paste JSON in Text A with required and provided string arrays.", 1],
    ["Workflow cycle detector", "cycle-check", "Paste JSON workflow nodes and edges in Text A. Reports whether a directed cycle exists.", 1],
    ["Reproducibility manifest", "manifest", "Paste JSON metadata in Text A. Produces a bounded schema-versioned manifest without file contents.", 1],
    ["Seed manifest generator", "seed-manifest", "A=random seed integer; Text A=short experiment/configuration description.", 1],
    ["Artifact name normalizer", "artifact-name", "Paste an experiment/artifact label in Text A. Creates a portable slug.", 1],
    ["Output path review", "output-path", "Paste a proposed relative output path in Text A. Rejects absolute paths and parent traversal.", 1],
    ["Workflow step budget", "step-budget", "A=planned steps, B=configured maximum steps.", 1],
    ["Dependency order check", "dependency-order", "Paste JSON node/edge data in Text A. Checks that all dependencies are declared.", 1],
  ]},
  { name: "API and operations", tools: [
    ["Retry schedule", "retry-schedule", "A=max attempts, B=initial delay ms, C=maximum delay ms. Returns capped exponential delays.", 1],
    ["Combined timeout budget", "timeout-sum", "Paste stage timeout values (milliseconds) into Text A, comma or newline separated.", 1],
    ["Pagination range", "pagination", "A=total records, B=offset, C=limit. Computes a bounded page and next offset.", 1],
    ["Request ID validator", "request-id", "Paste a UUID-like request identifier in Text A.", 1],
    ["JSON formatter", "json-format", "Paste JSON into Text A. Formats valid JSON and reports parse errors without echoing content.", 1],
    ["Query-string encoder", "query-encode", "Paste a query string or plain value into Text A. Returns URL-encoded output.", 1],
    ["Read-only curl builder", "curl-safe", "Paste an HTTPS URL in Text A. Builds a GET-only curl command without credentials.", 1],
    ["API response-envelope check", "envelope-check", "Paste JSON response data in Text A. Checks for common status/data/error/request_id fields.", 1],
    ["Rate-limit capacity", "rate-budget", "A=requests per second, B=window seconds, C=expected requests.", 1],
    ["Exponential backoff schedule", "backoff", "A=retry attempt count, B=base delay ms, C=maximum delay ms.", 1],
  ]},
  { name: "Prompt engineering", tools: [
    ["System prompt scaffold", "system-prompt", "Text A=task; Text B=constraints. Builds a concise editable system-prompt scaffold.", 1],
    ["Conversation role validator", "role-check", "Paste JSON messages with role/content fields in Text A.", 1],
    ["Prompt change summary", "prompt-diff", "Paste the old prompt in Text A and new prompt in Text B.", 1],
    ["Few-shot example formatter", "few-shot", "Text A=instructions; Text B=examples, one input => output pair per line.", 1],
    ["Evaluation-case formatter", "test-case-format", "Text A=test input; Text B=expected behavior. Creates a structured JSON case.", 1],
    ["Scoring rubric builder", "rubric", "Text A=task description; creates a transparent 0–4 evaluation rubric template.", 1],
    ["JSON schema example", "schema-sample", "Paste a JSON Schema-like object in Text A; creates a minimal example from common property types.", 1],
    ["Instruction-density report", "instruction-density", "Paste prompt text in Text A. Counts lines and imperative/constraint cues as a heuristic.", 1],
    ["Prompt token budget", "prompt-budget", "A=context limit, B=reserved output tokens, C=safety margin tokens.", 1],
    ["Prompt variant planner", "prompt-variants", "Text A=base prompt; Text B=goal. Creates three structured variants for human review.", 1],
  ]},
  { name: "Release engineering", tools: [
    ["Semantic version parser", "semver", "Paste a semantic version in Text A, for example 1.2.3-beta.1.", 1],
    ["Version compatibility check", "compatibility", "Text A=installed version and Text B=required version. Checks major-version compatibility only.", 1],
    ["SHA-256 digest", "sha256", "Text A=content to hash locally in the browser; large file hashing is not provided by this text tool.", 1],
    ["Manifest schema check", "manifest-check", "Paste a JSON manifest in Text A and check basic required metadata.", 1],
    ["Platform target comparison", "platform-check", "Text A=target platform, Text B=current platform label. Compares normalized labels.", 1],
    ["Dependency-spec sanity check", "dependency-check", "Paste a dependency spec in Text A. Performs syntax-level review only; it does not resolve packages.", 1],
    ["Changelog section organizer", "changelog", "Paste release notes in Text A. Groups bullet lines under Added/Changed/Fixed/Security headings.", 1],
    ["Port-range validator", "port-check", "Enter a port number in A or as Text A. Validates the 1–65535 range.", 1],
    ["Support-text redactor", "support-redact", "Paste diagnostic text in Text A. Removes likely secrets and home-directory path fragments.", 1],
    ["Portable filename normalizer", "filename", "Paste a desired file name in Text A. Produces a conservative cross-platform filename.", 1],
  ]},
];

const TOOLKIT_TOOLS: Tool[] = CATEGORIES.flatMap((category, categoryIndex) =>
  category.tools.map((item, featureIndex) => ({
    id: "T" + String(categoryIndex * 10 + featureIndex + 1).padStart(3, "0"),
    title: item[0],
    kind: item[1],
    description: item[2],
    param: item[3],
    category: category.name,
  })),
);

function num(value: string): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}
function clamp(value: number, low: number, high: number): number {
  return Math.min(high, Math.max(low, value));
}
function fmt(value: number, digits = 3): string {
  if (!Number.isFinite(value)) return "not calculable";
  return Number(value.toFixed(digits)).toLocaleString("en-US");
}
function rec(value: unknown): JsonRecord | null {
  return value !== null && typeof value === "object" && !Array.isArray(value) ? value as JsonRecord : null;
}
function parseRows(source: string): unknown[] {
  const trimmed = source.trim();
  if (!trimmed) return [];
  try {
    const parsed: unknown = JSON.parse(trimmed);
    if (Array.isArray(parsed)) return parsed;
    return [parsed];
  } catch {
    const rows: unknown[] = [];
    for (const line of trimmed.split(/\r?\n/)) {
      if (!line.trim()) continue;
      try { rows.push(JSON.parse(line) as unknown); }
      catch { rows.push(line); }
    }
    return rows;
  }
}
function parseNumbers(source: string): number[] {
  return source.split(/[\s,;]+/).map((value) => value.trim()).filter(Boolean).map(Number).filter((value) => Number.isFinite(value));
}
function percentile(values: number[], p: number): number {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const index = clamp(Math.ceil(clamp(p, 0, 100) / 100 * sorted.length) - 1, 0, sorted.length - 1);
  return sorted[index];
}
function parseCsv(source: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [], cell = "", quoted = false;
  for (let i = 0; i < source.length; i += 1) {
    const char = source[i];
    if (char === '"' && quoted && source[i + 1] === '"') { cell += '"'; i += 1; }
    else if (char === '"') quoted = !quoted;
    else if (char === "," && !quoted) { row.push(cell); cell = ""; }
    else if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && source[i + 1] === "\n") i += 1;
      row.push(cell); rows.push(row); row = []; cell = "";
    } else cell += char;
  }
  if (cell.length || row.length) { row.push(cell); rows.push(row); }
  return rows.filter((item) => item.some((value) => value.length > 0));
}
function redactText(source: string): string {
  return source
    .replace(/-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----/g, "[REDACTED PRIVATE KEY]")
    .replace(/\bBearer\s+[A-Za-z0-9._~+/-]+=*/gi, "Bearer [REDACTED]")
    .replace(/\b(api[_-]?key|access[_-]?token|refresh[_-]?token|password|passwd|secret)\b(\s*[:=]\s*)["']?[^'" \r\n,;}]+/gi, "$1$2[REDACTED]")
    .replace(/\b(gh[pousr]_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{16,}|AKIA[A-Z0-9]{16})\b/g, "[REDACTED TOKEN]");
}
function parseGraph(source: string): { nodes: string[]; edges: [string, string][] } {
  const parsed: unknown = JSON.parse(source);
  const object = rec(parsed);
  if (!object) throw new Error("Graph must be a JSON object.");
  const nodesRaw = Array.isArray(object.nodes) ? object.nodes : [];
  const nodes = nodesRaw.map((item) => typeof item === "string" ? item : String(rec(item)?.id ?? "")).filter(Boolean);
  const edgeRaw = Array.isArray(object.edges) ? object.edges : [];
  const edges: [string, string][] = edgeRaw.map((item) => {
    if (Array.isArray(item) && item.length >= 2) return [String(item[0]), String(item[1])];
    const edge = rec(item);
    if (edge) return [String(edge.from ?? edge.source ?? ""), String(edge.to ?? edge.target ?? "")];
    return ["", ""];
  });
  if (new Set(nodes).size !== nodes.length) throw new Error("Graph contains duplicate node IDs.");
  const unknown = edges.find(([from, to]) => !nodes.includes(from) || !nodes.includes(to));
  if (unknown) throw new Error("An edge refers to a node that was not declared: " + unknown[0] + " → " + unknown[1]);
  return { nodes, edges };
}
function topological(source: string): { order: string[]; hasCycle: boolean } {
  const graph = parseGraph(source);
  const indegree = new Map(graph.nodes.map((node) => [node, 0]));
  const outgoing = new Map(graph.nodes.map((node) => [node, [] as string[]]));
  for (const [from, to] of graph.edges) {
    outgoing.get(from)?.push(to);
    indegree.set(to, (indegree.get(to) ?? 0) + 1);
  }
  const ready = graph.nodes.filter((node) => indegree.get(node) === 0);
  const order: string[] = [];
  while (ready.length) {
    const current = ready.shift();
    if (!current) break;
    order.push(current);
    for (const next of outgoing.get(current) ?? []) {
      indegree.set(next, (indegree.get(next) ?? 1) - 1);
      if (indegree.get(next) === 0) ready.push(next);
    }
  }
  return { order, hasCycle: order.length !== graph.nodes.length };
}
function localHostCheck(value: string): { host: string; appearsLocal: boolean; reason: string } {
  let host = value.trim().toLowerCase();
  try { if (host.includes("://")) host = new URL(host).hostname.toLowerCase(); }
  catch { return { host, appearsLocal: false, reason: "Invalid URL" }; }
  host = host.replace(/^\[|\]$/g, "").replace(/\.$/, "");
  const parts = host.split(".").map(Number);
  const ipv4 = parts.length === 4 && parts.every((part) => Number.isInteger(part) && part >= 0 && part <= 255);
  const privateV4 = ipv4 && (
    parts[0] === 10 ||
    parts[0] === 127 ||
    (parts[0] === 192 && parts[1] === 168) ||
    (parts[0] === 172 && parts[1] >= 16 && parts[1] <= 31) ||
    (parts[0] === 169 && parts[1] === 254)
  );
  const appearsLocal = host === "localhost" || host === "::1" || host.endsWith(".local") || Boolean(privateV4);
  return { host, appearsLocal, reason: appearsLocal ? "Loopback/private/link-local name or address pattern" : "Does not match recognized local/private patterns" };
}
function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Utility could not complete.";
}

async function runOperation(tool: Tool, input: ToolkitInput): Promise<string> {
  const a = num(input.a), b = num(input.b), c = num(input.c), textA = input.textA, textB = input.textB;
  const bits = tool.param ?? 4;
  const json = (value: unknown) => JSON.stringify(value, null, 2);
  const rows = () => parseRows(textA);
  const numericA = () => parseNumbers(textA);
  const numericB = () => parseNumbers(textB);
  switch (tool.kind) {
    case "weight-size": return fmt(a * bits / 8) + " GB estimated weight storage\nFormula: parameter billions × bits ÷ 8. Excludes quantization metadata, KV cache, activations, and runtime overhead.";
    case "kv-cache": {
      const extras = parseNumbers(textB);
      const headDim = extras[0] || 128, bytes = extras[1] || 2;
      return json({ estimate_GiB: Number((a * b * (c || 8) * headDim * bytes * 2 / (1024 ** 3)).toFixed(3)), layers: a, context_tokens: b, kv_heads: c || 8, head_dimension_assumption: headDim, bytes_per_value: bytes, note: "Approximation; verify the model's actual architecture, GQA layout, and cache dtype." });
    }
    case "quant-savings": {
      const original = a * 2;
      const packed = a * bits / 8;
      return json({ fp16_GB: fmt(original), quantized_weight_GB: fmt(packed), estimated_savings_GB: fmt(original - packed), estimated_savings_percent: fmt(original ? (original - packed) / original * 100 : 0), quantization_bits: bits, note: "Weight-only estimate; scales and quantization block metadata add overhead." });
    }
    case "quant-compare": {
      const sourceBits = b || 16, targetBits = c || 4, original = a * sourceBits / 8, target = a * targetBits / 8;
      return json({ parameters_billions: a, source_bits: sourceBits, target_bits: targetBits, source_GB: fmt(original), target_GB: fmt(target), savings_GB: fmt(original - target), savings_percent: fmt(original ? (original - target) / original * 100 : 0) });
    }
    case "memory-fit": {
      const base = a * bits / 8;
      const isHardware = tool.category === "Hardware planning";
      const reservePercent = clamp(c, 0, 95);
      const overheadPercent = isHardware ? 0 : clamp(c, 0, 500);
      const required = base * (1 + overheadPercent / 100);
      const usable = isHardware ? b * (1 - reservePercent / 100) : b;
      return json({ assumed_bits_per_parameter: bits, estimated_weight_GB: fmt(base), runtime_overhead_percent: fmt(overheadPercent), physical_memory_GB: fmt(b), reserve_percent: isHardware ? reservePercent : null, usable_memory_GB: fmt(usable), total_estimate_GB: fmt(required), estimated_fit: required <= usable, note: "A weight-focused screening estimate, not a guarantee. KV cache and activations may require substantially more memory." });
    }
    case "shard-count": {
      if (b <= 0) throw new Error("B must be greater than zero.");
      return json({ estimated_size_GB: a, target_shard_GB: b, shard_count: Math.max(1, Math.ceil(a / b)), final_shard_GB: fmt(a % b || Math.min(a, b)), note: "Actual tensor/model formats may impose their own shard rules." });
    }
    case "compression-ratio": {
      if (b <= 0) throw new Error("B must be greater than zero.");
      return json({ original_GB: a, compressed_GB: b, compression_ratio: fmt(a / b) + "×", size_reduction_percent: fmt((a - b) / a * 100) + "%" });
    }
    case "effective-batch": return json({ effective_batch_size: Math.max(0, Math.floor(a)) * Math.max(0, Math.floor(b)) * Math.max(1, Math.floor(c || 1)), formula: "micro-batch × accumulation × device count" });
    case "steps-epoch": return json({ steps_per_epoch: b > 0 ? Math.ceil(a / (b * Math.max(1, c || 1))) : null, examples: a, batch_size_per_device: b, devices: Math.max(1, c || 1) });
    case "total-steps": return json({ steps_per_epoch: b > 0 ? Math.ceil(a / b) : null, epochs: c, total_optimizer_steps: b > 0 ? Math.ceil(a / b) * Math.max(0, Math.ceil(c)) : null });
    case "tokens-seen": return json({ estimated_tokens_processed: Math.max(0, a) * Math.max(0, b) * Math.max(0, c), formula: "steps × effective batch × sequence length" });
    case "warmup-steps": return json({ warmup_steps: Math.ceil(Math.max(0, a) * clamp(b, 0, 100) / 100), total_steps: a, warmup_percent: clamp(b, 0, 100) });
    case "training-duration": return json({ raw_seconds: a * b, with_checkpoint_overhead_seconds: a * b * (1 + clamp(c, 0, 1000) / 100), estimated_minutes: fmt(a * b * (1 + clamp(c, 0, 1000) / 100) / 60), note: "Use a measured steps/second benchmark for a reliable estimate." });
    case "linear-lr": return json({ learning_rate: Math.max(0, a) * (1 - clamp(b / (c || 1), 0, 1)), progress_percent: fmt(clamp(b / (c || 1), 0, 1) * 100) });
    case "cosine-lr": return json({ learning_rate: Math.max(0, a) * (1 + Math.cos(Math.PI * clamp(b / (c || 1), 0, 1))) / 2, progress_percent: fmt(clamp(b / (c || 1), 0, 1) * 100), note: "Un-warmed cosine decay; actual schedulers may have warmup, restarts, or minimum LR." });
    case "optimizer-memory": return json({ parameter_billions: a, weight_bytes_per_parameter: b || 2, state_copies: c || 2, estimated_weight_and_state_GB: fmt(a * ((b || 2) + (c || 2) * 4)), note: "Assumes FP32 optimizer states when counting each state copy as four bytes; excludes activations and gradients." });
    case "checkpoint-storage": return json({ base_storage_GB: a * Math.max(0, b), temporary_overhead_GB: a * Math.max(0, b) * clamp(c, 0, 1000) / 100, total_budget_GB: a * Math.max(0, b) * (1 + clamp(c, 0, 1000) / 100) });
    case "json-stats": {
      const parsed = rows();
      const objectRows = parsed.filter((item) => rec(item) !== null).map((item) => rec(item) as JsonRecord);
      const keys = Array.from(new Set(objectRows.flatMap((item) => Object.keys(item)))).sort();
      const missingCounts = Object.fromEntries(keys.map((key) => [key, objectRows.filter((item) => !(key in item) || item[key] === null).length]));
      return json({ record_count: parsed.length, object_record_count: objectRows.length, non_object_count: parsed.length - objectRows.length, field_names: keys, missing_or_null_by_field: missingCounts, note: "Values are not returned." });
    }
    case "jsonl-validate": {
      const lines = textA.split(/\r?\n/).filter((line) => line.trim());
      let invalid = 0, nonObject = 0;
      for (const line of lines) { try { if (rec(JSON.parse(line) as unknown) === null) nonObject += 1; } catch { invalid += 1; } }
      return json({ non_empty_lines: lines.length, malformed_json_lines: invalid, valid_non_object_lines: nonObject, valid_object_lines: lines.length - invalid - nonObject });
    }
    case "duplicate-lines": {
      const lines = textA.split(/\r?\n/).map((line) => line.trim()).filter(Boolean), counts = new Map<string, number>();
      for (const line of lines) counts.set(line, (counts.get(line) ?? 0) + 1);
      const duplicateGroups = Array.from(counts.values()).filter((count) => count > 1).length;
      return json({ non_empty_lines: lines.length, unique_lines: counts.size, duplicate_groups: duplicateGroups, duplicate_extra_occurrences: lines.length - counts.size });
    }
    case "schema-diff": {
      const left = rows(), right = parseRows(textB);
      const lkeys = new Set(left.flatMap((item) => Object.keys(rec(item) ?? {})));
      const rkeys = new Set(right.flatMap((item) => Object.keys(rec(item) ?? {})));
      return json({ text_a_records: left.length, text_b_records: right.length, only_in_text_a: Array.from(lkeys).filter((key) => !rkeys.has(key)).sort(), only_in_text_b: Array.from(rkeys).filter((key) => !lkeys.has(key)).sort(), shared_fields: Array.from(lkeys).filter((key) => rkeys.has(key)).sort() });
    }
    case "null-rate": {
      const field = textB.trim();
      if (!field) throw new Error("Enter the field name in Text B.");
      const list = rows(), missing = list.filter((item) => { const object = rec(item); return !object || !(field in object) || object[field] === null; }).length;
      return json({ field, records: list.length, missing_or_null: missing, missing_or_null_percent: fmt(list.length ? missing / list.length * 100 : 0) });
    }
    case "text-stats": {
      const lines = textA.split(/\r?\n/), words = textA.trim() ? textA.trim().split(/\s+/) : [];
      const lens = lines.map((line) => line.length);
      return json({ characters: textA.length, lines: textA ? lines.length : 0, words: words.length, approximate_tokens_character_div_4: Math.ceil(textA.length / 4), mean_line_characters: fmt(lens.length ? lens.reduce((sum, length) => sum + length, 0) / lens.length : 0), max_line_characters: lens.reduce((maximum, length) => Math.max(maximum, length), 0) });
    }
    case "split-size": {
      const trainFraction = clamp(b, 0, 1), valFraction = clamp(c, 0, 1 - trainFraction);
      return json({ total_rows: Math.floor(a), train_rows: Math.floor(a * trainFraction), validation_rows: Math.floor(a * valFraction), test_rows: Math.max(0, Math.floor(a) - Math.floor(a * trainFraction) - Math.floor(a * valFraction)), train_fraction: trainFraction, validation_fraction: valFraction, test_fraction: 1 - trainFraction - valFraction });
    }
    case "class-balance": {
      const field = textB.trim(); if (!field) throw new Error("Enter the label field in Text B.");
      const counts = new Map<string, number>();
      for (const item of rows()) { const object = rec(item); const value = object && field in object ? String(object[field]) : "[missing]"; counts.set(value, (counts.get(value) ?? 0) + 1); }
      return json({ records: rows().length, classes: Object.fromEntries(Array.from(counts.entries()).sort((x, y) => y[1] - x[1]).map(([key, count]) => [key.slice(0, 120), count])), note: "Class values may be sensitive; review output before sharing." });
    }
    case "leakage": {
      const norm = (line: string) => line.trim().replace(/\s+/g, " ").toLocaleLowerCase();
      const train = new Set(textA.split(/\r?\n/).map(norm).filter(Boolean)), evalRows = textB.split(/\r?\n/).map(norm).filter(Boolean);
      const overlap = evalRows.filter((line) => train.has(line));
      return json({ train_unique_lines: train.size, evaluation_lines: evalRows.length, exact_overlap_count: overlap.length, exact_overlap_percent: fmt(evalRows.length ? overlap.length / evalRows.length * 100 : 0), note: "Detects exact normalized line overlap only; it does not detect semantic leakage." });
    }
    case "csv-preview": {
      const data = parseCsv(textA);
      return json({ row_count: Math.max(0, data.length - 1), column_count: data[0]?.length ?? 0, headers: data[0] ?? [], preview: data.slice(1, 6).map((row) => row.slice(0, 20)), note: "Review the preview for sensitive values before sharing." });
    }
    case "exact-match": {
      const references = textA.split(/\r?\n/), predictions = textB.split(/\r?\n/), count = Math.max(references.length, predictions.length);
      if (!textA.trim() || !textB.trim()) throw new Error("Supply references in Text A and predictions in Text B.");
      const matched = Array.from({ length: count }, (_, index) => (references[index] ?? "").trim() === (predictions[index] ?? "").trim()).filter(Boolean).length;
      return json({ matched, total: count, exact_match_percent: fmt(matched / count * 100), mismatched_or_missing: count - matched });
    }
    case "token-f1":
    case "jaccard": {
      const left = textA.toLocaleLowerCase().match(/[\p{L}\p{N}_]+/gu) ?? [], right = textB.toLocaleLowerCase().match(/[\p{L}\p{N}_]+/gu) ?? [];
      const leftSet = new Set(left), rightSet = new Set(right), overlap = Array.from(leftSet).filter((token) => rightSet.has(token)).length;
      if (tool.kind === "jaccard") { const union = new Set([...leftSet, ...rightSet]).size; return json({ intersection: overlap, union, jaccard_percent: fmt(union ? overlap / union * 100 : 0) }); }
      const precision = rightSet.size ? overlap / rightSet.size : 0, recall = leftSet.size ? overlap / leftSet.size : 0;
      return json({ overlap_unique_tokens: overlap, reference_unique_tokens: leftSet.size, prediction_unique_tokens: rightSet.size, precision: fmt(precision), recall: fmt(recall), f1: fmt(precision + recall ? 2 * precision * recall / (precision + recall) : 0), note: "Unique-token overlap; this is not a semantic metric or official benchmark." });
    }
    case "wilson": {
      const total = Math.floor(b), successes = Math.floor(a), z = 1.96;
      if (total <= 0 || successes < 0 || successes > total) throw new Error("Require B > 0 and 0 ≤ successes A ≤ total B.");
      const p = successes / total, den = 1 + z * z / total, center = (p + z * z / (2 * total)) / den, half = z * Math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / den;
      return json({ successes, total, rate_percent: fmt(p * 100), wilson_95_low_percent: fmt(Math.max(0, center - half) * 100), wilson_95_high_percent: fmt(Math.min(1, center + half) * 100) });
    }
    case "threshold": return json({ score: a, threshold: b, passed: a >= b, margin: fmt(a - b) });
    case "pass-rate": {
      const values = numericA(), threshold = a, passed = values.filter((value) => value >= threshold).length;
      return json({ count: values.length, passed, failed: values.length - passed, pass_rate_percent: fmt(values.length ? passed / values.length * 100 : 0), threshold });
    }
    case "relative-change": return json({ baseline: a, current: b, absolute_change: fmt(b - a), relative_change_percent: a !== 0 ? fmt((b - a) / Math.abs(a) * 100) : null, direction: b > a ? "increase" : b < a ? "decrease" : "unchanged", note: a === 0 ? "Relative change is undefined when the baseline is zero." : undefined });
    case "absolute-difference": return json({ baseline: a, current: b, absolute_difference: fmt(Math.abs(b - a)), signed_difference: fmt(b - a) });
    case "mae":
    case "rmse": {
      const actual = numericA(), predicted = numericB();
      if (!actual.length || actual.length !== predicted.length) throw new Error("Text A and Text B must contain equal non-empty numeric lists.");
      const squaredOrAbs = actual.map((value, index) => tool.kind === "mae" ? Math.abs(value - predicted[index]) : (value - predicted[index]) ** 2);
      const avg = squaredOrAbs.reduce((sum, value) => sum + value, 0) / actual.length;
      return json({ samples: actual.length, metric: tool.kind === "mae" ? "MAE" : "RMSE", score: fmt(tool.kind === "mae" ? avg : Math.sqrt(avg)) });
    }
    case "token-estimate": return json({ characters: textA.length, approximate_tokens: Math.ceil(textA.length / 4), method: "characters divided by four", warning: "Tokenizer-specific counts vary; use the target model's tokenizer for authoritative budgeting." });
    case "context-budget": return json({ context_tokens: a, prompt_tokens: b, reserved_output_tokens: c, remaining_unallocated_tokens: Math.max(0, a - b - c), fits: b + c <= a, overflow_tokens: Math.max(0, b + c - a) });
    case "throughput": {
      if (b <= 0) throw new Error("B (elapsed seconds) must be greater than zero.");
      return json({ tokens: a, seconds: b, tokens_per_second: fmt(a / b), milliseconds_per_token: fmt(a ? b * 1000 / a : 0) });
    }
    case "percentiles":
    case "latency-summary": {
      const values = numericA();
      if (!values.length) throw new Error("Enter one or more numeric latency samples in Text A.");
      return json({ samples: values.length, min: values.reduce((minimum, value) => Math.min(minimum, value), Number.POSITIVE_INFINITY), median: percentile(values, 50), p90: percentile(values, 90), p95: percentile(values, 95), p99: percentile(values, 99), max: values.reduce((maximum, value) => Math.max(maximum, value), Number.NEGATIVE_INFINITY), unit: "same unit as input" });
    }
    case "timeout-budget": return json({ combined_timeout_ms: Math.max(0, a) + Math.max(0, b) + Math.max(0, c), connect_ms: a, first_token_ms: b, stream_idle_ms: c, note: "A combined budget is not the same as a per-stage enforced timeout." });
    case "parallel-slots": {
      if (b <= 0) throw new Error("B (memory per request) must be greater than zero.");
      return json({ available_memory_GB: a, extra_memory_per_request_GB: b, estimated_parallel_slots: Math.max(0, Math.floor(a / b)), note: "Ignores scheduler overhead, KV-cache growth, and fragmentation." });
    }
    case "stop-check": {
      const stops = textB.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
      const hits = stops.filter((stop) => textA.includes(stop));
      return json({ stop_sequences_checked: stops.length, matched_count: hits.length, stopped_by: hits[0] ? "[matched sequence redacted]" : null, contains_any_stop_sequence: hits.length > 0 });
    }
    case "template-render": {
      const values: unknown = JSON.parse(textB);
      const object = rec(values);
      if (!object) throw new Error("Text B must be a JSON object.");
      const rendered = textA.replace(/\{\{\s*([A-Za-z0-9_.-]+)\s*\}\}/g, (_match, key: string) => {
        const value = key.split(".").reduce<unknown>((current, part) => rec(current)?.[part], object);
        return value === undefined ? "[MISSING:" + key + "]" : typeof value === "string" ? value : JSON.stringify(value);
      });
      return rendered;
    }
    case "truncation": return json({ context_limit: a, prompt_tokens: b, requested_output_tokens: c, available_output_tokens: Math.max(0, a - b), will_truncate_or_overflow: b + c > a, overflow_tokens: Math.max(0, b + c - a) });
    case "memory-reserve": return json({ installed_memory_GB: a, reserve_percent: clamp(b, 0, 100), reserved_GB: a * clamp(b, 0, 100) / 100, available_GB: a * (1 - clamp(b, 0, 100) / 100) });
    case "cpu-workers": return json({ logical_cores: Math.max(0, Math.floor(a)), reserved_cores: clamp(Math.floor(b), 0, Math.max(0, Math.floor(a))), recommended_worker_ceiling: Math.max(1, Math.floor(a) - Math.max(0, Math.floor(b))), note: "Starting point only; tune against measured throughput and latency." });
    case "bandwidth-rate": {
      if (b <= 0) throw new Error("B must be greater than zero.");
      return json({ bandwidth_GB_per_second: a, bytes_per_generated_token: b, theoretical_tokens_per_second: fmt(a * 1e9 / b), note: "An idealized bandwidth ceiling; actual kernels, caching, and parallelism reduce throughput." });
    }
    case "unified-memory": return json({ physical_unified_memory_GB: a, usable_percent: clamp(b, 0, 100), usable_GB: a * clamp(b, 0, 100) / 100, model_GB: c, fits_weight_only: c <= a * clamp(b, 0, 100) / 100 });
    case "pcie-time": {
      if (b <= 0) throw new Error("B (effective GB/s) must be greater than zero.");
      return json({ transfer_GB: a, effective_GB_per_second: b, theoretical_seconds: fmt(a / b), theoretical_milliseconds: fmt(a / b * 1000), note: "Does not account for protocol overhead, synchronization, or contention." });
    }
    case "thermal-headroom": return json({ limit_celsius: a, current_celsius: b, headroom_celsius: fmt(a - b), at_or_above_limit: b >= a });
    case "performance-per-watt": {
      if (b <= 0) throw new Error("B (watts) must be greater than zero.");
      return json({ tokens_per_second: a, watts: b, tokens_per_joule: fmt(a / b), note: "Compare measurements using the same workload and power measurement boundary." });
    }
    case "uncertainty": return json({ estimate: a, uncertainty_percent: clamp(b, 0, 1000), low: a - Math.abs(a) * clamp(b, 0, 1000) / 100, high: a + Math.abs(a) * clamp(b, 0, 1000) / 100, note: "Illustrative sensitivity range, not a statistical confidence interval." });
    case "power-budget": return json({ device_power_budget_W: a, other_system_load_W: b, accelerator_load_W: c, total_load_W: b + c, spare_budget_W: a - b - c, within_budget: b + c <= a });
    case "redact": return redactText(textA);
    case "pii-scan": return json({ email_like_count: (textA.match(/\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi) ?? []).length, phone_like_count: (textA.match(/(?:\+?\d[\d .()\-]{7,}\d)/g) ?? []).length, note: "Counts only; heuristic patterns can miss or overcount sensitive data." });
    case "path-check": {
      const path = textA.trim().replace(/\\/g, "/"), absolute = path.startsWith("/") || /^[A-Za-z]:\//.test(path) || path.startsWith("//"), traversal = path.split("/").includes(".."), nul = path.includes("\0");
      return json({ relative_path: !absolute, parent_traversal: traversal, contains_nul: nul, lexically_safe: Boolean(path) && !absolute && !traversal && !nul, note: "Lexical check only; filesystem symlinks and permissions require server-side validation." });
    }
    case "url-check": {
      let details: unknown;
      try {
        const url = new URL(textA.trim());
        details = { protocol: url.protocol, hostname: url.hostname, secure_transport: url.protocol === "https:", credentials_embedded: Boolean(url.username || url.password), non_http_scheme: !["https:", "http:"].includes(url.protocol), has_query: Boolean(url.search), review_required: url.protocol !== "https:" || Boolean(url.username || url.password) };
      } catch { details = { valid_url: false, review_required: true }; }
      return json(details);
    }
    case "tool-policy": {
      const list: unknown = JSON.parse(textA);
      if (!Array.isArray(list)) throw new Error("Text A must be a JSON array.");
      const allowedKeys = new Set(["name", "description", "allowed", "read", "write", "network", "execute"]);
      return json({ tools_reviewed: list.length, decisions: list.map((item) => {
        const object = rec(item) ?? {};
        const requested = object.allowed === true;
        const read = object.read === true, write = object.write === true, network = object.network === true, execute = object.execute === true;
        const unknownPermissionFields = Object.keys(object).filter((key) => !allowedKeys.has(key));
        const candidateReadOnly = requested && read && !write && !network && !execute && unknownPermissionFields.length === 0;
        return { name: String(object.name ?? "[unnamed]").slice(0, 120), requested_allow: requested, read, write, network, execute, unknown_permission_fields: unknownPermissionFields, decision: candidateReadOnly ? "candidate read-only allow; still require operator review" : "deny by default" };
      }), note: "Advisory review only. A policy engine must enforce permissions at the backend boundary." });
    }
    case "env-redact": return textA.split(/\r?\n/).map((line) => {
      if (!line.trim() || /^\s*[#;]/.test(line)) return line;
      const at = line.indexOf("="); if (at < 0) return line;
      const key = line.slice(0, at), value = line.slice(at + 1);
      return /key|token|secret|pass|credential|cookie|auth|private/i.test(key) ? key + "=[REDACTED]" : key + "=" + value;
    }).join("\n");
    case "secret-scan": {
      const patterns: [string, RegExp][] = [
        ["private_key", /-----BEGIN [A-Z ]*PRIVATE KEY-----/g],
        ["bearer_token", /\bBearer\s+[A-Za-z0-9._~+/-]+=*/gi],
        ["github_token", /\bgh[pousr]_[A-Za-z0-9_]{20,}\b/g],
        ["openai_like_key", /\bsk-[A-Za-z0-9_-]{16,}\b/g],
        ["aws_access_key", /\bAKIA[A-Z0-9]{16}\b/g],
        ["password_assignment", /\b(password|passwd|secret)\s*[:=]\s*\S+/gi],
      ];
      return json(Object.fromEntries(patterns.map(([name, pattern]) => [name, (textA.match(pattern) ?? []).length])));
    }
    case "injection-scan": {
      const checks: [string, RegExp][] = [["instruction_override", /ignore (all |any |the )?(previous|above|prior) instructions?/i], ["secret_exfiltration", /(reveal|print|dump|exfiltrate).{0,40}(secret|password|token|credential)/i], ["role_override", /(you are now|act as|system prompt is)/i], ["tool_misuse", /(disable|bypass).{0,30}(security|guardrail|permission|policy)/i]];
      const triggered = checks.filter(([, pattern]) => pattern.test(textA)).map(([name]) => name);
      return json({ heuristic_flags: triggered, flag_count: triggered.length, note: "Heuristic only. Never use this output as the sole security control." });
    }
    case "bounded-input": return json({ input_characters: textA.length, maximum_characters: Math.max(0, Math.floor(a)), accepted_characters: Math.min(textA.length, Math.max(0, Math.floor(a))), would_truncate: textA.length > Math.max(0, Math.floor(a)), preview: textA.slice(0, Math.max(0, Math.min(Math.floor(a), 500))) });
    case "local-address": return json(localHostCheck(textA));
    case "dag-validate":
    case "dag-order":
    case "cycle-check":
    case "dependency-order": {
      const ordered = topological(textA);
      if (tool.kind === "cycle-check") return json({ has_cycle: ordered.hasCycle, node_count: parseGraph(textA).nodes.length });
      if (tool.kind === "dag-validate") return json({ valid: !ordered.hasCycle, has_cycle: ordered.hasCycle, topological_order: ordered.order, node_count: parseGraph(textA).nodes.length, edge_count: parseGraph(textA).edges.length });
      if (tool.kind === "dependency-order") return json({ has_cycle: ordered.hasCycle, dependency_order: ordered.order, all_dependencies_declared: true });
      return json({ topological_order: ordered.order, has_cycle: ordered.hasCycle });
    }
    case "missing-inputs": {
      const object = rec(JSON.parse(textA) as unknown); if (!object) throw new Error("Text A must be a JSON object.");
      const required = Array.isArray(object.required) ? object.required.map(String) : [], provided = new Set(Array.isArray(object.provided) ? object.provided.map(String) : []);
      return json({ required_count: required.length, provided_count: provided.size, missing: required.filter((item) => !provided.has(item)), ready: required.every((item) => provided.has(item)) });
    }
    case "manifest":
    case "manifest-check": {
      const object = rec(JSON.parse(textA) as unknown); if (!object) throw new Error("Text A must contain a JSON object.");
      if (tool.kind === "manifest-check") return json({ valid_json_object: true, has_name: typeof object.name === "string" || typeof object.project === "string", has_version: typeof object.version === "string" || typeof object.schema_version === "number", top_level_keys: Object.keys(object).sort(), note: "Basic metadata sanity check only." });
      return json({ schema_version: 1, created_at: new Date().toISOString(), metadata: object, reproducibility_note: "Add exact model, dataset, code, dependency, and seed identifiers before relying on this manifest." });
    }
    case "seed-manifest": return json({ schema_version: 1, seed: Math.floor(a), experiment_description: textA.slice(0, 500), seed_applied: false, note: "This records the requested seed; it does not set seeds in training frameworks." });
    case "artifact-name": return textA.normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9._-]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 100) || "axiom-artifact";
    case "output-path": {
      const path = textA.trim().replace(/\\/g, "/"), absolute = path.startsWith("/") || /^[A-Za-z]:\//.test(path), traversal = path.split("/").includes("..");
      return json({ path, accepted: Boolean(path) && !absolute && !traversal && !path.includes("\0"), reasons: [absolute ? "absolute path" : "", traversal ? "parent traversal" : "", path.includes("\0") ? "NUL byte" : ""].filter(Boolean), note: "This lexical review does not inspect filesystem symlinks." });
    }
    case "step-budget": return json({ planned_steps: Math.max(0, Math.floor(a)), configured_max_steps: Math.max(0, Math.floor(b)), accepted: a >= 0 && a <= b, excess_steps: Math.max(0, Math.floor(a - b)) });
    case "retry-schedule":
    case "backoff": {
      const attempts = Math.floor(a), base = Math.max(0, b), cap = Math.max(0, c || 30000);
      return json({ delays_ms: Array.from({ length: clamp(attempts, 0, 20) }, (_, index) => Math.min(cap, base * 2 ** index)), attempts: clamp(attempts, 0, 20), capped_at_ms: cap, note: "No jitter is added; inject random jitter in production clients where appropriate." });
    }
    case "timeout-sum": {
      const values = numericA();
      return json({ stages: values.length, stage_timeout_sum_ms: values.reduce((sum, value) => sum + Math.max(0, value), 0), maximum_stage_ms: Math.max(0, ...values) });
    }
    case "pagination": {
      const total = Math.max(0, Math.floor(a)), offset = clamp(Math.floor(b), 0, total), limit = clamp(Math.floor(c || 50), 1, 1000), end = Math.min(total, offset + limit);
      return json({ total, offset, limit, returned_count: Math.max(0, end - offset), next_offset: end < total ? end : null, has_more: end < total });
    }
    case "request-id": return json({ value: textA.trim(), valid_uuid: /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(textA.trim()), note: "UUID validation only; a request ID is not an authentication credential." });
    case "json-format": try { return json(JSON.parse(textA) as unknown); } catch { throw new Error("Text A is not valid JSON. Input contents are not echoed."); }
    case "query-encode": return encodeURIComponent(textA);
    case "curl-safe": {
      let url: URL;
      try { url = new URL(textA.trim()); } catch { throw new Error("Enter a valid absolute URL."); }
      if (url.protocol !== "https:") throw new Error("Only HTTPS URLs are emitted by this read-only curl builder.");
      if (url.username || url.password) throw new Error("Remove embedded URL credentials first.");
      const singleQuote = String.fromCharCode(39);
      const shellEscape = singleQuote + String.fromCharCode(34) + singleQuote + String.fromCharCode(34) + singleQuote;
      const quotedUrl = singleQuote + url.toString().split(singleQuote).join(shellEscape) + singleQuote;
      return "curl --fail --silent --show-error --max-time 15 --request GET " + quotedUrl;
    }
    case "envelope-check": {
      const object = rec(JSON.parse(textA) as unknown); if (!object) throw new Error("Text A must be a JSON object.");
      return json({ has_status: "status" in object, has_data: "data" in object || "result" in object, has_error: "error" in object || "detail" in object, has_request_id: "request_id" in object || "requestId" in object, top_level_keys: Object.keys(object).sort() });
    }
    case "rate-budget": return json({ requests_per_second: a, window_seconds: b, capacity: Math.max(0, a) * Math.max(0, b), expected_requests: c, within_capacity: c <= a * b, excess_requests: Math.max(0, c - a * b) });
    case "system-prompt": return "SYSTEM PROMPT DRAFT\n\nRole:\nYou are an assistant for the task below. Follow the stated constraints and do not claim actions or evidence you do not have.\n\nTask:\n" + (textA.trim() || "[Describe the task]") + "\n\nConstraints:\n" + (textB.trim() || "- Be accurate and state uncertainty.\n- Respect data boundaries.\n- Ask for missing essential information rather than inventing facts.") + "\n\nOutput contract:\n- Provide a direct answer.\n- Separate verified facts from estimates.\n- Do not expose secrets or hidden reasoning.";
    case "role-check": {
      const parsed: unknown = JSON.parse(textA); if (!Array.isArray(parsed)) throw new Error("Text A must be a JSON array of message objects.");
      const allowed = new Set(["system", "developer", "user", "assistant", "tool"]);
      const issues = parsed.flatMap((item, index) => { const object = rec(item); if (!object) return ["message " + index + " is not an object"]; const role = String(object.role ?? ""); return [...(!allowed.has(role) ? ["message " + index + " has an unknown role"] : []), !(typeof object.content === "string" || Array.isArray(object.content)) ? ["message " + index + " has no string/parts content"] : []]; });
      return json({ message_count: parsed.length, issues, valid_shape: issues.length === 0, note: "Structural check only; content and tool-call semantics need separate validation." });
    }
    case "prompt-diff": {
      const oldLines = textA.split(/\r?\n/), newLines = textB.split(/\r?\n/), oldSet = new Set(oldLines), newSet = new Set(newLines);
      return json({ old_lines: oldLines.length, new_lines: newLines.length, removed_line_count: oldLines.filter((line) => !newSet.has(line)).length, added_line_count: newLines.filter((line) => !oldSet.has(line)).length, added_lines: newLines.filter((line) => !oldSet.has(line)).slice(0, 30), removed_lines: oldLines.filter((line) => !newSet.has(line)).slice(0, 30) });
    }
    case "few-shot": return "TASK\n" + textA.trim() + "\n\nEXAMPLES\n" + textB.split(/\r?\n/).filter(Boolean).map((line, index) => "Example " + (index + 1) + ":\n" + line).join("\n\n") + "\n\nNow solve the new input. Do not copy an example when it does not apply.";
    case "test-case-format": return json({ schema_version: 1, input: textA, expected_behavior: textB, assertions: [], notes: "Add objective assertions before using this test in an automated gate." });
    case "rubric": return json({ task: textA, scale: { "0": "Not attempted or unusable", "1": "Major errors; misses core requirements", "2": "Partially correct; meaningful omissions", "3": "Correct with minor gaps", "4": "Fully correct, complete, and well grounded" }, dimensions: ["correctness", "coverage", "clarity", "constraint compliance"], scoring_note: "Define task-specific evidence and adjudication rules before benchmarking." });
    case "schema-sample": {
      const schema = rec(JSON.parse(textA) as unknown); if (!schema) throw new Error("Text A must contain a schema object.");
      const properties = rec(schema.properties) ?? {};
      const sample: JsonRecord = {};
      for (const [key, value] of Object.entries(properties)) { const property = rec(value) ?? {}; const type = String(property.type ?? "string"); sample[key] = type === "integer" || type === "number" ? 0 : type === "boolean" ? false : type === "array" ? [] : type === "object" ? {} : type === "null" ? null : "example"; }
      return json({ sample, required: Array.isArray(schema.required) ? schema.required : [], note: "Minimal illustrative sample; it is not validated against the full JSON Schema specification." });
    }
    case "instruction-density": {
      const words = textA.trim().split(/\s+/).filter(Boolean), cues = (textA.match(/\b(must|should|never|always|required|only|do not|don't|ensure|avoid|return|include|exclude)\b/gi) ?? []).length;
      return json({ characters: textA.length, words: words.length, instruction_cues: cues, cue_per_100_words: fmt(words.length ? cues / words.length * 100 : 0), lines: textA ? textA.split(/\r?\n/).length : 0, note: "Heuristic cue count; not a measure of prompt quality." });
    }
    case "prompt-budget": return json({ context_tokens: a, reserved_output_tokens: b, safety_margin_tokens: c, prompt_budget_tokens: Math.max(0, a - b - c), overcommitted: b + c > a });
    case "prompt-variants": return json({ base: textA, goal: textB, variants: [{ name: "concise", instruction: "Solve the task with the fewest steps needed. State assumptions." }, { name: "structured", instruction: "Use an explicit plan, verify each requirement, then present a structured result." }, { name: "verification-focused", instruction: "Prioritize evidence, edge cases, and independent checks. Label uncertainty and limitations." }], note: "Templates for human review; no model was invoked." });
    case "semver": {
      const match = textA.trim().match(/^[v=]?(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+([0-9A-Za-z.-]+))?$/);
      return json(match ? { valid: true, major: Number(match[1]), minor: Number(match[2]), patch: Number(match[3]), prerelease: match[4] ?? null, build_metadata: match[5] ?? null } : { valid: false, note: "Expected MAJOR.MINOR.PATCH with an optional prerelease/build suffix." });
    }
    case "compatibility": {
      const installed = textA.trim().replace(/^v/, "").split(/[.+-]/), required = textB.trim().replace(/^v/, "").split(/[.+-]/);
      const left = installed.slice(0, 3).map((part) => Number(part)), right = required.slice(0, 3).map((part) => Number(part));
      const valid = left.length === 3 && right.length === 3 && [...left, ...right].every(Number.isFinite);
      return json({ installed: textA.trim(), required: textB.trim(), parseable_triplets: valid, same_major: valid && left[0] === right[0], installed_at_least_required: valid && (left[0] > right[0] || (left[0] === right[0] && (left[1] > right[1] || (left[1] === right[1] && left[2] >= right[2])))), note: "Simplified numeric comparison; not a full package-specifier/semver range evaluator." });
    }
    case "sha256": {
      if (!globalThis.crypto?.subtle) throw new Error("Web Crypto is unavailable in this browser context.");
      const bytes = new TextEncoder().encode(textA), digest = await globalThis.crypto.subtle.digest("SHA-256", bytes);
      return Array.from(new Uint8Array(digest)).map((value) => value.toString(16).padStart(2, "0")).join("");
    }
    case "platform-check": {
      const normalize = (value: string) => value.toLowerCase().replace(/amd64|x64/g, "x86_64").replace(/arm64/g, "aarch64").replace(/macos/g, "darwin").trim();
      return json({ target: textA.trim(), current: textB.trim(), normalized_target: normalize(textA), normalized_current: normalize(textB), exact_normalized_match: normalize(textA) === normalize(textB), note: "Label comparison only; it does not inspect the current runtime." });
    }
    case "dependency-check": {
      const spec = textA.trim(), valid = /^[A-Za-z0-9_.-]+(?:\[[A-Za-z0-9_,.-]+\])?\s*(?:===?|~=|!=|<=?|>=?)?\s*[A-Za-z0-9*+_.! -]*$/.test(spec);
      return json({ dependency_spec: spec.slice(0, 300), syntax_looks_plausible: valid, note: "Syntax heuristic only. Use the package resolver and lockfile for authoritative compatibility." });
    }
    case "changelog": {
      const buckets: Record<string, string[]> = { Added: [], Changed: [], Fixed: [], Security: [], Other: [] };
      for (const line of textA.split(/\r?\n/).filter(Boolean)) {
        const match = line.match(/^\s*[-*]\s*\[(Added|Changed|Fixed|Security)\]\s*(.*)$/i);
        if (match) { const key = match[1][0].toUpperCase() + match[1].slice(1).toLowerCase(); buckets[key].push(match[2]); }
        else buckets.Other.push(line.replace(/^\s*[-*]\s*/, ""));
      }
      return json(buckets);
    }
    case "port-check": {
      const value = textA.trim() ? Number(textA.trim()) : a;
      return json({ port: value, valid_integer: Number.isInteger(value), valid_port: Number.isInteger(value) && value >= 1 && value <= 65535, privileged_port: Number.isInteger(value) && value >= 1 && value < 1024 });
    }
    case "support-redact": return redactText(textA).replace(/(?:\/home|\/Users|\/mnt\/c)\/[^/\s]+/g, "[REDACTED HOME]").replace(/\b[A-Za-z]:\\Users\\[^\\\s]+/gi, "[REDACTED HOME]");
    case "filename": {
      const normalized = textA.normalize("NFKD").replace(/[\u0300-\u036f]/g, "").replace(/[<>:"\/\\|?*\x00-\x1F]/g, "-").replace(/\s+/g, "-").replace(/[. ]+$/g, "").replace(/-+/g, "-").slice(0, 120);
      return normalized || "axiom-file";
    }
    default: throw new Error("This utility is not implemented: " + tool.kind);
  }
}

export default function AxiomToolkit() {
  const [category, setCategory] = useState("All utilities");
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState("T001");
  const [input, setInput] = useState<ToolkitInput>({ a: "7", b: "16", c: "1", textA: "", textB: "" });
  const [result, setResult] = useState("");
  const [error, setError] = useState("");
  const [running, setRunning] = useState(false);
  const [ranId, setRanId] = useState("");

  const selected = useMemo(() => TOOLKIT_TOOLS.find((tool) => tool.id === selectedId) ?? TOOLKIT_TOOLS[0], [selectedId]);
  const visibleTools = useMemo(() => TOOLKIT_TOOLS.filter((tool) => (category === "All utilities" || tool.category === category) && (tool.title + " " + tool.description + " " + tool.category).toLowerCase().includes(search.toLowerCase().trim())), [category, search]);

  const chooseCategory = (value: string) => {
    setCategory(value);
    const first = value === "All utilities" ? TOOLKIT_TOOLS[0] : TOOLKIT_TOOLS.find((tool) => tool.category === value);
    if (first) setSelectedId(first.id);
    setResult(""); setError(""); setRanId("");
  };

  async function execute() {
    setRunning(true); setError(""); setResult(""); setRanId("");
    try {
      if (input.textA.length > 1_000_000 || input.textB.length > 1_000_000) {
        throw new Error("Inputs are limited to 1,000,000 characters per text field to keep browser-local processing bounded.");
      }
      const output = await runOperation(selected, input);
      setResult(output);
      setRanId(selected.id);
    } catch (cause) { setError(errorMessage(cause)); }
    finally { setRunning(false); }
  }

  return (
    <section className="axiom-toolkit">
      <div className="page-header">
        <div>
          <p className="eyebrow">AXIOM / LOCAL OPERATIONS TOOLKIT</p>
          <h1>AI Toolkit</h1>
          <p className="page-description">120 local utilities for model sizing, quantization, training, dataset quality, evaluation, inference, hardware, security, workflows, APIs, prompts, and releases.</p>
        </div>
        <div className="page-actions">
          <span className="status-pill success" aria-label="Feature count">{TOOLKIT_TOOLS.length} utilities</span>
        </div>
      </div>

      <div className="panel-surface" style={{ padding: 20, marginBottom: 18 }}>
        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap", justifyContent: "space-between" }}>
          <label style={{ display: "grid", gap: 6, flex: "1 1 280px" }}>
            <span>Search utilities</span>
            <input aria-label="Search toolkit utilities" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search KV cache, JSONL, secrets, retry…" />
          </label>
          <div style={{ fontSize: 13, opacity: 0.8 }}>{visibleTools.length} of {TOOLKIT_TOOLS.length} shown</div>
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 14 }} aria-label="Toolkit categories">
          {["All utilities", ...CATEGORIES.map((item) => item.name)].map((name) => (
            <button key={name} type="button" onClick={() => chooseCategory(name)} aria-pressed={category === name} className={category === name ? "primary-button" : "secondary-button"}>{name}</button>
          ))}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 440px), 1fr))", gap: 16, alignItems: "start" }}>
        <div className="panel-surface" style={{ padding: 16, minWidth: 0 }}>
          <h2 style={{ marginTop: 0 }}>Utility catalog</h2>
          <div style={{ display: "grid", gap: 8, maxHeight: 700, overflowY: "auto" }}>
            {visibleTools.map((tool) => (
              <button key={tool.id} type="button" data-tool-id={tool.id} data-tool-kind={tool.kind} onClick={() => { setSelectedId(tool.id); setResult(""); setError(""); setRanId(""); }} aria-pressed={selectedId === tool.id} className={selectedId === tool.id ? "toolkit-tool is-selected" : "toolkit-tool"} style={{ textAlign: "left", padding: 12, borderRadius: 10, border: "1px solid var(--border-color, #394150)", background: selectedId === tool.id ? "var(--surface-raised, rgba(100,120,160,.12))" : "transparent", color: "inherit", cursor: "pointer" }}>
                <span style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "baseline" }}>
                  <strong>{tool.title}</strong><small style={{ opacity: 0.7 }}>{tool.id}</small>
                </span>
                <small style={{ display: "block", opacity: 0.7, marginTop: 4 }}>{tool.category}</small>
              </button>
            ))}
            {visibleTools.length === 0 && <p>No utilities match this search.</p>}
          </div>
        </div>

        <div className="panel-surface" style={{ padding: 20, minWidth: 0 }}>
          <p className="eyebrow">{selected.category} · {selected.id}</p>
          <h2 style={{ marginTop: 0 }}>{selected.title}</h2>
          <p>{selected.description}</p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: 10 }}>
            <label style={{ display: "grid", gap: 5 }}>Number A<input aria-label="Number A" inputMode="decimal" type="number" value={input.a} onChange={(event) => setInput({ ...input, a: event.target.value })} /></label>
            <label style={{ display: "grid", gap: 5 }}>Number B<input aria-label="Number B" inputMode="decimal" type="number" value={input.b} onChange={(event) => setInput({ ...input, b: event.target.value })} /></label>
            <label style={{ display: "grid", gap: 5 }}>Number C<input aria-label="Number C" inputMode="decimal" type="number" value={input.c} onChange={(event) => setInput({ ...input, c: event.target.value })} /></label>
          </div>
          <label style={{ display: "grid", gap: 6, marginTop: 12 }}>
            <span>Text A / primary input</span>
            <textarea aria-label="Text A" rows={5} value={input.textA} onChange={(event) => setInput({ ...input, textA: event.target.value })} placeholder="Paste data, values, JSON, prompt text, URL, or measurements as described above." />
          </label>
          <label style={{ display: "grid", gap: 6, marginTop: 12 }}>
            <span>Text B / comparison or supporting input</span>
            <textarea aria-label="Text B" rows={4} value={input.textB} onChange={(event) => setInput({ ...input, textB: event.target.value })} placeholder="Use when the selected utility needs a comparison, schema, replacement object, or extra settings." />
          </label>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 14 }}>
            <button type="button" className="primary-button" onClick={() => void execute()} disabled={running}>{running ? "Running locally…" : "Run utility"}</button>
            <button type="button" className="secondary-button" onClick={() => { setInput({ a: "7", b: "16", c: "1", textA: "", textB: "" }); setResult(""); setError(""); setRanId(""); }}>Reset inputs</button>
            {result && <button type="button" className="secondary-button" onClick={() => { void navigator.clipboard?.writeText(result).catch(() => setError("Clipboard access is unavailable; select and copy the result manually.")); }}>Copy result</button>}
          </div>
          {error && <p role="alert" style={{ marginTop: 14 }}>{error}</p>}
          {result && <div style={{ marginTop: 16 }}>
            <h3>Result {ranId === selected.id ? "· completed locally" : ""}</h3>
            <pre className="api-playground-json" aria-live="polite" style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere", maxHeight: 360, overflow: "auto" }}>{result}</pre>
          </div>}
          <p style={{ fontSize: 12, opacity: 0.72, marginTop: 18 }}>Privacy boundary: these utility calculations execute in this browser tab and do not call the AXIOM API. Estimates are advisory, not hardware measurements. Do not paste secrets or personal data into the toolkit; redact before sharing any result.</p>
        </div>
      </div>
    </section>
  );
}
