import { expect, type Page } from "@playwright/test";

const E2E_USERNAME = "axiom-e2e-admin";
const E2E_PASSWORD = "AxiomTest123";

/** Complete the real local first-boot/setup/sign-in flow for an isolated browser context. */
export async function ensureAuthenticated(page: Page): Promise<void> {
  await page.goto("/");

  if (await page.getByLabel("Primary navigation").isVisible().catch(() => false)) {
    return;
  }

  const beginSetup = page.getByRole("button", { name: /Begin setup/i });
  if (await beginSetup.isVisible().catch(() => false)) {
    await beginSetup.click();
    await page.locator("#setup-username").fill(E2E_USERNAME);
    await page.locator("#setup-password").fill(E2E_PASSWORD);
    await page.locator("#setup-confirm").fill(E2E_PASSWORD);
    await page.getByRole("button", { name: /Create administrator/i }).click();
    await expect(page.getByRole("heading", { name: "Administrator created." })).toBeVisible();
  }

  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible({ timeout: 6_000 });
  await page.locator("#login-username").fill(E2E_USERNAME);
  await page.locator("#login-password").fill(E2E_PASSWORD);
  await page.getByRole("button", { name: /^Sign in$/i }).click();
  await expect(page.getByLabel("Primary navigation")).toBeVisible({ timeout: 6_000 });
}
