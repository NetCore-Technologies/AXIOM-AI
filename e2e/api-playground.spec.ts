import { expect, test } from "@playwright/test";
import { ensureAuthenticated } from "./helpers/auth";

test("API Playground exposes bounded read-only endpoint choices", async ({ page }) => {
  const requests: Array<{ url: string; method: string; postData: string | null }> = [];
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    requests.push({ url: new URL(request.url()).pathname + new URL(request.url()).search, method: request.method(), postData: request.postData() });
    const pathname = new URL(request.url()).pathname;
    if (pathname.endsWith("/health")) {
      await route.fulfill({ json: { status: "ok", version: "test" } });
    } else if (pathname.endsWith("/meta")) {
      await route.fulfill({ json: { api_contract_version: 1, application_version: "test" } });
    } else if (pathname.endsWith("/runtime")) {
      await route.fulfill({ json: { status: "offline", hardware: {} } });
    } else if (pathname.endsWith("/models")) {
      await route.fulfill({ json: { models: [], total: 0, limit: 5, offset: 0, has_more: false } });
    } else if (pathname.endsWith("/datasets")) {
      await route.fulfill({ json: { datasets: [] } });
    } else if (pathname.endsWith("/events")) {
      await route.fulfill({ json: { events: [] } });
    } else if (pathname.endsWith("/diagnostics/workspace")) {
      await route.fulfill({ json: { checks: [], status: "ok" } });
    } else if (pathname.endsWith("/diagnostics/roadmap") || pathname.endsWith("/diagnostics/runtime-connectors")) {
      await route.fulfill({ json: { items: [], total: 120, summary: {} } });
    } else {
      await route.fulfill({ status: 404, json: { detail: "Not found" } });
    }
  });

  await ensureAuthenticated(page);
  await page.goto("/?page=api-playground");
  await expect(page.getByRole("heading", { name: "Choose an endpoint" })).toBeVisible();
  const select = page.getByLabel("Endpoint");
  const options = await select.locator("option").evaluateAll((nodes) => nodes.map((node) => (node as HTMLOptionElement).value));
  expect(options.length).toBeGreaterThanOrEqual(8);
  expect(options.every((option) => option.startsWith("/api/"))).toBe(true);
  expect(options.some((option) => option.includes("/api/jobs") || option.includes("/delete"))).toBe(false);

  await select.selectOption("/api/meta");
  await page.getByRole("button", { name: "Run read-only request" }).click();
  await expect(page.locator(".api-playground-json")).toContainText('"api_contract_version": 1');
  expect(requests.length).toBeGreaterThan(0);
  expect(requests.every((request) => request.method === "GET" && request.postData === null)).toBe(true);
});
