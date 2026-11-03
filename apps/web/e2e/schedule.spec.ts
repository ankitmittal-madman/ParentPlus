import { expect, test } from "@playwright/test";

test("shows a clearly labelled example schedule", async ({ page }) => {
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.origin === "http://127.0.0.1:3189") await route.continue();
    else await route.abort();
  });
  const writes: string[] = [];
  page.on("request", (request) => { if (request.method() !== "GET" && request.method() !== "HEAD") writes.push(request.url()); });
  await page.goto("/schedule");
  await expect(page.getByRole("heading", { name: "Schedule", exact: true })).toBeVisible();
  await expect(page.getByText(/example data.*not real classes/i)).toBeVisible();
  const sessions = page.getByRole("list", { name: "Example sessions" });
  await expect(sessions.getByText("Clay Basics")).toBeVisible();
  await expect(sessions.getByText("Clay Juniors")).toBeVisible();
  await expect(sessions.getByText("Example Monday, 5:00 PM")).toBeVisible();
  const storageBefore = await page.evaluate(() => JSON.stringify({ local: { ...localStorage }, session: { ...sessionStorage } }));
  await page.getByLabel("Course name").fill("Dance");
  await page.getByLabel("Batch name").fill("Beginners");
  await page.getByRole("button", { name: "Preview class setup" }).click();
  await expect(page.getByRole("status")).toContainText("Preview only — not saved");
  await expect(page.getByRole("status")).toContainText("Dance");
  expect(writes).toEqual([]);
  expect(await page.evaluate(() => JSON.stringify({ local: { ...localStorage }, session: { ...sessionStorage } }))).toBe(storageBefore);
  await page.reload();
  await expect(page.getByRole("status")).toHaveCount(0);
});
