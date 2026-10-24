import { expect, test } from "@playwright/test";
import { ensureAuthenticated } from "./helpers/auth";

test("Runtime GUI submits bounded prompts to the local inference API and displays the result", async ({ page }) => {
  await ensureAuthenticated(page);
  await page.route("**/api/workspace/runtime", (route) => route.fulfill({ json: {
    status: "offline",
    hardware: { os_name: "Linux", architecture: "x86_64", cpu_cores: 8, ram_gb: 16, gpu_name: null, vram_gb: null, cuda_available: false },
  } }));
  await page.route("**/api/inference/status", (route) => route.fulfill({ json: {
    backend: "ollama", endpoint: "http://127.0.0.1:11434", runtime_installed: true,
    status: "online", models: ["qwen2.5:0.5b"], error: null, checked_at: "2026-10-21T00:00:00Z",
  } }));
  await page.route("**/api/diagnostics/runtime-connectors", (route) => route.fulfill({ json: {
    schema_version: 1, discovery_mode: "passive_local_discovery", checked_at: "2026-10-21T00:00:00Z",
    scope_note: "Presence is not a connection.", connectors: [],
  } }));
  let received: Record<string, unknown> | null = null;
  await page.route("**/api/inference/generate/stream", async (route) => {
    received = route.request().postDataJSON() as Record<string, unknown>;
    const events = [
      { type: "token", token: "Hello from the mocked local model." },
      { type: "complete", result: {
        request_id: "stream-test-request", model: "qwen2.5:0.5b", response: "", done: true,
        done_reason: "stop", prompt_eval_count: 4, eval_count: 6,
        total_duration_ms: 21.4, generated_at: "2026-10-21T00:00:00Z", execution: "local",
      } },
    ];
    await route.fulfill({ status: 200, contentType: "application/x-ndjson", body: events.map((event) => JSON.stringify(event)).join("\n") + "\n" });
  });


  await page.goto("/?page=runtime");
  await expect(page.getByRole("heading", { name: "Local model inference" })).toBeVisible();
  await expect(page.getByText("OLLAMA ONLINE", { exact: true })).toBeVisible();
  await page.getByPlaceholder("Ask your local model to do something…").fill("Say hello in one sentence.");
  await page.getByRole("button", { name: "Run locally" }).click();
  await expect(page.getByTestId("local-inference-output")).toContainText("Hello from the mocked local model.");
  expect(received).toMatchObject({ model: "qwen2.5:0.5b", prompt: "Say hello in one sentence.", num_predict: 256, temperature: 0.7 });
});


test("Runtime can stop a streamed local Ollama generation and retain partial output", async ({ page }) => {
  await ensureAuthenticated(page);
  await page.route("**/api/workspace/runtime", (route) => route.fulfill({ json: {
    status: "offline",
    hardware: { os_name: "Linux", architecture: "x86_64", cpu_cores: 8, ram_gb: 16, gpu_name: null, vram_gb: null, cuda_available: false },
  } }));
  await page.route("**/api/inference/status", (route) => route.fulfill({ json: {
    backend: "ollama", endpoint: "http://127.0.0.1:11434", runtime_installed: true,
    status: "online", models: ["qwen2.5:0.5b"], error: null, checked_at: "2026-10-21T00:00:00Z",
  } }));
  await page.route("**/api/diagnostics/runtime-connectors", (route) => route.fulfill({ json: {
    schema_version: 1, discovery_mode: "passive_local_discovery", checked_at: "2026-10-21T00:00:00Z",
    scope_note: "Presence is not a connection.", connectors: [],
  } }));

  let unblock: (() => void) | undefined;
  let routeStarted: (() => void) | undefined;
  const holdResponse = new Promise<void>((resolve) => { unblock = resolve; });
  const routeReady = new Promise<void>((resolve) => { routeStarted = resolve; });
  await page.route("**/api/inference/generate/stream", async (route) => {
    routeStarted?.();
    await holdResponse;
    const events = [
      { type: "token", token: "Partial answer" },
      { type: "complete", result: {
        request_id: "stopped-stream-test", model: "qwen2.5:0.5b", response: "",
        done: true, done_reason: "stop", prompt_eval_count: 3, eval_count: 2,
        total_duration_ms: 5, generated_at: "2026-10-21T00:00:00Z", execution: "local",
      } },
    ];
    try {
      await route.fulfill({ status: 200, contentType: "application/x-ndjson", body: events.map((event) => JSON.stringify(event)).join("\n") + "\n" });
    } catch {
      // The test deliberately aborts this request before releasing the mock response.
    }
  });

  await page.goto("/?page=runtime");
  await page.getByPlaceholder("Ask your local model to do something…").fill("Write a long response.");
  await page.getByRole("button", { name: "Run locally" }).click();
  await routeReady;
  await expect(page.getByRole("button", { name: "Stop generation" })).toBeVisible();
  await page.getByRole("button", { name: "Stop generation" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Generation stopped. Partial output is retained." })).toBeVisible();
  unblock?.();
});
