import { expect, test } from "@playwright/test";
import { ensureAuthenticated } from "./helpers/auth";

const backend = (id: string, name: string, status: "ready" | "setup_required", supportsChat: boolean, models: string[] = []) => ({
  id, name, kind: id === "axiom-native" ? "native" : "openai-compatible",
  endpoint: id === "axiom-native" ? null : "http://127.0.0.1:8080",
  supports_chat: supportsChat, formats: ["local model files"],
  strengths: ["Local execution", "No cloud routing", "Bounded API"],
  tradeoffs: ["Model/backend compatibility must be checked", "Measured speed varies by hardware"],
  best_for: ["balanced"], status, installed: status === "ready", reachable: status === "ready",
  models, model_count: models.length, error: status === "ready" ? null : "Install or configure a compatible local model.",
  scope: id === "axiom-native" ? "in_process_native_engine" : "fixed_loopback_only",
});

test("Engine Fabric compares local engines and routes chat to the chosen service", async ({ page }) => {
  await ensureAuthenticated(page);
  await page.route("**/api/engine/backends**", async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({ json: {
        schema_version: 1, backend_id: "llama-cpp", backend_name: "llama.cpp server", model: "tiny-local",
        response: "A reply from the selected local backend.", done: true, prompt_eval_count: 5,
        eval_count: 7, total_duration_ms: 20, generated_at: "2026-10-24T00:00:00Z",
        execution: "local_loopback", privacy: { prompt_returned: false, response_persisted: false, cloud_provider_used: false },
      } });
      return;
    }
    await route.fulfill({ json: {
      schema_version: 1, checked_at: "2026-10-24T00:00:00Z", host: { os: "Linux", architecture: "x86_64" },
      profile: "balanced",
      profiles: [
        { id: "balanced", label: "Balanced" }, { id: "low-memory", label: "Low memory" },
        { id: "throughput", label: "High throughput" }, { id: "easy-setup", label: "Easy setup" },
        { id: "portable", label: "Portable / quantized" }, { id: "minimal-daemons", label: "Minimal background services" },
      ],
      backends: [
        backend("axiom-native", "AXIOM Native Engine", "setup_required", false),
        backend("ollama", "Ollama", "ready", true, ["qwen2.5:0.5b"]),
        backend("llama-cpp", "llama.cpp server", "ready", true, ["tiny-local"]),
        backend("lm-studio", "LM Studio local server", "setup_required", true),
        backend("vllm", "vLLM local server", "setup_required", true),
        backend("llama-cpp-python", "llama-cpp-python server", "setup_required", true),
      ],
      recommendation: { profile: "balanced", backend_id: "llama-cpp", name: "llama.cpp server", status: "ready", reason: "A ready quantized local runtime is available." },
      security: { network_scope: "IPv4 loopback only", environment_proxies_used: false, remote_endpoints_configurable: false, credentials_sent: false, model_downloads_started: false, processes_launched: false },
      scope_note: "Only local APIs were inspected.",
    } });
  });
  await page.goto("/?page=runtime");
  await expect(page.getByRole("heading", { name: "Choose the right local engine" })).toBeVisible();
  await expect(page.getByText("AXIOM Native Engine", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Recommended for this profile").first()).toBeVisible();
  await page.getByLabel("External local backend").selectOption("llama-cpp");
  await page.getByLabel("Model ID").fill("tiny-local");
  await page.getByPlaceholder("Ask the selected local model to do something…").fill("Say hello locally.");
  await page.getByRole("button", { name: "Run on selected engine" }).click();
  await expect(page.getByRole("region", { name: "Engine Fabric response" })).toContainText("A reply from the selected local backend.");
});
