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
  await expect(page.getByRole("heading", { name: "Check class setup" })).toHaveCount(0);
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

test("supports coach navigation at a narrow phone width", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 640 });
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.origin === "http://127.0.0.1:3189") await route.continue();
    else await route.abort();
  });
  await page.goto("/schedule");
  const nav = page.getByRole("navigation", { name: "Main navigation" });
  const links = nav.getByRole("link");
  await expect(links).toHaveCount(5);
  await expect(nav.getByRole("link", { name: "Schedule" })).toHaveAttribute("aria-current", "page");
  const boxes = await links.evaluateAll((elements) => elements.map((element) => {
    const box = element.getBoundingClientRect();
    const hit = document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2);
    return { left: box.left, right: box.right, width: box.width, height: box.height, hit: !!hit && element.contains(hit) };
  }));
  for (const [index, box] of boxes.entries()) {
    expect(box.width).toBeGreaterThanOrEqual(44);
    expect(box.height).toBeGreaterThanOrEqual(44);
    expect(box.left).toBeGreaterThanOrEqual(0);
    expect(box.right).toBeLessThanOrEqual(320);
    expect(box.hit).toBe(true);
    if (index) expect(box.left).toBeGreaterThanOrEqual(boxes[index - 1].right);
  }
  await nav.getByRole("link", { name: "Today" }).focus();
  await page.keyboard.press("Tab");
  await expect(nav.getByRole("link", { name: "Schedule" })).toBeFocused();
  await page.keyboard.press("Tab");
  await page.keyboard.press("Tab");
  await expect(nav.getByRole("link", { name: "Students" })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/students$/);
  await expect(nav.getByRole("link", { name: "Students" })).toHaveAttribute("aria-current", "page");
  await nav.getByRole("link", { name: "Today" }).click();
  await expect(page.getByText(/example data.*not real classes or records/i)).toBeVisible();
  await expect(page.getByText("Start class")).toHaveCount(0);
  const menuTrigger = page.locator("summary").filter({ hasText: "Open menu" });
  await menuTrigger.click();
  const menu = page.getByRole("navigation", { name: "Coach menu" });
  await expect(menu.getByRole("link", { name: "Schedule" })).toBeVisible();
  await menuTrigger.click();
  await expect(menu).toBeHidden();
  await menuTrigger.focus();
  await page.keyboard.press("Enter");
  await expect(menu).toBeVisible();
  await menu.getByRole("link", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/login$/);
});
