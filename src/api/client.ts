const API_BASE = import.meta.env.VITE_AXIOM_API_URL || "";

export type WorkspaceModel = {
  id: string;
  name: string;
  source: string;
  format: string;
  parameters?: string | null;
  quantization?: string | null;
  architecture?: string | null;
  license?: string | null;
  tags?: string[];
  favorite?: boolean;
  content_sha256?: string | null;
};

export type WorkspaceModelPage = {
  models: WorkspaceModel[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
};

export type WorkspaceModelCandidate = {
  path: string;
  lineage: { relation: "source" | "derived_from"; parent_manifest_sha256: string | null };
  format: string;
  has_config: boolean;
  weight_file_count: number;
  weight_size_bytes: number;
};

export type WorkspaceModelInspection = {
  path: string;
  architecture: string | null;
  model_type: string | null;
  parameter_count: number | null;
  model_format: string;
  weight_size_bytes: number;
  has_config: boolean;
  has_tokenizer: boolean;
  has_safetensors: boolean;
  has_gguf: boolean;
  has_pytorch_weights: boolean;
  capabilities: string[];
  estimated_vram_gb: number | null;
  status: string;
};

export type WorkspaceDataset = {
  path: string;
  size_bytes: number;
};

export type DatasetProfileField = {
  name: string;
  occurrences: number;
  null_count: number;
  null_rate: number;
  types: Record<string, number>;
  possibly_sensitive: boolean;
};

export type DatasetScanLimits = {
  max_bytes: number;
  max_rows: number;
  max_line_bytes: number;
};

export type DatasetManifest = {
  schema_version: number;
  generated_at: string;
  path: string;
  lineage: { relation: "source" | "derived_from"; parent_manifest_sha256: string | null };
  file_name: string;
  format: string;
  file_size_bytes: number;
  bytes_hashed: number;
  full_content_hashed: boolean;
  sha256: string | null;
  partial_sha256: string | null;
  status: "complete" | "partial" | "changed_during_read";
  modified_at: string | null;
  limits: { max_bytes: number };
};

export type DatasetCleaningPreview = {
  path: string;
  file_name: string;
  preview_only: boolean;
  output_written: boolean;
  file_size_bytes: number;
  bytes_scanned: number;
  lines_scanned: number;
  kept_rows: number;
  removed_rows: number;
  removed_empty_rows: number;
  removed_invalid_rows: number;
  removed_non_object_rows: number;
  removed_schema_rows: number;
  removed_duplicate_rows: number;
  overlong_rows: number;
  rewritten_rows: number;
  estimated_output_bytes: number;
  truncated: boolean;
  truncation_reasons: string[];
  changes: Array<{ operation: string; rows: number }>;
  warnings: string[];
  limits: DatasetScanLimits;
};

export type DatasetProfile = {
  file_name: string;
  file_size_bytes: number;
  bytes_scanned: number;
  lines_scanned: number;
  valid_rows: number;
  invalid_rows: number;
  empty_rows: number;
  duplicate_rows: number;
  duplicate_key_summary: {
    fields: string[];
    eligible_rows: number;
    duplicate_rows: number;
    rate: number;
    threshold: number | null;
    threshold_exceeded: boolean;
  };
  overlong_rows: number;
  diagnostics: {
    encoding: string;
    encoding_errors: number;
    malformed_json_rows: number;
    non_object_json_rows: number;
    newline_style: string;
    newline_counts: Record<string, number>;
    delimiter: string;
  };
  text_token_lengths: Record<string, { observations: number; histogram: Record<string, number> }>;
  privacy_review_recommended: boolean;
  possibly_sensitive_fields: string[];
  sensitive_field_rules: string[];
  ignored_sensitive_fields: string[];
  pii_scan: {
    status: "completed" | "not_run";
    opted_in: boolean;
    values_scanned: number;
    matches_by_type: Record<string, number>;
    fields_by_type: Record<string, string[]>;
    long_values_skipped: number;
    rows_truncated_by_scan_limit: number;
    max_text_bytes: number;
    max_values_per_row: number;
  };
  truncated: boolean;
  truncation_reasons: string[];
  fields: DatasetProfileField[];
  warnings: string[];
  limits: DatasetScanLimits;
};

export type DatasetQualityResult = {
  datasets: Array<{ path: string; profile: DatasetProfile }>;
  comparison: {
    dataset_count: number;
    datasets: Array<{ path: string; valid_rows: number; truncated: boolean }>;
    has_differences: boolean;
    fields: Array<{
      name: string;
      present_in: string[];
      missing_from: string[];
      types_by_dataset: Record<string, string[]>;
      type_mismatch: boolean;
      possibly_sensitive: boolean;
    }>;
  };
  checks: Record<string, {
    passed: boolean;
    missing_fields: string[];
    type_mismatches: Array<{ field: string; expected: string; observed: string[] }>;
  }>;
  limits: DatasetScanLimits;
};

export type HardwareSnapshot = {
  os_name: string;
  architecture: string;
  cpu_cores: number;
  ram_gb: number;
  gpu_name: string | null;
  vram_gb: number | null;
  cuda_available: boolean;
};

export type RuntimeSnapshot = {
  status: string;
  hardware: HardwareSnapshot;
};

export type TrainingPlan = {
  method: string;
  precision: string;
  lora_rank: number;
  batch_size: number;
  gradient_accumulation: number;
  sequence_length: number;
  learning_rate: number;
  estimated_vram_gb: number;
  fits_hardware: boolean;
  reason: string;
};

export type WorkspaceEvent = {
  action: string;
  detail: string | null;
  timestamp: string;
};

export type WorkspaceExperiment = {
  schema_version: 1;
  id: string;
  name: string;
  created_at: string;
  model: string | null;
  dataset: string | null;
  notes: string | null;
  tags: string[];
  parameter_billions: number;
  requested_method: string;
  status: "planned";
  hardware?: HardwareSnapshot;
  plan: TrainingPlan;
};

export type WorkspaceExperimentPage = {
  experiments: WorkspaceExperiment[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
};

export type WorkspaceEvaluationRun = {
  schema_version: 1;
  id: string;
  name: string;
  created_at: string;
  model_label: string | null;
  baseline: boolean;
  status: "complete" | "partial";
  execution_status: "precomputed_outputs_only";
  comparison: {
    baseline_run_id: string;
    metric: string;
    baseline_score: number;
    current_score: number;
    delta: number;
    regression_tolerance: number;
    status: "passed" | "regression";
  } | null;
  output_manifest: { format: string; sha256: string; bytes: number };
  report: {
    path: string;
    file_name: string;
    dataset_manifest: {
      sha256: string | null;
      partial_sha256: string | null;
      bytes_hashed: number;
      file_size_bytes: number;
      full_content_hashed: boolean;
    };
    fields: {
      prediction: string;
      reference: string;
      split: string | null;
      selected_split: string | null;
    };
    counts: {
      lines_scanned: number;
      valid_samples: number;
      invalid_json_rows: number;
      non_object_rows: number;
      overlong_rows: number;
      missing_value_rows: number;
      non_string_value_rows: number;
      filtered_split_rows: number;
    };
    metrics: {
      exact_match: number;
      normalized_exact_match: number;
      token_precision_micro: number;
      token_recall_micro: number;
      token_f1_micro: number;
    };
    confidence_intervals: {
      confidence_level: number;
      method: string;
      exact_match: { low: number; high: number };
      normalized_exact_match: { low: number; high: number };
    };
    truncated: boolean;
    truncation_reasons: string[];
    limits: DatasetScanLimits;
    privacy: { raw_values_returned: false; raw_values_persisted: false };
  };
};

export type WorkspaceEvaluationRunPage = {
  runs: WorkspaceEvaluationRun[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
};

export type WorkflowNodeType =
  | "dataset.profile"
  | "model.inspect"
  | "training.plan"
  | "evaluation.run"
  | "report.export";

export type WorkflowNode = { id: string; type: WorkflowNodeType };
export type WorkflowEdge = { source: string; target: string };
export type WorkspaceWorkflowVersion = {
  revision: number;
  updated_at: string;
  name: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
};
export type WorkspaceWorkflow = {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  schema_version: number;
  revision: number;
  versions: WorkspaceWorkflowVersion[];
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  execution_status: "not_executable";
};
export type WorkflowTemplate = {
  id: string;
  name: string;
  description: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
};

export type WorkflowDryRun = {
  workflow_id: string;
  workflow_revision: number;
  schema_version: number;
  status: "planning_only";
  execution_status: "not_executable";
  executed: false;
  job_created: false;
  node_count: number;
  steps: Array<{ node_id: string; type: WorkflowNodeType; state: "not_run" }>;
  unresolved_inputs: Array<{ node_id: string; type: WorkflowNodeType; reason: string }>;
  resource_summary: {
    available_hardware: HardwareSnapshot;
    estimated_training_plan: TrainingPlan | null;
    estimated_vram_gb: number | null;
    fits_hardware: boolean | null;
    parameters_billions: number | null;
    method: string | null;
  };
  reproducibility_manifest: {
    schema_version: number;
    generated_at: string;
    workflow_id: string;
    workflow_revision: number;
    graph_sha256: string;
    seed: number;
    seed_applied: boolean;
    execution_status: "not_executable";
    software: {
      axiom: string;
      python: string;
      platform: string;
      architecture: string;
      dependencies: Record<string, string | null>;
    };
    hardware: HardwareSnapshot;
    planning_settings: {
      parameter_billions: number | null;
      requested_method: string | null;
      selected_method: string | null;
    };
  };
  warnings: string[];
};

export type McpTool = { name: string; description: string };
export type McpToolProfile = { name: string; allowed_tools: string[] };
export type McpToolPolicy = {
  active_profile: string;
  profiles: McpToolProfile[];
  tools: McpTool[];
};

export type OptimizerProfile = {
  number: number;
  key: string;
  name: string;
  description: string;
  context_tokens: number;
  temperature: number;
  preferred_quantization: string;
};

export type OptimizationPlan = {
  profile: OptimizerProfile;
  model: {
    source: string;
    local_path: string;
    parameter_billions: number;
    estimated_fp16_gb: number;
    files: number;
    weights: string[];
  };
  system: {
    os: string;
    arch: string;
    cpu_count: number;
    ram_gb: number;
    gpu_available: boolean;
    gpu_name: string;
    vram_gb: number;
    disk_free_gb: number;
  };
  optimization: {
    target_tokens_per_second: number;
    recommended_quantization: string;
    recommended_format: string;
    runtime_bundle: boolean;
    benchmark_required: boolean;
  };
};

export type HardwareStatus = {
  cpu_name: string;
  ram_gb: number | null;
  gpu_name: string;
  vram_gb: number | null;
};

type ApiErrorBody = {
  request_id?: unknown;
  detail?: unknown;
  message?: unknown;
  error?: unknown;
};

function messageFromPayload(payload: unknown, fallback: string): string {
  if (!payload || typeof payload !== "object") return fallback;

  const body = payload as ApiErrorBody;
  for (const candidate of [body.detail, body.message, body.error]) {
    if (typeof candidate === "string" && candidate.trim()) return candidate;
    if (candidate && typeof candidate === "object" && !Array.isArray(candidate)) {
      const nestedMessage = (candidate as { message?: unknown }).message;
      if (typeof nestedMessage === "string" && nestedMessage.trim()) return nestedMessage;
    }
    if (Array.isArray(candidate)) {
      const messages = candidate.flatMap((item) => {
        if (!item || typeof item !== "object") return [];
        const entry = item as { loc?: unknown; msg?: unknown };
        const location = Array.isArray(entry.loc) ? entry.loc.join(".") : "";
        const message = typeof entry.msg === "string" ? entry.msg : "Invalid request";
        return [location ? `${location}: ${message}` : message];
      });
      if (messages.length) return messages.join("; ");
    }
  }

  return fallback;
}

async function requestJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const requestId = globalThis.crypto?.randomUUID?.()
    ?? `ui-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 15_000);
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  headers.set("X-Request-ID", requestId);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...init,
      signal: controller.signal,
      headers,
    });
    const raw = await response.text();
    let payload: unknown = null;
    if (raw) {
      try {
        payload = JSON.parse(raw) as unknown;
      } catch {
        payload = raw;
      }
    }

    if (!response.ok) {
      const bodyRequestId = payload && typeof payload === "object"
        ? (payload as ApiErrorBody).request_id
        : undefined;
      const responseRequestId = response.headers.get("X-Request-ID")
        || (typeof bodyRequestId === "string" ? bodyRequestId : requestId);
      throw new Error(`${messageFromPayload(payload, `AXIOM request failed (${response.status})`)} (request ID ${responseRequestId})`);
    }

    return payload as T;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error(`AXIOM backend did not respond within 15 seconds (request ID ${requestId}).`, { cause: error });
    }
    if (error instanceof TypeError) {
      throw new Error(`AXIOM backend is unavailable. Start the local API and try again (request ID ${requestId}).`, { cause: error });
    }
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
}

export const axiomApi = {
  health: () => requestJson<{ status: string; version: string }>("/api/health"),

  models: async () => {
    const result = await axiomApi.modelsPage();
    return result.models;
  },

  modelsPage: (offset = 0, limit = 100) => {
    const query = new URLSearchParams({ offset: String(offset), limit: String(limit) });
    return requestJson<WorkspaceModelPage>(`/api/workspace/models?${query.toString()}`);
  },

  discoverModels: () => requestJson<{ candidates: WorkspaceModelCandidate[]; truncated: boolean }>("/api/workspace/models/discover"),

  inspectModel: (path: string) => requestJson<{ inspection: WorkspaceModelInspection }>("/api/workspace/models/inspect", {
    method: "POST",
    body: JSON.stringify({ path }),
  }),

  addModel: (model: Omit<WorkspaceModel, "id">) =>
    requestJson<{ model: WorkspaceModel }>("/api/workspace/models", {
      method: "POST",
      body: JSON.stringify(model),
    }),

  updateModel: (id: string, changes: Partial<Omit<WorkspaceModel, "id" | "name" | "source">>) =>
    requestJson<{ model: WorkspaceModel }>(`/api/workspace/models/${encodeURIComponent(id)}`, {
      method: "PATCH",
      body: JSON.stringify(changes),
    }),

  removeModel: (id: string) =>
    requestJson<{ removed: WorkspaceModel; weights_deleted: false }>(`/api/workspace/models/${encodeURIComponent(id)}`, {
      method: "DELETE",
    }),

  exportModels: () => requestJson<{ schema_version: number; models: WorkspaceModel[] }>("/api/workspace/models/export"),

  importModels: (payload: { schema_version: number; models: WorkspaceModel[] }) =>
    requestJson<{ imported: number; models: WorkspaceModel[] }>("/api/workspace/models/import", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  datasets: async () => {
    const result = await requestJson<{ datasets: WorkspaceDataset[] }>("/api/workspace/datasets");
    return result.datasets;
  },

  profileDataset: async (
    path: string,
    limits?: DatasetScanLimits,
    options?: {
      duplicate_key_fields?: string[];
      duplicate_rate_threshold?: number | null;
      text_fields?: string[];
      sensitive_field_rules?: string[];
      ignored_sensitive_fields?: string[];
      scan_pii?: boolean;
    },
  ) => {
    const query = new URLSearchParams({ path });
    if (limits) {
      query.set("max_bytes", String(limits.max_bytes));
      query.set("max_rows", String(limits.max_rows));
      query.set("max_line_bytes", String(limits.max_line_bytes));
    }
    options?.duplicate_key_fields?.forEach((field) => query.append("duplicate_key_fields", field));
    options?.text_fields?.forEach((field) => query.append("text_fields", field));
    options?.sensitive_field_rules?.forEach((rule) => query.append("sensitive_field_rules", rule));
    options?.ignored_sensitive_fields?.forEach((field) => query.append("ignored_sensitive_fields", field));
    if (options?.duplicate_rate_threshold !== undefined && options.duplicate_rate_threshold !== null) {
      query.set("duplicate_rate_threshold", String(options.duplicate_rate_threshold));
    }
    if (options?.scan_pii) query.set("scan_pii", "true");
    const result = await requestJson<{ profile: DatasetProfile }>(
      `/api/workspace/dataset-profile?${query.toString()}`,
    );
    return result.profile;
  },

  datasetManifest: async (path: string, maxBytes: number, parentManifestSha256?: string) => {
    const query = new URLSearchParams({ path, max_bytes: String(maxBytes) });
    if (parentManifestSha256) query.set("parent_manifest_sha256", parentManifestSha256);
    const result = await requestJson<{ manifest: DatasetManifest }>(
      `/api/workspace/dataset-manifest?${query.toString()}`,
    );
    return result.manifest;
  },

  previewDatasetCleaning: async (path: string, limits: DatasetScanLimits) => {
    const result = await requestJson<{ preview: DatasetCleaningPreview }>(
      "/api/workspace/dataset-cleaning-preview",
      { method: "POST", body: JSON.stringify({ path, ...limits }) },
    );
    return result.preview;
  },

  datasetQuality: (input: {
    paths: string[];
    required_fields: string[];
    expected_types: Record<string, string>;
    duplicate_key_fields: string[];
    duplicate_rate_threshold: number | null;
    text_fields: string[];
    sensitive_field_rules: string[];
    ignored_sensitive_fields: string[];
    scan_pii: boolean;
    limits: DatasetScanLimits;
  }) => requestJson<DatasetQualityResult>("/api/workspace/dataset-quality", {
    method: "POST",
    body: JSON.stringify({
      paths: input.paths,
      required_fields: input.required_fields,
      expected_types: input.expected_types,
      duplicate_key_fields: input.duplicate_key_fields,
      duplicate_rate_threshold: input.duplicate_rate_threshold,
      text_fields: input.text_fields,
      sensitive_field_rules: input.sensitive_field_rules,
      ignored_sensitive_fields: input.ignored_sensitive_fields,
      scan_pii: input.scan_pii,
      ...input.limits,
    }),
  }),

  trainingPlan: async (parameterBillions: number, method: string) => {
    const query = new URLSearchParams({
      parameter_billions: String(parameterBillions),
      method,
    });
    const result = await requestJson<{ plan: TrainingPlan }>(
      `/api/workspace/training-plan?${query.toString()}`,
      { method: "POST" },
    );
    return result.plan;
  },

  runtime: () => requestJson<RuntimeSnapshot>("/api/workspace/runtime"),

  events: async () => {
    const result = await requestJson<{ events: WorkspaceEvent[] }>("/api/workspace/events");
    return result.events;
  },

  experiments: async (limit = 100) => {
    const result = await axiomApi.experimentsPage({ limit });
    return result.experiments;
  },

  experimentsPage: async (input: { limit?: number; offset?: number; q?: string; tag?: string } = {}) => {
    const query = new URLSearchParams({
      limit: String(input.limit ?? 100),
      offset: String(input.offset ?? 0),
    });
    if (input.q) query.set("q", input.q);
    if (input.tag) query.set("tag", input.tag);
    return requestJson<WorkspaceExperimentPage>(
      `/api/workspace/experiments?${query.toString()}`,
    );
  },

  createExperiment: (experiment: {
    name: string;
    parameter_billions: number;
    method: string;
    plan_snapshot?: TrainingPlan;
    model?: string;
    dataset?: string;
    notes?: string;
    tags?: string[];
  }) =>
    requestJson<{ experiment: WorkspaceExperiment }>("/api/workspace/experiments", {
      method: "POST",
      body: JSON.stringify(experiment),
    }),

  updateExperiment: (id: string, metadata: { name: string; notes: string | null; tags: string[] }) =>
    requestJson<{ experiment: WorkspaceExperiment; plan_immutable: boolean }>(
      `/api/workspace/experiments/${encodeURIComponent(id)}`,
      { method: "PATCH", body: JSON.stringify(metadata) },
    ),

  deleteExperiment: (id: string) =>
    requestJson<{ deleted: WorkspaceExperiment; run_artifacts_deleted: boolean }>(
      `/api/workspace/experiments/${encodeURIComponent(id)}`,
      { method: "DELETE" },
    ),

  evaluationRunsPage: (limit = 20, offset = 0) =>
    requestJson<WorkspaceEvaluationRunPage>(`/api/evaluation/runs?${new URLSearchParams({
      limit: String(limit),
      offset: String(offset),
    }).toString()}`),

  createEvaluationRun: (input: {
    path: string;
    prediction_field: string;
    reference_field: string;
    split_field?: string;
    split_value?: string;
    model_label?: string;
    baseline?: boolean;
    baseline_run_id?: string;
    regression_metric?: "exact_match" | "normalized_exact_match" | "token_f1_micro";
    regression_tolerance?: number;
  }) => requestJson<{ run: WorkspaceEvaluationRun }>("/api/evaluation/runs", {
    method: "POST",
    body: JSON.stringify(input),
  }),

  deleteEvaluationRun: (id: string) =>
    requestJson<{ deleted: WorkspaceEvaluationRun }>(`/api/evaluation/runs/${encodeURIComponent(id)}`, {
      method: "DELETE",
    }),

  workflows: async () => {
    const result = await requestJson<{ workflows: WorkspaceWorkflow[] }>("/api/workflows");
    return result.workflows;
  },

  workflowTemplates: async () => {
    const result = await requestJson<{ templates: WorkflowTemplate[] }>("/api/workflows/templates");
    return result.templates;
  },

  validateWorkflow: (workflow: {
    name: string;
    nodes: WorkflowNode[];
    edges: WorkflowEdge[];
  }) => requestJson<{ valid: boolean; node_count: number; connection_count: number }>(
    "/api/workflows/validate",
    { method: "POST", body: JSON.stringify(workflow) },
  ),

  dryRunWorkflow: (id: string, input: { parameter_billions: number; method: string; seed: number }) =>
    requestJson<{ dry_run: WorkflowDryRun }>(`/api/workflows/${encodeURIComponent(id)}/dry-run`, {
      method: "POST",
      body: JSON.stringify(input),
    }),

  createWorkflow: (workflow: {
    name: string;
    nodes: WorkflowNode[];
    edges: WorkflowEdge[];
  }) => requestJson<{ workflow: WorkspaceWorkflow }>("/api/workflows", {
    method: "POST",
    body: JSON.stringify(workflow),
  }),

  updateWorkflow: (id: string, workflow: {
    name: string;
    nodes: WorkflowNode[];
    edges: WorkflowEdge[];
  }) => requestJson<{ workflow: WorkspaceWorkflow }>(`/api/workflows/${encodeURIComponent(id)}`, {
    method: "PUT",
    body: JSON.stringify(workflow),
  }),

  duplicateWorkflow: (id: string) =>
    requestJson<{ workflow: WorkspaceWorkflow }>(`/api/workflows/${encodeURIComponent(id)}/duplicate`, {
      method: "POST",
    }),

  workflowVersions: async (id: string) => {
    const result = await requestJson<{ versions: WorkspaceWorkflowVersion[] }>(
      `/api/workflows/${encodeURIComponent(id)}/versions`,
    );
    return result.versions;
  },

  mcpToolPolicy: () => requestJson<McpToolPolicy>("/api/security/tool-permissions"),

  saveMcpToolProfile: (name: string, allowedTools: string[]) =>
    requestJson<{ profile: McpToolProfile }>(
      `/api/security/tool-profiles/${encodeURIComponent(name)}`,
      { method: "PUT", body: JSON.stringify({ allowed_tools: allowedTools }) },
    ),

  createMcpToolProfile: (name: string) =>
    requestJson<{ profile: McpToolProfile }>(
      `/api/security/tool-profiles/${encodeURIComponent(name)}`,
      { method: "POST" },
    ),

  setActiveMcpProfile: (name: string) =>
    requestJson<{ active_profile: string }>("/api/security/active-profile", {
      method: "PUT",
      body: JSON.stringify({ name }),
    }),

  optimizerProfiles: async () => {
    const result = await requestJson<{ profiles: OptimizerProfile[] }>("/api/optimizer/profiles");
    return result.profiles;
  },

  optimizationPlan: (model: string, profile: number, targetTokensPerSecond: number) =>
    requestJson<OptimizationPlan>("/api/optimizer/plan", {
      method: "POST",
      body: JSON.stringify({
        model,
        profile,
        target_tokens_per_second: targetTokensPerSecond,
      }),
    }),

  optimizationHardware: () => requestJson<HardwareStatus>("/api/optimization/hardware"),
};
