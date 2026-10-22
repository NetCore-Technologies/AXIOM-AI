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
});
