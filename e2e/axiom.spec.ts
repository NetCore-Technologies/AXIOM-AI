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
    await expect(page.getByText("AXIOM backend")).toBeVisible();

    await page.getByRole("button", { name: /Models/ }).first().click();
    await expect(page.getByRole("heading", { name: "Models" })).toBeVisible();
    await expect(page.getByRole("button", { name: /axiom model list/ })).toBeVisible();

    await page.getByRole("button", { name: "Agent Optimizer" }).click();
    await expect(page.getByRole("heading", { name: "Make a large model fit your device" })).toBeVisible();
    await expect(page.getByRole("button", { name: "OPTIMIZE MODEL" })).toBeDisabled();

    await page.getByRole("button", { name: "Quantization Lab" }).click();
    await expect(page.getByRole("heading", { name: "Make a large model fit your device" })).toBeVisible();
    await expect(page.getByText("AXIOM / QUANTIZATION LAB")).toBeVisible();

    await page.getByRole("button", { name: "Collapse sidebar" }).click();
    await expect(page.locator(".app-shell")).toHaveClass(/sidebar-collapsed/);
    await expect(page.getByRole("button", { name: "Expand sidebar" })).toBeVisible();
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

test.describe("AXIOM landing page", () => {
  test.beforeEach(async ({ page }) => {
    await page.route(
      /^https:\/\/(?:fonts\.googleapis\.com|fonts\.gstatic\.com)\//,
      (route) => route.abort(),
    );
    await page.goto("/website/");
  });

  test("takes the CLI CTA to the terminal install section", async ({ page }) => {
    const cliCtas = page.locator('a[href="#install"]');

    expect(await cliCtas.count()).toBeGreaterThan(0);
    await expect(cliCtas.first()).toHaveAttribute("href", "#install");

    await cliCtas.first().click();

    await expect(page).toHaveURL(/\/website\/#install$/);
    await expect(page.locator("#install")).toBeVisible();
    await expect(page.locator("#install")).toContainText("Install the CLI");
  });

  test("keeps GitHub and CLI destinations explicit and network-independent", async ({ page }) => {
    const githubLinks = page.locator(
      'a[href="https://github.com/NetCore-Technologies/AXIOM-AI"]',
    );
    const cliCtas = page.locator('a[href="#install"]');

    expect(await githubLinks.count()).toBeGreaterThan(0);
    expect(await cliCtas.count()).toBeGreaterThan(0);

    const destinationChecks = [
      [githubLinks, "https://github.com/NetCore-Technologies/AXIOM-AI"],
      [cliCtas, "#install"],
    ] as const;

    for (const [links, destination] of destinationChecks) {
      const destinations = await links.evaluateAll((elements) =>
        elements.map((element) => element.getAttribute("href")),
      );
      expect(new Set(destinations)).toEqual(new Set([destination]));
    }

    await expect(githubLinks.first()).toHaveAttribute("target", "_blank");
    await expect(page.locator("#unix-command")).toHaveText(
      "curl -fsSL https://raw.githubusercontent.com/NetCore-Technologies/AXIOM-AI/main/installers/install.sh | bash",
    );
    await expect(page.locator("#windows-command")).toHaveText(
      "irm https://raw.githubusercontent.com/NetCore-Technologies/AXIOM-AI/main/installers/install.ps1 | iex",
    );
  });

  test("does not render gradient styling or fake dashboard metrics", async ({ page }) => {
    const visibleCopy = await page.locator("body").innerText();
    expect(visibleCopy).not.toMatch(/\b\d+(?:\.\d+)?%\b/);
    expect(visibleCopy).not.toMatch(
      /\b(?:system health|inference activity|model registry|ready|synced|live)\b/i,
    );

    await expect(page.locator("[data-count], .metric-card, .gradient-icon")).toHaveCount(0);

    const gradientElements = await page.evaluate(() =>
      Array.from(document.querySelectorAll("body *"))
        .filter((element) => getComputedStyle(element).backgroundImage.includes("gradient"))
        .map((element) => element.tagName.toLowerCase()),
    );
    expect(gradientElements).toEqual([]);
  });
});
