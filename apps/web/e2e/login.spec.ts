import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.origin === "http://127.0.0.1:3189") await route.continue();
    else await route.abort();
  });
});

test("rejects an invalid email in the browser", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: "Welcome to Parent Plus" })).toBeVisible();
  await page.getByLabel("Email address").fill("not-an-email");
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.locator("#email-error")).toHaveText("Enter a valid email address.");
  await expect(page.getByLabel("Email address")).toHaveAttribute("aria-invalid", "true");
  await page.getByLabel("Email address").fill("coach@example.com");
  await expect(page.getByLabel("Email address")).toHaveAttribute("aria-invalid", "false");
  await expect(page.locator("#email-error")).toHaveCount(0);
});

test("does not claim email delivery when live OTP is disabled", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email address").fill("coach@example.com");
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.locator("#email-error")).toHaveText("Email verification is not enabled in this environment.");
  await expect(page.getByLabel("Email address")).toHaveAttribute("aria-invalid", "false");
  await expect(page.getByLabel("Email address")).toHaveAccessibleDescription("Email verification is not enabled in this environment.");
  await expect(page.getByRole("status")).toHaveCount(0);
  await expect(page.getByLabel("Verification code")).toHaveCount(0);
});

test("redirects an anonymous visitor away from the coach home", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("heading", { name: "Welcome to Parent Plus" })).toBeVisible();
});

test("keeps parent profiles unavailable when disabled", async ({ page }) => {
  const writes: string[] = [];
  const external: string[] = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (request.method() !== "GET" && request.method() !== "HEAD") writes.push(url.origin);
    if (url.origin !== "http://127.0.0.1:3189") external.push(url.origin);
  });
  await page.goto("/parent/children");
  await expect(page.getByRole("heading", { name: "Parent profiles" })).toBeVisible();
  await expect(page.getByText("Profiles are not available in this environment.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Load profiles" })).toHaveCount(0);
  const storage = await page.evaluate(() => JSON.stringify({ local: { ...localStorage }, session: { ...sessionStorage } }));
  await page.reload();
  await expect(page.getByText("Profiles are not available in this environment.")).toBeVisible();
  expect(await page.evaluate(() => JSON.stringify({ local: { ...localStorage }, session: { ...sessionStorage } }))).toBe(storage);
  expect(writes).toEqual([]);
  expect(external).toEqual([]);
});
