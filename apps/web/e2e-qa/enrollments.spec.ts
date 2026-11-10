import {
  test,
  expect,
  login,
  emailFor,
  workspace,
  child,
  setup,
} from "./fixtures";
import type { Page } from "@playwright/test";
const A = "QA Enrolment Batch A",
  B = "QA Enrolment Batch B",
  CHILD = "Fictional Enrolment Child";
async function signOut(page: Page) {
  await page.goto("/login");
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page.getByLabel("Email address")).toBeVisible();
}
async function createBatch(page: Page, name: string) {
  const p = await setup(page);
  await p
    .getByLabel("Course name", { exact: true })
    .fill("QA Enrolment Course " + name.slice(-1));
  await p.getByLabel("Batch name", { exact: true }).fill(name);
  const zone = p.getByLabel("Academy time zone", { exact: true });
  if (await zone.isEnabled()) await zone.fill("Asia/Kolkata");
  await p.getByLabel("First session date").fill("2026-11-16");
  await p.getByLabel("Local start time").fill("17:00");
  await p.getByLabel("Last date for weekly sessions").fill("2026-11-30");
  await p
    .getByRole("button", {
      name: "Create course, batch and weekly sessions",
      exact: true,
    })
    .click();
  await expect(
    p.getByText("Weekly schedule: 3 sessions", { exact: true }),
  ).toBeVisible();
  await p
    .getByRole("button", {
      name: "Confirm course, batch and schedule",
      exact: true,
    })
    .click();
  await expect(
    p.getByText("Setup completed — acknowledged", { exact: true }),
  ).toBeVisible();
}
async function connected(page: Page, two = false) {
  const coach = emailFor();
  await login(page, coach);
  const academy = await workspace(page, "academy");
  await createBatch(page, A);
  if (two) await createBatch(page, B);
  await page.goto("/students");
  await page
    .getByRole("button", { name: "Load academies", exact: true })
    .click();
  await page
    .getByLabel("Academy", { exact: true })
    .selectOption({ label: academy });
  await page
    .getByRole("button", { name: "Add a student", exact: true })
    .click();
  const link = await page.getByLabel("Family invite link").inputValue();
  await signOut(page);
  const parent = await login(page);
  await child(page, CHILD);
  await page.goto(link);
  await page
    .getByRole("button", { name: "Check invitation", exact: true })
    .click();
  await page
    .getByLabel("Your child", { exact: true })
    .selectOption({ label: CHILD });
  await page.getByLabel(/I confirm this is my child/).check();
  await page
    .getByRole("button", { name: "Confirm academy connection", exact: true })
    .click();
  await expect(
    page.getByText("Connection saved. Batch enrolment is a separate step.", {
      exact: true,
    }),
  ).toBeVisible();
  return { coach, parent, academy };
}
async function manager(page: Page, coach: string) {
  await signOut(page);
  await login(page, coach);
  await page.goto("/students");
  const p = page.getByRole("region", { name: "Batch enrolment", exact: true });
  await expect(p.getByRole("button", { name: A, exact: true })).toBeVisible();
  return p;
}
async function enrol(page: Page) {
  const p = page.getByRole("region", { name: "Batch enrolment", exact: true });
  await p.getByRole("button", { name: A, exact: true }).click();
  await p
    .getByLabel("Connected child", { exact: true })
    .selectOption({ label: CHILD });
  await p.getByRole("button", { name: "Enrol child", exact: true }).click();
  const row = p.getByRole("article").filter({ hasText: CHILD });
  await expect(row.getByText("Active", { exact: true })).toBeVisible();
  return { p, row };
}
async function parentClasses(page: Page, parent: string) {
  await signOut(page);
  await login(page, parent);
  await page.goto("/parent/children");
  const p = page.getByRole("region", { name: "Child classes", exact: true });
  await expect(
    p.getByLabel("Child for classes", { exact: true }),
  ).toBeVisible();
  return p;
}
test("[ENROL-001] explicit enrolment, parent reload and pause/resume/withdraw persist", async ({
  page,
}) => {
  const c = await connected(page);
  await page.goto("/parent/children");
  await expect(
    page
      .getByRole("region", { name: "Child classes", exact: true })
      .getByText("No saved classes for this child.", { exact: true }),
  ).toBeVisible();
  await manager(page, c.coach);
  const { p, row } = await enrol(page);
  await page.reload();
  await expect(p.getByRole("article").filter({ hasText: CHILD })).toHaveCount(
    1,
  );
  await p
    .getByRole("button", { name: "Refresh enrolments", exact: true })
    .click();
  await row
    .getByLabel("Reason", { exact: true })
    .selectOption("temporary_break");
  await row
    .getByRole("button", { name: "Pause enrolment", exact: true })
    .click();
  await expect(row.getByText("Paused", { exact: true })).toBeVisible();
  let parent = await parentClasses(page, c.parent);
  await expect(parent.getByText(A, { exact: false })).toBeVisible();
  await expect(parent.getByText("Paused", { exact: true })).toBeVisible();
  await page.reload();
  await parent
    .getByRole("button", { name: "Refresh classes", exact: true })
    .click();
  await expect(parent.getByText("Paused", { exact: true })).toBeVisible();
  await manager(page, c.coach);
  await row
    .getByRole("button", { name: "Resume enrolment", exact: true })
    .click();
  await expect(row.getByText("Active", { exact: true })).toBeVisible();
  await row
    .getByLabel("Reason", { exact: true })
    .selectOption("schedule_change");
  await row
    .getByRole("button", { name: "Withdraw enrolment", exact: true })
    .click();
  await expect(row.getByText("Withdrawn", { exact: true })).toBeVisible();
  await expect(
    row.getByRole("button", { name: "Resume enrolment", exact: true }),
  ).toHaveCount(0);
  parent = await parentClasses(page, c.parent);
  await expect(parent.getByText("Withdrawn", { exact: true })).toBeVisible();
});
test("[ENROL-002] interrupted enrolment retries same request without duplicate registration", async ({
  page,
}) => {
  const c = await connected(page);
  const p = await manager(page, c.coach);
  await p
    .getByLabel("Connected child", { exact: true })
    .selectOption({ label: CHILD });
  let injected = false;
  const requests: string[] = [];
  await page.route("**/students", (route) => {
    const body = route.request().postData() || "";
    if (route.request().method() === "POST" && body.includes('"requestId"')) {
      requests.push(body);
      if (!injected) {
        injected = true;
        return route.abort();
      }
    }
    return route.fallback();
  });
  await p.getByRole("button", { name: "Enrol child", exact: true }).click();
  await expect(p.getByText(/The enrolment reply is uncertain/)).toBeVisible();
  expect(injected).toBe(true);
  await expect(p.getByLabel("Connected child", { exact: true })).toBeDisabled();
  await p
    .getByRole("button", { name: "Check enrolment status", exact: true })
    .click();
  await expect(p.getByRole("article").filter({ hasText: CHILD })).toHaveCount(
    1,
  );
  expect(requests.length >= 2).toBe(true);
  const ids = requests.map((s) => s.match(/"requestId":"([0-9a-f-]+)"/)?.[1]);
  expect(Boolean(ids[0]) && ids[0] === ids[1]).toBe(true);
});
test("[ENROL-003] another parent cannot see a child's saved class; completion persists", async ({
  page,
}) => {
  const c = await connected(page);
  await manager(page, c.coach);
  await enrol(page);
  await signOut(page);
  await login(page);
  await child(page, "Fictional Other Enrolment Child");
  await page.goto("/parent/children");
  let p = page.getByRole("region", { name: "Child classes", exact: true });
  await expect(
    p.getByText("No saved classes for this child.", { exact: true }),
  ).toBeVisible();
  await expect(p.getByText(A, { exact: false })).toHaveCount(0);
  await page.goto("/students");
  await expect(page).toHaveURL(/\/coach-access$/);
  const managerPanel = await manager(page, c.coach);
  const row = managerPanel.getByRole("article").filter({ hasText: CHILD });
  await row
    .getByRole("button", { name: "Complete enrolment", exact: true })
    .click();
  await expect(row.getByText("Completed", { exact: true })).toBeVisible();
  p = await parentClasses(page, c.parent);
  await expect(p.getByText("Completed", { exact: true })).toBeVisible();
});
test("[ENROL-004] Hindi lifecycle and two batch filters show saved independent states", async ({
  page,
}) => {
  const c = await connected(page, true);
  const en = await manager(page, c.coach);
  await en
    .getByLabel("Enrolment language / नामांकन की भाषा")
    .selectOption("hi");
  const p = page.getByRole("region", { name: "बैच नामांकन", exact: true });
  await p.getByRole("button", { name: A, exact: true }).click();
  await p
    .getByLabel("जुड़ा हुआ बच्चा", { exact: true })
    .selectOption({ label: CHILD });
  let injected = false;
  const requests: string[] = [];
  await page.route("**/students", (route) => {
    const body = route.request().postData() || "";
    if (route.request().method() === "POST" && body.includes('"requestId"')) {
      requests.push(body);
      if (!injected) {
        injected = true;
        return route.abort();
      }
    }
    return route.fallback();
  });
  await p
    .getByRole("button", { name: "बच्चे का नामांकन करें", exact: true })
    .click();
  await expect(p.getByText(/नामांकन का उत्तर निश्चित नहीं है/)).toBeVisible();
  expect(injected).toBe(true);
  await expect(p.getByLabel("जुड़ा हुआ बच्चा", { exact: true })).toBeDisabled();
  await p
    .getByRole("button", { name: "नामांकन की स्थिति जाँचें", exact: true })
    .click();
  let row = p.getByRole("article").filter({ hasText: CHILD });
  await expect(row).toHaveCount(1);
  await expect(row.getByText("सक्रिय", { exact: true })).toBeVisible();
  expect(requests).toHaveLength(2);
  const ids = requests.map((body) => body.match(/"requestId":"([0-9a-f-]+)"/)?.[1]);
  expect(ids[0]).toMatch(/^[0-9a-f-]{36}$/);
  expect(ids[1]).toBe(ids[0]);
  expect(requests[1]).toBe(requests[0]);
  await page.unroute("**/students");
  await row.getByLabel("कारण", { exact: true }).selectOption("temporary_break");
  await row.getByRole("button", { name: "नामांकन रोकें", exact: true }).click();
  await expect(row.getByText("रुका हुआ", { exact: true })).toBeVisible();
  await row
    .getByRole("button", { name: "नामांकन फिर शुरू करें", exact: true })
    .click();
  await row
    .getByRole("button", { name: "नामांकन पूरा करें", exact: true })
    .click();
  await expect(row.getByText("पूरा", { exact: true })).toBeVisible();
  await p.getByRole("button", { name: B, exact: true }).click();
  await expect(
    p.getByText("इस बैच में कोई सहेजा गया नामांकन नहीं है।", { exact: true }),
  ).toBeVisible();
  await p
    .getByLabel("जुड़ा हुआ बच्चा", { exact: true })
    .selectOption({ label: CHILD });
  await p
    .getByRole("button", { name: "बच्चे का नामांकन करें", exact: true })
    .click();
  row = p.getByRole("article").filter({ hasText: CHILD });
  await row.getByLabel("कारण", { exact: true }).selectOption("other");
  await row
    .getByRole("button", { name: "नामांकन वापस लें", exact: true })
    .click();
  await expect(row.getByText("वापस लिया गया", { exact: true })).toBeVisible();
  await p.getByRole("button", { name: A, exact: true }).click();
  await expect(p.getByText("पूरा", { exact: true })).toBeVisible();
  await p
    .getByRole("button", { name: "नामांकन रीफ़्रेश करें", exact: true })
    .click();
  await signOut(page);
  await login(page, c.parent);
  await page.goto("/parent/children");
  const parent = page.getByRole("region", {
    name: "बच्चे की कक्षाएँ",
    exact: true,
  });
  await parent
    .getByRole("button", { name: "कक्षाएँ रीफ़्रेश करें", exact: true })
    .click();
  await expect(parent.getByRole("article")).toHaveCount(2);
  await expect(parent.getByText("पूरा", { exact: true })).toBeVisible();
  await expect(
    parent.getByText("वापस लिया गया", { exact: true }),
  ).toBeVisible();
});
test("[ENROL-005] two managers recover a stale edit and explicitly act on the refreshed version", async ({
  page,
  browser,
}) => {
  const c = await connected(page);
  const p = await manager(page, c.coach);
  await enrol(page);
  const other = await browser.newContext();
  try {
    await other.route("**/*", (r) =>
      ["http://127.0.0.1:3193", "http://127.0.0.1:54321"].includes(
        new URL(r.request().url()).origin,
      )
        ? r.continue()
        : r.abort(),
    );
    const second = await other.newPage();
    const admin = await login(second);
    await second.goto("/founder");
    await second
      .getByRole("button", { name: "Refresh test records", exact: true })
      .click();
    await second
      .getByLabel("Test account", { exact: true })
      .selectOption({ label: admin });
    await second
      .getByLabel("Test workspace", { exact: true })
      .selectOption({ label: c.academy });
    await second.getByLabel("Role", { exact: true }).selectOption("admin");
    await second
      .getByRole("button", { name: "Apply test access", exact: true })
      .click();
    await expect(second.getByRole("status")).toContainText(
      "Test membership updated",
    );
    await second.goto("/students");
    const secondPanel = second.getByRole("region", {
      name: "Batch enrolment",
      exact: true,
    });
    const secondRow = secondPanel
      .getByRole("article")
      .filter({ hasText: CHILD });
    await expect(secondRow.getByText("Active", { exact: true })).toBeVisible();
    await page.bringToFront();
    const row = p.getByRole("article").filter({ hasText: CHILD });
    await expect(row.getByText("Active", { exact: true })).toBeVisible();
    await secondRow
      .getByLabel("Reason", { exact: true })
      .selectOption("temporary_break");
    // Another manager/device changes the real record without refocusing the first window.
    await secondRow
      .getByRole("button", { name: "Pause enrolment", exact: true })
      .evaluate((node: HTMLElement) => node.click());
    await expect(secondRow.getByText("Paused", { exact: true })).toBeVisible();
    await expect(row.getByText("Active", { exact: true })).toBeVisible();
    const attempts: string[] = [];
    await page.route("**/students", (r) => {
      const body = r.request().postData() || "";
      if (body.includes('"expectedVersion"')) attempts.push(body);
      return r.fallback();
    });
    await row
      .getByRole("button", { name: "Complete enrolment", exact: true })
      .click();
    await expect(row.getByText("Paused", { exact: true })).toBeVisible();
    await expect(
      p.getByRole("button", { name: "Refresh enrolments", exact: true }),
    ).toBeEnabled();
    await expect(
      p.getByLabel("Academy for enrolment", { exact: true }),
    ).toBeEnabled();
    await row
      .getByRole("button", { name: "Resume enrolment", exact: true })
      .click();
    await expect(row.getByText("Active", { exact: true })).toBeVisible();
    const versions = attempts.map(
      (s) => s.match(/"expectedVersion":(\d+)/)?.[1],
    );
    const ids = attempts.map((s) => s.match(/"requestId":"([0-9a-f-]+)"/)?.[1]);
    expect(versions[0] === "1" && versions[1] === "2").toBe(true);
    expect(Boolean(ids[0]) && Boolean(ids[1]) && ids[0] !== ids[1]).toBe(true);
  } finally {
    await other.close();
  }
});
