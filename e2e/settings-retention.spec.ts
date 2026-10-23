import { expect, test } from "@playwright/test";
import { ensureAuthenticated } from "./helpers/auth";

test("Settings explains local data retention and links to runtime trace controls", async ({ page }) => {
  await ensureAuthenticated(page);
  await page.goto("/?page=settings");

  await expect(page.getByRole("heading", { level: 1, name: "Settings", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Data and retention", exact: true })).toBeVisible();
  await expect(page.getByText(/metadata-only records in memory/i)).toBeVisible();

  const guide = page.getByRole("link", { name: "Read the data retention and deletion guide" });
  await expect(guide).toHaveAttribute(
    "href",
    "https://github.com/NetCore-Technologies/AXIOM-AI/blob/latest/development/docs/DATA-RETENTION.md",
  );

  await page.getByRole("button", { name: "Review traces" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Runtime", exact: true })).toBeVisible();
  await expect(page.getByRole("region", { name: "Runtime request trace history" })).toBeVisible();
});
