import { test, expect } from "@playwright/test";

const app = "http://127.0.0.1:3190";
const fake = "http://127.0.0.1:3191";
const actor = "11111111-1111-4111-8111-111111111111";
const other = "22222222-2222-4222-8222-222222222222";
let blockedOrigins = [];
let pageErrors = [];
const enc = (value) => Buffer.from(JSON.stringify(value)).toString("base64url");
function tokenFor(id) {
  return enc({ alg: "HS256", typ: "JWT" }) + "." + enc({ sub: id, aud: "authenticated", role: "authenticated", exp: 4102444800, iat: 1700000000 }) + ".c3ludGhldGlj";
}
function sessionCookie(id) {
  const token = tokenFor(id);
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

test("recovers a confirmation committed before its response was lost", async ({ page, request }) => {
  await page.goto("/parent/children");
  await page.getByRole("button", { name: "Check creation status" }).click();
  await page.getByLabel("Child name").fill("Asha");
  await page.getByRole("button", { name: "Create profile" }).click();
  await expect(page.getByText("Profile: Asha")).toBeVisible();
  await page.getByRole("button", { name: "Load profiles" }).click();
  await expect(page.getByRole("listitem")).toHaveText(["Asha"]);
  expect((await request.post(fake + "/__test/lose-ack")).ok()).toBeTruthy();
  await page.getByRole("button", { name: "Confirm result" }).click();
  await expect(page.getByRole("button", { name: "Load profiles" })).toBeDisabled();
  await expect(page.getByRole("listitem")).toHaveCount(0);
  await expect(page.getByText("Unable to confirm the profile. Check creation status before trying again.")).toBeVisible();
  const marker = await page.evaluate(() => sessionStorage.getItem("parentplus.child-creation-recovery.v1"));
  expect(marker).toBeTruthy();
  expect(marker).not.toContain("Asha");
  expect(JSON.parse(marker).operation).toBe("ack");
  await page.reload();
  await expect(page.getByRole("button", { name: "Load profiles" })).toBeDisabled();
  await page.getByRole("button", { name: "Check creation status" }).click();
  await expect(page.getByText("Result confirmed")).toBeVisible();
  expect(await page.evaluate(() => sessionStorage.getItem("parentplus.child-creation-recovery.v1"))).toBeNull();
  await page.getByRole("button", { name: "Load profiles" }).click();
  await expect(page.getByRole("listitem")).toHaveText(["Asha"]);
  const events = await (await request.get(fake + "/__test/events")).json();
  expect(events.filter((event) => event === "app_ack_child_creation")).toHaveLength(1);
  expect(events.filter((event) => event === "app_begin_child_creation")).toHaveLength(1);
});

test("retries an uncommitted confirmation after reload", async ({ page, request }) => {
  await page.goto("/parent/children");
  await page.getByRole("button", { name: "Check creation status" }).click();
  await page.getByLabel("Child name").fill("Asha");
  await page.getByRole("button", { name: "Create profile" }).click();
  await expect(page.getByText("Profile: Asha")).toBeVisible();
  expect((await request.post(fake + "/__test/fail-before-ack")).ok()).toBeTruthy();
  await page.getByRole("button", { name: "Confirm result" }).click();
  await expect(page.getByText("Unable to confirm the profile. Check creation status before trying again.")).toBeVisible();
  const marker = await page.evaluate(() => sessionStorage.getItem("parentplus.child-creation-recovery.v1"));
  expect(marker).toBeTruthy();
  expect(marker).not.toContain("Asha");
  expect(JSON.parse(marker).operation).toBe("ack");
  const headers = { authorization: "Bearer " + tokenFor(actor), apikey: "synthetic-public-key" };
  const before = await (await request.post(fake + "/rest/v1/rpc/app_current_child_creation", { headers, data: {} })).json();
  expect(before).toHaveLength(1);
  expect(before[0].intent_id).toBe(JSON.parse(marker).priorIntentId);
  expect(before[0].acknowledged).toBe(false);
  await page.reload();
  await expect(page.getByRole("button", { name: "Load profiles" })).toBeDisabled();
  await page.getByRole("button", { name: "Check creation status" }).click();
  await expect(page.getByRole("button", { name: "Retry confirmation" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Load profiles" })).toBeDisabled();
  await page.getByRole("button", { name: "Retry confirmation" }).click();
  await expect(page.getByText("Result confirmed")).toBeVisible();
  const after = await (await request.post(fake + "/rest/v1/rpc/app_current_child_creation", { headers, data: {} })).json();
  expect(after).toHaveLength(1);
  expect(after[0].intent_id).toBe(before[0].intent_id);
  expect(after[0].child_id).toBe(before[0].child_id);
  expect(after[0].acknowledged).toBe(true);
  expect(await page.evaluate(() => sessionStorage.getItem("parentplus.child-creation-recovery.v1"))).toBeNull();
  await page.getByRole("button", { name: "Load profiles" }).click();
  await expect(page.getByRole("listitem")).toHaveText(["Asha"]);
  const events = await (await request.get(fake + "/__test/events")).json();
  expect(events.filter((event) => event === "app_ack_child_creation")).toHaveLength(2);
  expect(events.filter((event) => event === "app_begin_child_creation")).toHaveLength(1);
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


test("fences an uncommitted request before allowing a new profile", async ({ page, request }) => {
  expect((await request.post(fake + "/__test/fail-before")).ok()).toBeTruthy();
  await page.goto("/parent/children");
  await page.getByRole("button", { name: "Check creation status" }).click();
  await page.getByLabel("Child name").fill("Asha");
  await page.getByRole("button", { name: "Create profile" }).click();
  await expect(page.getByText(/unable to confirm the profile/i)).toBeVisible();
  const marker = await page.evaluate(() => sessionStorage.getItem("parentplus.child-creation-recovery.v1"));
  expect(marker).toBeTruthy();
  expect(marker).not.toContain("Asha");
  const originalRequest = JSON.parse(marker).requestId;
  await page.reload();
  await expect(page.getByRole("button", { name: "Load profiles" })).toBeDisabled();
  await page.getByRole("button", { name: "Check creation status" }).click();
  await page.getByRole("button", { name: "Stop waiting for this request" }).click();
  await expect(page.getByLabel("Child name")).toBeVisible();
  expect(await page.evaluate(() => sessionStorage.getItem("parentplus.child-creation-recovery.v1"))).toBeNull();
  const headers = { authorization: "Bearer " + tokenFor(actor), apikey: "synthetic-public-key" };
  const delayed = await request.post(fake + "/rest/v1/rpc/app_begin_child_creation", { headers, data: { p_display_name: "Asha", p_prior_intent_id: null, p_request_id: originalRequest } });
  expect(delayed.status()).toBe(409);
  await page.getByLabel("Child name").fill("Asha");
  await page.getByRole("button", { name: "Create profile" }).click();
  await expect(page.getByText("Profile: Asha")).toBeVisible();
  const state = await request.post(fake + "/rest/v1/rpc/app_current_child_creation", { headers, data: {} });
  const profiles = await state.json();
  expect(profiles).toHaveLength(1);
  expect(profiles[0].request_id).not.toBe(originalRequest);
  const events = await (await request.get(fake + "/__test/events")).json();
  expect(events).toContain("app_fence_child_creation");
});
