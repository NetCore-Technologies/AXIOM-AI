import { expect, test } from "@playwright/test";
import { ensureAuthenticated } from "./helpers/auth";

test.describe("AXIOM local AI Toolkit", () => {
  test.beforeEach(async ({ page }) => {
    await ensureAuthenticated(page);
    await page.goto("/?page=toolkit");
  });

  test("exposes all 120 utility actions through the Control Center", async ({ page }) => {
    await expect(page.getByRole("heading", { name: "AI Toolkit" })).toBeVisible();
    await expect(page.getByText("120 of 120 shown", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: /FP16 weight footprint/ })).toBeVisible();
    await expect(page.getByRole("button", { name: /SHA-256 digest/ })).toHaveCount(1);
    await expect(page.getByRole("button", { name: /Workflow topological order/ })).toHaveCount(1);
  });

  test("runs a deterministic model-weight estimate locally", async ({ page }) => {
    await page.getByRole("button", { name: "Run utility" }).click();
    await expect(page.locator(".api-playground-json")).toContainText("14 GB estimated weight storage");
    await expect(page.getByText(/completed locally/)).toBeVisible();
  });

  test("searches and runs the JSONL validator", async ({ page }) => {
    await page.getByRole("textbox", { name: "Search toolkit utilities" }).fill("JSONL validity");
    await page.getByRole("button", { name: /JSONL validity check/ }).click();
    await page.getByRole("textbox", { name: "Text A" }).fill('{"ok":true}\nnot-json\n[]');
    await page.getByRole("button", { name: "Run utility" }).click();
    const result = page.locator(".api-playground-json");
    await expect(result).toContainText('"malformed_json_lines": 1');
    await expect(result).toContainText('"valid_non_object_lines": 1');
    await expect(result).toContainText('"valid_object_lines": 1');
  });

  test("keeps the path-traversal checker local and labels its limits", async ({ page }) => {
    await page.getByRole("textbox", { name: "Search toolkit utilities" }).fill("Path traversal guard");
    await page.getByRole("button", { name: /Path traversal guard/ }).click();
    await page.getByRole("textbox", { name: "Text A" }).fill("../outside/weights");
    await page.getByRole("button", { name: "Run utility" }).click();
    await expect(page.locator(".api-playground-json")).toContainText('"parent_traversal": true');
    await expect(page.getByText(/do not call the AXIOM API/i)).toBeVisible();
  });

  test("smoke-tests representative utilities across all 12 categories locally", async ({ page }) => {
    test.setTimeout(45_000);
    const apiRequests: string[] = [];
    page.on("request", (request) => {
      const url = new URL(request.url());
      if (url.pathname.startsWith("/api/")) apiRequests.push(url.pathname);
    });

    const cases: Array<{
      search: string;
      title: string;
      a?: string;
      b?: string;
      c?: string;
      textA?: string;
      textB?: string;
      expected: string;
    }> = [
      { search: "FP16 weight footprint", title: "FP16 weight footprint", a: "7", expected: "14 GB estimated weight storage" },
      { search: "Q4 versus FP16 savings", title: "Q4 versus FP16 savings", a: "7", expected: '"estimated_savings_GB": "10.5"' },
      { search: "Effective batch size", title: "Effective batch size", a: "4", b: "8", c: "2", expected: '"effective_batch_size": 64' },
      { search: "JSONL validity check", title: "JSONL validity check", textA: '{"id":1}\\nnot-json\\n[]', expected: '"malformed_json_lines": 1' },
      { search: "Wilson score interval", title: "Wilson score interval", a: "9", b: "10", expected: '"wilson_95_low_percent"' },
      { search: "Measured tokens per second", title: "Measured tokens per second", a: "120", b: "4", expected: '"tokens_per_second": "30"' },
      { search: "Memory fit with reserve", title: "Memory fit with reserve", a: "7", b: "16", c: "20", expected: '"estimated_fit": true' },
      { search: "Path traversal guard", title: "Path traversal guard", textA: "../models/private", expected: '"parent_traversal": true' },
      { search: "Workflow cycle detector", title: "Workflow cycle detector", textA: '{"nodes":["a","b"],"edges":[["a","b"],["b","a"]]}', expected: '"has_cycle": true' },
      { search: "Retry schedule", title: "Retry schedule", a: "3", b: "100", c: "500", expected: '"delays_ms": [\\n    100,\\n    200,\\n    400' },
      { search: "Prompt template renderer", title: "Prompt template renderer", textA: "Hello {{user}}", textB: '{"user":"AXIOM"}', expected: "Hello AXIOM" },
      { search: "Semantic version parser", title: "Semantic version parser", textA: "1.2.3-beta.1", expected: '"valid": true' },
    ];

    for (const item of cases) {
      await page.getByRole("textbox", { name: "Search toolkit utilities" }).fill(item.search);
      await page.getByRole("button", { name: new RegExp(item.title, "i") }).click();
      if (item.a !== undefined) await page.getByRole("spinbutton", { name: "Number A" }).fill(item.a);
      if (item.b !== undefined) await page.getByRole("spinbutton", { name: "Number B" }).fill(item.b);
      if (item.c !== undefined) await page.getByRole("spinbutton", { name: "Number C" }).fill(item.c);
      if (item.textA !== undefined) await page.getByRole("textbox", { name: "Text A" }).fill(item.textA);
      if (item.textB !== undefined) await page.getByRole("textbox", { name: "Text B" }).fill(item.textB);
      await page.getByRole("button", { name: "Run utility" }).click();
      await expect(page.locator(".api-playground-json"), item.title).toContainText(item.expected);
    }
    expect(apiRequests, "toolkit operations should not call the API").toEqual([]);
  });

  test("quotes shell values and keeps policy review default-deny", async ({ page }) => {
    await page.getByRole("textbox", { name: "Search toolkit utilities" }).fill("Read-only curl builder");
    await page.getByRole("button", { name: /Read-only curl builder/ }).click();
    await page.getByRole("textbox", { name: "Text A" }).fill("https://example.com/?q=$HOME");
    await page.getByRole("button", { name: "Run utility" }).click();
    const shellResult = page.locator(".api-playground-json");
    await expect(shellResult).toContainText("'https://example.com/?q=$HOME'");

    await page.getByRole("textbox", { name: "Search toolkit utilities" }).fill("Default-deny tool policy");
    await page.getByRole("button", { name: /Default-deny tool policy/ }).click();
    await page.getByRole("textbox", { name: "Text A" }).fill('[{"name":"reader","allowed":true,"read":true},{"name":"unknown","allowed":true,"read":true,"admin":true}]');
    await page.getByRole("button", { name: "Run utility" }).click();
    await expect(page.locator(".api-playground-json")).toContainText("candidate read-only allow");
    await expect(page.locator(".api-playground-json")).toContainText("unknown_permission_fields");
    await expect(page.locator(".api-playground-json")).toContainText("deny by default");
  });
});
