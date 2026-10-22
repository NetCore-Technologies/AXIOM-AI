import { expect, test } from "@playwright/test";
import { ensureAuthenticated } from "./helpers/auth";

test("model registry filters and saved presets use the real typed API query contract", async ({ page }) => {
  const requests: URL[] = [];
  const models = [
    { id: "a".repeat(32), name: "Qwen Seven", source: "models/qwen-seven", format: "gguf", parameters: "7B", quantization: "Q4_K_M", architecture: "QwenForCausalLM", license: "Apache-2.0", tags: ["local", "chat"], favorite: true, content_sha256: null },
    { id: "b".repeat(32), name: "Qwen Mini", source: "models/qwen-mini", format: "gguf", parameters: "1.5B", quantization: "Q4_K_M", architecture: "QwenForCausalLM", license: "Apache-2.0", tags: ["local", "chat"], favorite: false, content_sha256: null },
    { id: "c".repeat(32), name: "Llama Base", source: "models/llama", format: "safetensors", parameters: "8B", quantization: "", architecture: "LlamaForCausalLM", license: "Meta", tags: ["training"], favorite: false, content_sha256: null },
  ];

  await page.route("**/api/workspace/models**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.pathname !== "/api/workspace/models" || request.method() !== "GET") {
      await route.continue();
      return;
    }
    requests.push(url);
    const search = (url.searchParams.get("search") ?? "").toLowerCase();
    const format = (url.searchParams.get("format") ?? "").toLowerCase();
    const tag = (url.searchParams.get("tag") ?? "").toLowerCase();
    const favorites = url.searchParams.get("favorite_only") === "true";
    const sortBy = url.searchParams.get("sort_by") ?? "name";
    const sortOrder = url.searchParams.get("sort_order") ?? "asc";
    const filtered = models.filter((model) =>
      (!search || [model.name, model.source, model.format, model.parameters ?? "", model.architecture ?? "", model.license ?? "", ...model.tags].some((field) => field.toLowerCase().includes(search)))
      && (!format || format === "all" || model.format.toLowerCase() === format)
      && (!tag || model.tags.some((item) => item.toLowerCase() === tag))
      && (!favorites || model.favorite)
    );
    filtered.sort((left, right) => {
      const a = sortBy === "parameters" ? Number.parseFloat(left.parameters ?? "0") : sortBy === "favorite" ? Number(left.favorite) : String(left[sortBy as keyof typeof left] ?? "").toString().toLowerCase();
      const b = sortBy === "parameters" ? Number.parseFloat(right.parameters ?? "0") : sortBy === "favorite" ? Number(right.favorite) : String(right[sortBy as keyof typeof right] ?? "").toString().toLowerCase();
      const result = typeof a === "number" && typeof b === "number" ? a - b : String(a).localeCompare(String(b));
      return sortOrder === "desc" ? -result : result;
    });
    const offset = Number(url.searchParams.get("offset") ?? "0");
    const limit = Number(url.searchParams.get("limit") ?? "25");
    const items = filtered.slice(offset, offset + limit);
    await route.fulfill({ json: {
      models: items, total: filtered.length, limit, offset, has_more: offset + limit < filtered.length,
      filters: { search, favorite_only: favorites, format: format || null, tag: tag || null, sort_by: sortBy, sort_order: sortOrder },
    } });
  });

  await page.route("**/api/model-studio/status", (route) => route.fulfill({ json: {
    schema_version: 1, ollama_installed: false, ollama_endpoint: "http://127.0.0.1:11434",
    download_limit_bytes: 1000000, gguf_directory: "models", catalogue: "Hugging Face",
    network_search_is_explicit: true,
  } }));
  await page.route("**/api/model-studio/jobs**", (route) => route.fulfill({ json: { jobs: [] } }));

  await ensureAuthenticated(page);
  await page.goto("/?page=models");
  await expect(page.getByRole("heading", { level: 1, name: "Models", exact: true })).toBeVisible();
  await expect(page.getByText("Qwen Seven", { exact: true })).toBeVisible();

  await page.getByRole("textbox", { name: "Search model registry" }).fill("qwen");
  await page.getByRole("textbox", { name: "Exact model format" }).fill("gguf");
  await page.getByRole("textbox", { name: "Exact model tag" }).fill("chat");
  await page.getByRole("checkbox", { name: "Favorites only" }).check();
  await page.getByLabel("Sort model registry by").selectOption("parameters");
  await page.getByLabel("Model sort order").selectOption("desc");
  await page.getByRole("button", { name: "Apply filters" }).click();

  await expect(page.getByText("Qwen Seven", { exact: true })).toBeVisible();
  await expect(page.getByText("Qwen Mini", { exact: true })).toHaveCount(0);
  const filteredRequest = requests.at(-1);
  expect(filteredRequest?.searchParams.get("search")).toBe("qwen");
  expect(filteredRequest?.searchParams.get("format")).toBe("gguf");
  expect(filteredRequest?.searchParams.get("tag")).toBe("chat");
  expect(filteredRequest?.searchParams.get("favorite_only")).toBe("true");
  expect(filteredRequest?.searchParams.get("sort_by")).toBe("parameters");
  expect(filteredRequest?.searchParams.get("sort_order")).toBe("desc");

  await page.getByRole("textbox", { name: "Saved filter name" }).fill("Favorite Qwen chat models");
  await page.getByRole("button", { name: "Save current filters" }).click();
  await expect(page.getByText("Favorite Qwen chat models", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Clear filters" }).click();
  await expect(page.getByText("Qwen Mini", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Apply", exact: true }).last().click();
  await expect(page.getByText("Qwen Seven", { exact: true })).toBeVisible();
  await expect(page.getByText("Qwen Mini", { exact: true })).toHaveCount(0);
});
