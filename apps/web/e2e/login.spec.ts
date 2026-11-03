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
});

test("does not claim email delivery when live OTP is disabled", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email address").fill("coach@example.com");
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.locator("#email-error")).toHaveText("Email verification is not enabled in this environment.");
  await expect(page.getByRole("status")).toHaveCount(0);
  await expect(page.getByLabel("Verification code")).toHaveCount(0);
});
