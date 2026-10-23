import { expect, test } from "@playwright/test";
import { ensureAuthenticated } from "./helpers/auth";

test("Runtime page exposes direct AXIOM Engine inference with local model and adapter paths, then unloads it", async ({ page }) => {
  await ensureAuthenticated(page);
  let engineLoaded = false;
  let unloadCalls = 0;

  await page.route("**/api/workspace/runtime", (route) => route.fulfill({
    json: {
      status: "ready",
      hardware: {
        os_name: "Linux", architecture: "x86_64", cpu_cores: 8,
        ram_gb: 16, gpu_name: null, vram_gb: null, cuda_available: false,
      },
    },
  }));
  await page.route("**/api/inference/status", (route) => route.fulfill({ json: {
    backend: "ollama", endpoint: "http://127.0.0.1:11434", runtime_installed: false,
    status: "offline", models: [], error: "Ollama is offline for this test.", checked_at: "2026-10-21T00:00:00Z",
  } }));
  await page.route("**/api/diagnostics/runtime-connectors", (route) => route.fulfill({ json: {
    schema_version: 1, discovery_mode: "passive_local_discovery", checked_at: "2026-10-21T00:00:00Z",
    scope_note: "Passive discovery only.",
    connectors: [],
  } }));
  await page.route("**/api/engine/status", (route) => route.fulfill({ json: {
    engine: "axiom-native-pytorch-llama", ready: true, packages: { torch: true, tokenizers: true, safetensors: true },
    versions: { torch: "2.9.0", tokenizers: "0.22.0", safetensors: "0.6.0" },
    minimum_versions: { torch: "2.2.0", tokenizers: "0.19.0", safetensors: "0.4.0" },
    problems: [], execution_backend: "pytorch-native-axiom", transformers_generation_used: false, ollama_used: false,
    supported_model_types: ["llama", "mistral"], supported_weights: ["safetensors"],
    loaded: engineLoaded, architecture: engineLoaded ? "LlamaForCausalLM" : null, model_loading: "local_safetensors_only", remote_code: false,
    setup_note: "AXIOM Native Engine is ready for supported local Llama/Mistral safetensors checkpoints.",
    scope_note: "AXIOM-owned Llama/Mistral forward pass and autoregressive KV-cache decoder.", checked_at: "2026-10-22T00:00:00Z",
  } }));
  await page.route("**/api/engine/models", (route) => route.fulfill({ json: {
    schema_version: 1,
    models: [{
      path: "/models/llama-test", name: "llama-test", model_type: "llama",
      architecture: "LlamaForCausalLM", weight_format: "safetensors", ready_for_native_attempt: true,
    }],
    adapters: [{ path: "/runs/my-lora-adapter", name: "my-lora-adapter", weight_format: "safetensors LoRA" }],
    truncated: false, scope_note: "Metadata-only discovery under trusted local roots; weights are validated on run.",
  } }));
  await page.route("**/api/engine/generate/stream", (route) => {
    engineLoaded = true;
    const completed = {
      engine: "axiom-native-engine", execution_backend: "pytorch-native-axiom", transformers_generation_used: false, ollama_used: false,
      model: "llama-test", architecture: "LlamaForCausalLM", model_type: "llama", device: "cpu", checkpoint_format: "safetensors", decoder: "axiom-autoregressive-kv-cache",
      adapter: "my-lora-adapter", response: "AXIOM local engine test response.",
      prompt_tokens: 5, completion_tokens: 6, elapsed_ms: 120.5,
      generated_at: "2026-10-21T00:00:00Z", local_only: true,
    };
    return route.fulfill({
      status: 200,
      contentType: "application/x-ndjson",
      body: [
        JSON.stringify({ type: "token", response: "AXIOM local", completion_tokens: 2 }),
        JSON.stringify({ type: "complete", result: completed }),
      ].join("\n") + "\n",
    });
  });
  await page.route("**/api/engine/unload", (route) => {
    unloadCalls += 1;
    engineLoaded = false;
    return route.fulfill({ json: {
      schema_version: 1, unloaded: true, loaded: false,
      scope_note: "The loaded model and tokenizer references were released by AXIOM. Framework or OS-level allocators may retain some reserved memory.",
    } });
  });

  await page.goto("/?page=runtime");

  const engine = page.locator(".axiom-engine-panel");
  await expect(engine.getByRole("heading", { name: "AXIOM Local Engine" })).toBeVisible();
  await expect(engine).toContainText("own PyTorch Llama/Mistral forward pass");
  await expect(engine).toContainText("safetensors");
  await expect(engine.getByText("ENGINE READY")).toBeVisible();

  await engine.getByLabel("Select discovered native model").selectOption("/models/llama-test");
  await expect(engine.getByLabel("Local Llama / Mistral model directory")).toHaveValue("/models/llama-test");
  await engine.getByLabel("Select discovered LoRA adapter").selectOption("/runs/my-lora-adapter");
  await expect(engine.getByLabel("Optional LoRA adapter directory")).toHaveValue("/runs/my-lora-adapter");
  await engine.getByLabel("AXIOM Native Engine prompt").fill("Say hello.");
  await engine.getByRole("button", { name: "Run with AXIOM Engine" }).click();

  await expect(engine.getByTestId("axiom-engine-output")).toContainText("AXIOM local engine test response.");
  await expect(engine).toContainText("LlamaForCausalLM");
  await expect(engine.getByRole("button", { name: "Unload model" })).toBeVisible();

  await engine.getByRole("button", { name: "Unload model" }).click();
  await expect(engine.getByRole("status")).toContainText("released its loaded model and tokenizer references");
  await expect(engine.getByRole("button", { name: "Unload model" })).toHaveCount(0);
  expect(unloadCalls).toBe(1);

  // Starting a second request and stopping it must keep the UI responsive and
  // preserve the partial-output/cancellation status rather than reporting a
  // successful completion.
  await page.route("**/api/engine/generate/stream", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 3000));
    try {
      await route.fulfill({
        status: 200,
        contentType: "application/x-ndjson",
        body: JSON.stringify({
          type: "complete",
          result: {
            engine: "axiom-native-engine", execution_backend: "pytorch-native-axiom",
            transformers_generation_used: false, ollama_used: false,
            model: "llama-test", architecture: "LlamaForCausalLM", model_type: "llama",
            adapter: null, device: "cpu", checkpoint_format: "safetensors",
            decoder: "axiom-autoregressive-kv-cache", response: "Should not arrive",
            prompt_tokens: 3, completion_tokens: 1, elapsed_ms: 100,
            generated_at: "2026-10-22T00:00:00Z", local_only: true,
          },
        }) + "\\n",
      });
    } catch {
      // The browser has already aborted the request, which is the case under test.
    }
  });
  await engine.getByRole("button", { name: "Run with AXIOM Engine" }).click();
  await expect(engine.getByRole("button", { name: "Stop generation" })).toBeVisible();
  await engine.getByRole("button", { name: "Stop generation" }).click();
  await expect(engine.getByRole("alert")).toContainText("Generation cancelled after 0 token(s)");
  await expect(engine.getByTestId("axiom-engine-output")).toHaveCount(0);
});
