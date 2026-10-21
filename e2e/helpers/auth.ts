import { expect, type Page } from "@playwright/test";

const E2E_USERNAME = "axiom-e2e-admin";
const E2E_PASSWORD = "AxiomTest123";

export async function ensureAuthenticated(page: Page): Promise<void> {
  // Open the app origin, then reset only this test browser's AXIOM auth state.
  await page.goto("/");

  await page.evaluate(() => {
    for (const key of [
      "axiom-booted",
      "axiom-setup",
      "axiom-admin-v2",
      "axiom-admin",
    ]) {
      localStorage.removeItem(key);
    }
    sessionStorage.removeItem("axiom-session");
  });

  // Reload once with predictable first-boot state.
  await page.reload();

  page.on("pageerror", (error) => {
    console.error("[AXIOM browser error]", error.message);
  });

  const beginSetup = page.getByRole("button", { name: /Begin setup/i });
  await expect(beginSetup).toBeVisible({ timeout: 15_000 });
  await beginSetup.click();

  await expect(page.locator("#setup-username")).toBeVisible();
  await page.locator("#setup-username").fill(E2E_USERNAME);
  await page.locator("#setup-password").fill(E2E_PASSWORD);
  await page.locator("#setup-confirm").fill(E2E_PASSWORD);

  const createButton = page.getByRole("button", {
    name: /Create administrator/i,
  });
  await expect(createButton).toBeEnabled();
  await createButton.click();

  await expect(
    page.getByRole("heading", { name: "Administrator created." }),
  ).toBeVisible({ timeout: 10_000 });

  const signInHeading = page.getByRole("heading", { name: "Sign in" });
  await expect(signInHeading).toBeVisible({ timeout: 15_000 });

  await page.locator("#login-username").fill(E2E_USERNAME);
  await page.locator("#login-password").fill(E2E_PASSWORD);
  await page.getByRole("button", { name: /^Sign in$/i }).click();

  await expect(page.getByLabel("Primary navigation")).toBeVisible({
    timeout: 15_000,
  });
}
