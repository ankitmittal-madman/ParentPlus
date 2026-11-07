import { expect, test } from "@playwright/test";

test("redirects anonymous visitors away from the protected schedule", async ({ page }) => {
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.origin === "http://127.0.0.1:3189") await route.continue();
    else await route.abort();
  });
  const writes: string[] = [];
  page.on("request", (request) => { if (request.method() !== "GET" && request.method() !== "HEAD") writes.push(request.url()); });
  await page.goto("/schedule");
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("heading", { name: "Welcome to Parent Plus" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Schedule", exact: true })).toHaveCount(0);
  expect(writes).toEqual([]);
});

test("keeps the protected schedule behind sign-in at a narrow phone width", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 640 });
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.origin === "http://127.0.0.1:3189") await route.continue();
    else await route.abort();
  });
  await page.goto("/schedule");
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("heading", { name: "Welcome to Parent Plus" })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Main navigation" })).toHaveCount(0);
});
