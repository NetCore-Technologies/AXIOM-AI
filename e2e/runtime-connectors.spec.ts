import { expect, test } from "@playwright/test";
import { ensureAuthenticated } from "./helpers/auth";

test("Runtime page displays passive connector discovery without claiming connection", async ({ page }) => {
  await ensureAuthenticated(page);
  await page.route("**/api/workspace/runtime", (route) => route.fulfill({
    json: {
      status: "offline",
      hardware: {
        os_name: "Linux", architecture: "x86_64", cpu_cores: 8,
        ram_gb: 16, gpu_name: null, vram_gb: null, cuda_available: false,
      },
    },
  }));
  await page.route("**/api/diagnostics/runtime-connectors", (route) => route.fulfill({
    json: {
      schema_version: 1,
      discovery_mode: "passive_local_discovery",
      checked_at: "2026-10-20T00:00:00Z",
      scope_note: "Presence is not a connection.",
      connectors: [
        { id: "ollama", name: "Ollama", kind: "executable", present: true, status: "discovered_not_connected", potential_capabilities: ["local_inference"], evidence: "found on PATH", connection_checked: false, note: "No process contacted." },
        { id: "vllm-cli", name: "vLLM CLI", kind: "executable", present: false, status: "not_detected", potential_capabilities: ["serving"], evidence: "not present", connection_checked: false, note: "No process contacted." },
      ],
    },
  }));

  await page.goto("/?page=runtime");
  await expect(page.getByRole("heading", { name: "Runtime connectors" })).toBeVisible();
  await expect(page.getByText("Ollama", { exact: true })).toBeVisible();
  await expect(page.getByText("DISCOVERED", { exact: true })).toBeVisible();
  await expect(page.getByText("vLLM CLI", { exact: true })).toBeVisible();
  await expect(page.locator("body")).toContainText("does not start processes");
  await expect(page.locator("body")).not.toContainText("CONNECTED");
});
