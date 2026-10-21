import { expect, type Page } from "@playwright/test";

const E2E_USERNAME = "axiom-e2e-admin";
const E2E_PASSWORD = "AxiomTest123";

/** Complete first boot, administrator setup, and sign-in when required. */
export async function ensureAuthenticated(page: Page): Promise<void> {
  await page.goto("/");

  const navigation = page.getByLabel("Primary navigation");
  if (await navigation.isVisible().catch(() => false)) {
    return;
  }

  const beginSetup = page.getByRole("button", { name: /Begin setup/i });
  const usernameField = page.locator("#setup-username");
  const signInHeading = page.getByRole("heading", { name: "Sign in" });

  // Wait until the app has settled into one of its authentication states.
  await expect(
    beginSetup.or(usernameField).or(signInHeading),
  ).toBeVisible({ timeout: 10_000 });

  if (await beginSetup.isVisible().catch(() => false)) {
    await beginSetup.click();
  }

  // Also handle a browser already on the administrator setup screen.
  if (await usernameField.isVisible().catch(() => false)) {
    await usernameField.fill(E2E_USERNAME);
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
  }

  await expect(signInHeading).toBeVisible({ timeout: 10_000 });

  await page.locator("#login-username").fill(E2E_USERNAME);
  await page.locator("#login-password").fill(E2E_PASSWORD);
  await page.getByRole("button", { name: /^Sign in$/i }).click();

  await expect(navigation).toBeVisible({ timeout: 10_000 });
}
