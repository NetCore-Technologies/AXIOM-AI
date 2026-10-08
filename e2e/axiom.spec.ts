import { expect, test } from "@playwright/test";

test.describe("AXIOM Control Center", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    await page.reload();
  });

  test("completes first boot, authenticates, and navigates the workspace", async ({ page }) => {
    await expect(page.getByRole("heading", { name: "Build AI. Own AI." })).toBeVisible();

    await page.getByRole("button", { name: "Begin setup" }).click();
    await page.getByRole("textbox", { name: "Username", exact: true }).fill("operator");
    await page.getByRole("textbox", { name: "Password", exact: true }).fill("SecurePass1");
    await page.getByRole("textbox", { name: "Confirm password", exact: true }).fill("SecurePass");
    await expect(page.getByRole("button", { name: "Create administrator" })).toBeDisabled();

    await page.getByRole("textbox", { name: "Confirm password", exact: true }).fill("SecurePass1");
    await page.getByRole("button", { name: "Create administrator" }).click();
    await expect(page.getByText("Administrator created.")).toBeVisible();
    await expect(page.getByRole("heading", { name: /Welcome back[.!]?/ })).toBeVisible({ timeout: 15_000 });

    await page.getByRole("textbox", { name: "Username", exact: true }).fill("operator");
    await page.getByRole("textbox", { name: "Password", exact: true }).fill("SecurePass1");
    await page.getByRole("button", { name: "Sign in" }).click();

    await expect(page.getByRole("heading", { name: /Good (morning|afternoon|evening), operator\./ })).toBeVisible();
    await expect(page.getByText("No frontend API contract found")).toBeVisible();

    await page.getByRole("button", { name: /Models/ }).first().click();
    await expect(page.getByRole("heading", { name: "Models" })).toBeVisible();
    await expect(page.getByRole("button", { name: /axiom model list/ })).toBeVisible();
  });

  test("rejects invalid credentials without leaving the login screen", async ({ page }) => {
    await page.getByRole("button", { name: "Begin setup" }).click();
    await page.getByRole("textbox", { name: "Username", exact: true }).fill("operator");
    await page.getByRole("textbox", { name: "Password", exact: true }).fill("SecurePass1");
    await page.getByRole("textbox", { name: "Confirm password", exact: true }).fill("SecurePass1");
    await page.getByRole("button", { name: "Create administrator" }).click();
    await expect(page.getByRole("heading", { name: /Welcome back[.!]?/ })).toBeVisible({ timeout: 15_000 });

    await page.getByRole("textbox", { name: "Password", exact: true }).fill("WrongPass1");
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByRole("alert")).toContainText("Incorrect administrator name or password");
    await expect(page.getByRole("heading", { name: /Welcome back[.!]?/ })).toBeVisible();
  });
});
