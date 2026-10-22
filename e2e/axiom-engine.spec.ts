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
    engine: "axiom-local-engine", ready: true, packages: { torch: true, transformers: true, peft: true },
    versions: { torch: "2.9.0", transformers: "5.0.0", peft: "0.21.0" },
    loaded: engineLoaded, architecture: engineLoaded ? "LlamaForCausalLM" : null, model_loading: "local_files_only", remote_code: false,
    setup_note: "AXIOM Engine is ready for local Transformers causal-LM checkpoints.",
    scope_note: "Local model files only.", checked_at: "2026-10-21T00:00:00Z",
  } }));
  await page.route("**/api/engine/generate", (route) => {
    engineLoaded = true;
    return route.fulfill({ json: {
      engine: "axiom-local-engine", model: "llama-test", architecture: "LlamaForCausalLM",
      adapter: "my-lora-adapter", response: "AXIOM local engine test response.",
      prompt_tokens: 5, completion_tokens: 6, elapsed_ms: 120.5,
      generated_at: "2026-10-21T00:00:00Z", local_only: true,
    } });
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
  await expect(engine.getByText("ENGINE READY")).toBeVisible();

  await engine.getByLabel("Local Llama / Transformers model directory").fill("/models/llama-test");
  await engine.getByLabel("Optional LoRA adapter directory").fill("/runs/my-lora-adapter");
  await engine.getByLabel("Prompt").fill("Say hello.");
  await engine.getByRole("button", { name: "Run with AXIOM Engine" }).click();

  await expect(engine.getByTestId("axiom-engine-output")).toContainText("AXIOM local engine test response.");
  await expect(engine).toContainText("LlamaForCausalLM");
  await expect(engine.getByRole("button", { name: "Unload model" })).toBeVisible();

  await engine.getByRole("button", { name: "Unload model" }).click();
  await expect(engine.getByRole("status")).toContainText("released its loaded model and tokenizer references");
  await expect(engine.getByRole("button", { name: "Unload model" })).toHaveCount(0);
  expect(unloadCalls).toBe(1);
});
