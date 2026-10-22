import { expect, test } from "@playwright/test";
import { ensureAuthenticated } from "./helpers/auth";

test("Training page submits a bounded local LoRA job and displays its real status", async ({ page }) => {
  await ensureAuthenticated(page);

  const queuedJob = {
    schema_version: 1,
    id: "a".repeat(32),
    status: "queued",
    created_at: "2026-10-21T00:00:00Z",
    updated_at: "2026-10-21T00:00:00Z",
    started_at: null,
    finished_at: null,
    config: {
      model_path: "/models/base",
      dataset_path: "/data/train.jsonl",
      output_dir: "/runs/adapter",
      text_field: "text",
      max_steps: 3,
      sequence_length: 64,
      learning_rate: 0.0001,
      lora_rank: 4,
    },
    completed_steps: 0,
    loss: null,
    error: null,
    result: null,
    logs: ["Job queued."],
  };
  let submitted: Record<string, unknown> | null = null;

  await page.route("**/api/fine-tuning/**", route => {
    const { pathname } = new URL(route.request().url());
    if (pathname.endsWith("/runtime")) {
      return route.fulfill({ json: {
        backend: "transformers-peft-local-lora",
        can_start: true,
        packages: { torch: true, transformers: true, peft: true, accelerate: true },
        model_loading: "local_files_only",
        scope_note: "Local model only.",
      } });
    }
    if (pathname.endsWith("/jobs") && route.request().method() === "POST") {
      submitted = route.request().postDataJSON() as Record<string, unknown>;
      return route.fulfill({ status: 202, json: queuedJob });
    }
    if (pathname.endsWith("/jobs")) return route.fulfill({ json: { jobs: [] } });
    return route.fulfill({ json: queuedJob });
  });

  await page.goto("/?page=training");
  await page.getByLabel("Local base model directory").fill("/models/base");
  await page.getByLabel("JSONL training dataset").fill("/data/train.jsonl");
  await page.getByLabel("Adapter output directory").fill("/runs/adapter");
  await page.getByLabel("Maximum optimization steps").fill("3");
  await page.getByLabel("Sequence length").fill("64");
  await page.getByLabel("LoRA rank").fill("4");

  await page.getByRole("button", { name: "Start local fine-tuning" }).click();

  const jobStatus = page.locator('[aria-label="Fine-tuning job status"]');
  await expect(jobStatus).toBeVisible();
  await expect(jobStatus).toContainText("QUEUED");
  expect(submitted).toMatchObject({
    model_path: "/models/base",
    dataset_path: "/data/train.jsonl",
    output_dir: "/runs/adapter",
    max_steps: 3,
    sequence_length: 64,
    lora_rank: 4,
  });
});
