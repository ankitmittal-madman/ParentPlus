import { expect, test } from "@playwright/test";

test("shows a clearly labelled example schedule", async ({ page }) => {
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.origin === "http://127.0.0.1:3189") await route.continue();
    else await route.abort();
  });
  await page.goto("/schedule");
  await expect(page.getByRole("heading", { name: "Schedule", exact: true })).toBeVisible();
  await expect(page.getByText(/example data.*not real classes/i)).toBeVisible();
  const sessions = page.getByRole("list", { name: "Example sessions" });
  await expect(sessions.getByText("Clay Basics")).toBeVisible();
  await expect(sessions.getByText("Clay Juniors")).toBeVisible();
  await expect(sessions.getByText("Example Monday, 5:00 PM")).toBeVisible();
});
