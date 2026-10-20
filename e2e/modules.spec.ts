import { expect, test } from "@playwright/test";

test.describe("AXIOM module explorer", () => {
  test("lists existing GUI surfaces and honestly labels CLI-only entry points", async ({ page }) => {
    await page.goto("/?page=modules");

    await expect(page.getByRole("heading", { name: "Platform module directory" })).toBeVisible();
    await expect(page.getByRole("group", { name: "Agent Optimizer" })).toBeVisible();
    await expect(page.getByRole("group", { name: "Dataset engineering and quality" })).toBeVisible();
    await expect(page.getByRole("group", { name: "Developer tool catalog" })).toContainText("CLI surface");
    await expect(page.getByRole("group", { name: "Training planner and experiments" })).toContainText("Planning only");
    await expect(page.getByRole("link", { name: "Open API" })).toHaveAttribute("href", "/api/docs");
  });

  test("searches the directory and opens the existing page instead of simulating a command", async ({ page }) => {
    await page.goto("/?page=modules");
    await page.getByRole("textbox", { name: "Search AXIOM modules" }).fill("dataset quality");

    const datasetModule = page.getByRole("group", { name: "Dataset engineering and quality" });
    await expect(datasetModule).toBeVisible();
    await expect(page.getByRole("group", { name: "SuperCompress context utilities" })).toHaveCount(0);

    await datasetModule.getByRole("button", { name: "Open" }).click();
    await expect(page).toHaveURL(/page=datasets/);
    await expect(page.locator(".page-header h1")).toContainText("Datasets");
  });

  test("does not imply that roadmap planning work is already delivered", async ({ page }) => {
    await page.goto("/?page=modules");
    await expect(page.getByText(/does not mark planned roadmap items as implemented/i)).toBeVisible();
    await expect(page.getByRole("group", { name: "Workflow builder" })).toContainText("Design only");
  });
});
