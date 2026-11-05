import { test, expect } from "@playwright/test";

const app = "http://127.0.0.1:3190";
const fake = "http://127.0.0.1:3191";
const actor = "11111111-1111-4111-8111-111111111111";
const other = "22222222-2222-4222-8222-222222222222";
let blockedOrigins = [];
let pageErrors = [];
const enc = (value) => Buffer.from(JSON.stringify(value)).toString("base64url");
function sessionCookie(id) {
  const token = enc({ alg: "HS256", typ: "JWT" }) + "." + enc({ sub: id, aud: "authenticated", role: "authenticated", exp: 4102444800, iat: 1700000000 }) + ".c3ludGhldGlj";
  const user = { id, aud: "authenticated", role: "authenticated", email: "parent@example.test", app_metadata: {}, user_metadata: {}, created_at: "2026-01-01T00:00:00.000Z" };
  return { name: "sb-localhost-auth-token", value: "base64-" + enc({ access_token: token, refresh_token: "synthetic-refresh", expires_at: 4102444800, expires_in: 3600, token_type: "bearer", user }), url: app };
}

test.beforeEach(async ({ context, page, request }) => {
  blockedOrigins = [];
  pageErrors = [];
  const observeErrors = (browserPage) => browserPage.on("pageerror", (error) => pageErrors.push(error.message));
  observeErrors(page);
  context.on("page", observeErrors);
  const reset = await request.post(fake + "/__test/reset");
  expect(reset.ok()).toBeTruthy();
  await context.addCookies([sessionCookie(actor)]);
  await context.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.origin === app || url.origin === "http://localhost:3191") await route.continue();
    else { blockedOrigins.push(url.origin); await route.abort("blockedbyclient"); }
  });
});

test.afterEach(async ({ request }) => {
  const events = await (await request.get(fake + "/__test/events")).json();
  expect(blockedOrigins).toEqual([]);
  expect(pageErrors).toEqual([]);
  expect(events).not.toContain("unexpected-endpoint");
  expect(events).not.toContain("unexpected-other-rpc");
});

test("creates and confirms a profile using a synthetic provider", async ({ page, request }) => {
  await page.goto("/parent/children");
  await page.getByRole("button", { name: "Check creation status" }).click();
  await page.getByLabel("Child name").fill("Asha");
  await page.getByRole("button", { name: "Create profile" }).click();
  await expect(page.getByText("Profile: Asha")).toBeVisible();
  await page.getByRole("button", { name: "Confirm result" }).click();
  await expect(page.getByText("Result confirmed")).toBeVisible();
  await page.getByRole("button", { name: "Load profiles" }).click();
  await expect(page.getByRole("listitem")).toHaveText("Asha");
  const events = await (await request.get(fake + "/__test/events")).json();
  expect(events).toContain("app_begin_child_creation");
  expect(events).toContain("app_ack_child_creation");
  expect(events).toContain("app_list_created_children");
});

test("recovers an unconfirmed request after another tab creates a later profile", async ({ page, context, request }) => {
  expect((await request.post(fake + "/__test/lose")).ok()).toBeTruthy();
  await page.goto("/parent/children");
  await page.getByRole("button", { name: "Check creation status" }).click();
  await page.getByLabel("Child name").fill("Asha");
  await page.getByRole("button", { name: "Create profile" }).click();
  await expect(page.getByText(/unable to confirm the profile/i)).toBeVisible();
  const marker = await page.evaluate(() => sessionStorage.getItem("parentplus.child-creation-recovery.v1"));
  expect(marker).toBeTruthy();
  expect(marker).not.toContain("Asha");
  await expect(page.getByRole("button", { name: "Load profiles" })).toBeDisabled();

  const second = await context.newPage();
  await second.goto("/parent/children");
  await second.getByRole("button", { name: "Check creation status" }).click();
  await expect(second.getByText("Profile: Asha")).toBeVisible();
  await second.getByRole("button", { name: "Confirm result" }).click();
  await second.getByRole("button", { name: "Add another profile" }).click();
  await second.getByLabel("Child name").fill("Nila");
  await second.getByRole("button", { name: "Create profile" }).click();
  await expect(second.getByText("Profile: Nila")).toBeVisible();

  await page.bringToFront();
  await page.reload();
  await page.getByRole("button", { name: "Check creation status" }).click();
  await page.getByRole("button", { name: "Stop waiting for this request" }).click();
  await expect(page.getByText(/earlier request created a profile/i)).toBeVisible();
  await expect(page.getByText("Profile: Nila")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Add another profile" })).toHaveCount(0);
  expect(await page.evaluate(() => sessionStorage.getItem("parentplus.child-creation-recovery.v1"))).toBeNull();
  const events = await (await request.get(fake + "/__test/events")).json();
  expect(events).toContain("app_historical_child_creation");
});

test("keeps an unresolved request locked after an account switch", async ({ page, context, request }) => {
  expect((await request.post(fake + "/__test/lose")).ok()).toBeTruthy();
  await page.goto("/parent/children");
  await page.getByRole("button", { name: "Check creation status" }).click();
  await page.getByLabel("Child name").fill("Asha");
  await page.getByRole("button", { name: "Create profile" }).click();
  await expect(page.getByText(/unable to confirm the profile/i)).toBeVisible();
  const before = await (await request.get(fake + "/__test/events")).json();
  await context.addCookies([sessionCookie(other)]);
  await page.reload();
  await page.getByRole("button", { name: "Check creation status" }).click();
  await expect(page.getByText(/unable to confirm the profile\. Sign in to the original account/i)).toBeVisible();
  await expect(page.getByRole("button", { name: "Load profiles" })).toBeDisabled();
  await expect(page.getByText("Profile: Asha")).toHaveCount(0);
  expect(await page.evaluate(() => sessionStorage.getItem("parentplus.child-creation-recovery.v1"))).toBeTruthy();
  const after = await (await request.get(fake + "/__test/events")).json();
  expect(after.filter((event) => event === "app_current_child_creation")).toHaveLength(before.filter((event) => event === "app_current_child_creation").length);
  expect(after).toContain("user:" + other);
});
