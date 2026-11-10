import { test, expect, login, emailFor, workspace, child } from "./fixtures";
import type { Page } from "@playwright/test";
async function signOut(page: Page) {
  await page.goto("/login");
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page.getByLabel("Email address")).toBeVisible();
}
async function academy(page: Page, name: string) {
  await page.goto("/students");
  await page
    .getByRole("button", { name: "Load academies", exact: true })
    .click();
  await page
    .getByLabel("Academy", { exact: true })
    .selectOption({ label: name });
}
test("[INVITE-001] coach invites a separate parent; connection persists in both accounts", async ({
  page,
  context,
}) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  const coach = emailFor();
  await login(page, coach);
  const name = await workspace(page, "academy");
  await academy(page, name);
  await page
    .getByRole("button", { name: "Add a student", exact: true })
    .click();
  const link = await page.getByLabel("Family invite link").inputValue();
  await page.getByRole("button", { name: "Copy link", exact: true }).click();
  await expect(page.locator('p[role="alert"]')).toContainText("Link copied");
  await page
    .getByRole("button", { name: "Clear invitation", exact: true })
    .click();
  await expect(page.getByLabel("Family invite link")).toHaveCount(0);
  await signOut(page);
  await login(page);
  await child(page, "Fictional Invited Child");
  await page.goto(link);
  await expect(page).toHaveURL(/\/join$/);
  await page
    .getByRole("button", { name: "Check invitation", exact: true })
    .click();
  await expect(page.getByRole("heading", { name, exact: true })).toBeVisible();
  await page
    .getByLabel("Your child", { exact: true })
    .selectOption({ label: "Fictional Invited Child" });
  await expect(
    page.getByRole("button", {
      name: "Confirm academy connection",
      exact: true,
    }),
  ).toBeDisabled();
  await page.getByLabel(/I confirm this is my child/).check();
  await page
    .getByRole("button", { name: "Confirm academy connection", exact: true })
    .click();
  await expect(
    page.getByText("Connection saved. Batch enrolment is a separate step.", {
      exact: true,
    }),
  ).toBeVisible();
  await page.goto(link);
  await page
    .getByRole("button", { name: "Check invitation", exact: true })
    .click();
  await expect(
    page.getByText(
      "This invitation has already been accepted by your account.",
      { exact: true },
    ),
  ).toBeVisible();
  await page
    .getByRole("link", {
      name: "View or create your child profiles",
      exact: true,
    })
    .click();
  const parent = page.getByRole("region", {
    name: "Academy connections",
    exact: true,
  });
  await parent
    .getByRole("button", { name: "Load your child profiles", exact: true })
    .click();
  await parent
    .getByLabel("Your child", { exact: true })
    .selectOption({ label: "Fictional Invited Child" });
  await parent
    .getByRole("button", { name: "Load academy connections", exact: true })
    .click();
  await expect(parent.getByRole("listitem")).toContainText(name);
  await signOut(page);
  await login(page, coach);
  await academy(page, name);
  await page
    .getByRole("button", { name: "Load students", exact: true })
    .click();
  await expect(
    page.getByRole("listitem").filter({ hasText: "Fictional Invited Child" }),
  ).toHaveCount(1);
  await page.reload();
  await page
    .getByRole("button", { name: "Load academies", exact: true })
    .click();
  await page
    .getByLabel("Academy", { exact: true })
    .selectOption({ label: name });
  await page
    .getByRole("button", { name: "Load students", exact: true })
    .click();
  await expect(
    page
      .getByRole("region", { name: "Students", exact: true })
      .getByRole("listitem")
      .getByText("Fictional Invited Child", { exact: true }),
  ).toBeVisible();
});
test("[INVITE-002] missing and fake invitation refuse access and offer sign-in", async ({
  page,
}) => {
  await page.goto("/join");
  await expect(page.getByText(/Open the complete invite link/)).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Check invitation", exact: true }),
  ).toBeDisabled();
  await page.getByRole("link", { name: "Sign in", exact: true }).click();
  await expect(page.getByLabel("Email address")).toBeVisible();
  await login(page);
  await page.goto("/join#" + "ca".repeat(32));
  await page
    .getByRole("button", { name: "Check invitation", exact: true })
    .click();
  await expect(page.locator('p[role="alert"]')).toContainText(
    "Invitation unavailable",
  );
  await expect(
    page.getByRole("button", {
      name: "Confirm academy connection",
      exact: true,
    }),
  ).toHaveCount(0);
});
test("[INVITE-003] interrupted issue retries the same request", async ({
  page,
}) => {
  await login(page);
  const name = await workspace(page);
  await academy(page, name);
  const students = page.getByRole("region", { name: "Students", exact: true });
  let injected = false;
  const requests: string[] = [];
  await page.route("**/students", (route) => {
    const request = route.request();
    const body = request.postData() || "";
    let payload: unknown;
    try { payload = JSON.parse(body); } catch { /* Non-JSON reads are not invite writes. */ }
    // issueFamilyInvite takes actor, workspace, request UUID and a 64-hex token.
    // Scoped enrolment reads are also POSTs and must pass through unchanged.
    if (
      request.method() === "POST" &&
      Array.isArray(payload) && payload.length === 4 &&
      payload.slice(0, 3).every(value => typeof value === "string" && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)) &&
      typeof payload[3] === "string" && /^[0-9a-f]{64}$/.test(payload[3])
    ) {
      requests.push(body);
      if (!injected) { injected = true; return route.abort(); }
    }
    return route.fallback();
  });
  await students
    .getByRole("button", { name: "Add a student", exact: true })
    .click();
  await expect(students.getByRole("alert")).toContainText("unconfirmed");
  expect(injected).toBe(true);
  await students
    .getByRole("button", { name: "Retry invitation", exact: true })
    .click();
  await expect(students.getByLabel("Family invite link")).toBeVisible();
  expect(requests).toHaveLength(2);
  expect(requests[1]).toBe(requests[0]);
  const payloads = requests.map(body => JSON.parse(body) as string[]);
  expect(payloads[0][2]).toMatch(/^[0-9a-f-]{36}$/i);
  expect(payloads[1][2]).toBe(payloads[0][2]);
});
test("[INVITE-004] Hindi admission controls and empty parent connections", async ({
  page,
  context,
}) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await login(page);
  const name = await workspace(page);
  await page.goto("/students");
  await page.getByLabel("Language / भाषा").selectOption("hi");
  await page
    .getByRole("button", { name: "अकादमियाँ लोड करें", exact: true })
    .click();
  await page
    .getByLabel("अकादमी", { exact: true })
    .selectOption({ label: name });
  await page
    .getByRole("button", { name: "विद्यार्थी लोड करें", exact: true })
    .click();
  await expect(page.getByText(/इस पेज पर कोई जुड़ा बच्चा/)).toBeVisible();
  await page
    .getByRole("button", { name: "विद्यार्थी जोड़ें", exact: true })
    .click();
  await page
    .getByRole("button", { name: "लिंक कॉपी करें", exact: true })
    .click();
  await page
    .getByRole("button", { name: "निमंत्रण हटाएँ", exact: true })
    .click();
  await child(page, "Fictional Unconnected Child");
  const parent = page.getByRole("region", {
    name: "अकादमी से संबंध", exact: true,
  });
  await parent.getByRole("button", { name: "अपने बच्चे के प्रोफ़ाइल लोड करें", exact: true }).click();
  await parent.getByLabel("आपका बच्चा", { exact: true }).selectOption({ label: "Fictional Unconnected Child" });
  await parent.getByRole("button", { name: "अकादमी से संबंध लोड करें", exact: true }).click();
  await expect(parent.getByText("इस बच्चे का किसी अकादमी से सक्रिय संबंध नहीं है।", { exact: true })).toBeVisible();
});
