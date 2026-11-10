import { test, expect, type Page, type BrowserContext } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { randomUUID } from "node:crypto";

const API = "http://127.0.0.1:54321";
const MAIL = "http://127.0.0.1:54324";
const UUID = /^[a-f0-9-]{36}$/;
let controls: { table: string; enabled: boolean }[] = [];
function sql(statement: string) {
  return execFileSync("docker", ["--host=unix:///var/run/docker.sock", "exec", "-i", "supabase_db_ParentPlus", "psql", "-XAt", "-v", "ON_ERROR_STOP=1", "-U", "postgres", "-d", "postgres"], { input: statement, encoding: "utf8" }).trim();
}
async function isolate(context: BrowserContext) {
  await context.route("**/*", route => {
    const origin = new URL(route.request().url()).origin;
    return ["http://127.0.0.1:3192", API].includes(origin) ? route.continue() : route.abort();
  });
}
async function signup(page: Page, label: string) {
  const email = `local-${label}-${randomUUID()}@example.test`;
  await page.goto("/login");
  await page.getByRole("button", { name: "Create account", exact: true }).click();
  await page.getByLabel("Email address").fill(email);
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(page.getByLabel("Verification code")).toBeVisible();
  let messageId = "";
  await expect.poll(async () => {
    const response = await page.request.get(`${MAIL}/api/v1/messages`);
    const body = await response.json();
    const message = body.messages?.find((m: { To: { Address: string }[] }) => m.To?.some(to => to.Address === email));
    messageId = message?.ID ?? "";
    return Boolean(messageId);
  }).toBe(true);
  const message = await (await page.request.get(`${MAIL}/api/v1/message/${messageId}`)).json();
  const code = `${message.Text} ${message.HTML}`.match(/\b\d{6}\b/)?.[0];
  if (!code) throw new Error("The local email template did not provide a six-digit OTP");
  // Prove that a syntactically valid, incorrect code does not establish a session.
  const wrongCode = code === "000000" ? "000001" : "000000";
  await page.getByLabel("Verification code").fill(wrongCode);
  await page.getByRole("button", { name: "Verify code", exact: true }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Verification failed" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Continue to coach area" })).toHaveCount(0);
  await page.getByLabel("Verification code").fill(code);
  await page.getByRole("button", { name: "Verify code", exact: true }).click();
  await expect(page.getByText("Signed in.", { exact: true })).toBeVisible();
  const actor = sql(`select id from auth.users where email='${email}'`);
  if (!UUID.test(actor)) throw new Error("Unexpected local actor identifier");
  return actor;
}
test.beforeAll(() => {
  const names = ["parent_child_read_controls", "child_creation_controls", "class_setup_controls", "workspace_creation_controls"];
  controls = names.map(table => ({ table, enabled: sql(`select enabled from public.${table} where id`) === "t" }));
  for (const { table } of controls) sql(`update public.${table} set enabled=true where id`);
});
test.afterAll(() => {
  for (const { table, enabled } of controls) sql(`update public.${table} set enabled=${enabled} where id`);
  // Synthetic test records are retained locally for inspection. Never reset or
  // delete an existing workspace or database to make these journeys repeatable.
});

test("parent signup, OTP rejection, profile creation, recovery, isolation and sign-out", async ({ page, context, browser }) => {
  await isolate(context);
  const parent = await signup(page, "parent");
  await page.getByRole("link", { name: "View profiles you created" }).click();
  await page.getByRole("button", { name: "Check creation status", exact: true }).click();
  await page.getByLabel("Child name").fill("Fictional Parent Journey Child");
  await page.getByRole("button", { name: "Create profile", exact: true }).click();
  await expect(page.getByRole("button", { name: "Confirm result", exact: true })).toBeVisible();
  await page.reload();
  await page.getByRole("button", { name: "Check creation status", exact: true }).click();
  await expect(page.getByText("Fictional Parent Journey Child", { exact: false }).first()).toBeVisible();
  await page.getByRole("button", { name: "Confirm result", exact: true }).click();
  await page.getByRole("button", { name: "Load profiles", exact: true }).click();
  await expect(page.getByRole("listitem").filter({ hasText: "Fictional Parent Journey Child" })).toHaveCount(1);
  expect(sql(`select count(*) from public.children where created_by='${parent}'`)).toBe("1");
  expect(sql(`select status||':'||verification_level from public.guardianships where guardian_user_id='${parent}'`)).toBe("provisional:self_declared");
  const other = await browser.newContext({ baseURL: "http://127.0.0.1:3192" });
  try {
    await isolate(other);
    const outsider = await other.newPage();
    await signup(outsider, "outsider");
    await outsider.getByRole("link", { name: "View profiles you created" }).click();
    await outsider.getByRole("button", { name: "Load profiles", exact: true }).click();
    await expect(outsider.getByText("No profiles available for this account.")).toBeVisible();
    await expect(outsider.getByText("Fictional Parent Journey Child")).toHaveCount(0);
  } finally { await other.close(); }
  await page.goto("/login");
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page.getByLabel("Email address")).toBeVisible();
  await expect(page.getByRole("link", { name: "Continue to coach area" })).toHaveCount(0);
  await page.goto("/parent/children");
  await page.getByRole("button", { name: "Load profiles", exact: true }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Unable to load profiles" })).toBeVisible();
  await expect(page.getByText("Fictional Parent Journey Child")).toHaveCount(0);
});

for (const workspaceType of ["independent", "academy"] as const) {
test(`coach ${workspaceType} membership gate, weekly class setup, reload, acknowledgement and revocation`, async ({ page, context }) => {
  await isolate(context);
  const coach = await signup(page, "coach");
  await page.getByRole("link", { name: "Continue to coach area" }).click();
  await expect(page).toHaveURL(/\/coach-access$/);
  await page.getByRole("link", { name: "Set up your own workspace" }).click();
  await page.getByRole("button", { name: "Check workspace setup", exact: true }).click();
  await page.getByLabel("Workspace name").fill("Fictional E2E Coaching");
  await page.getByLabel("Workspace type").selectOption(workspaceType);
  await page.getByRole("button", { name: "Create workspace", exact: true }).click();
  await expect(page.getByRole("link", { name: "Continue to class setup" })).toBeVisible();
  await page.reload();
  await page.getByRole("button", { name: "Check workspace setup", exact: true }).click();
  await expect(page.getByRole("link", { name: "Continue to class setup" })).toBeVisible();
  const workspace = sql(`select id from public.workspaces where created_by='${coach}'`);
  expect(UUID.test(workspace)).toBe(true);
  expect(sql(`select count(*) from public.workspaces where created_by='${coach}'`)).toBe("1");
  await page.getByRole("link", { name: "Continue to class setup" }).click();
  await page.goto("/schedule");
  const setup = page.getByRole("region", { name: "Check class setup", exact: true });
  await setup.getByRole("button", { name: "Load academies", exact: true }).click();
  await setup.getByLabel("Academy", { exact: true }).selectOption(workspace);
  await setup.getByLabel("Course name", { exact: true }).fill("Fictional Clay Basics");
  await setup.getByLabel("Batch name", { exact: true }).fill("Fictional Clay Juniors");
  await setup.getByLabel("Academy time zone", { exact: true }).fill("Asia/Kolkata");
  await setup.getByLabel("First session date").fill("2026-11-16");
  await setup.getByLabel("Local start time").fill("17:00");
  await setup.getByLabel("Last date for weekly sessions").fill("2026-11-30");
  await expect(setup.getByLabel("Course name", { exact: true })).toHaveValue("Fictional Clay Basics");
  await expect(setup.getByLabel("Batch name", { exact: true })).toHaveValue("Fictional Clay Juniors");
  await expect(setup.getByLabel("Academy time zone", { exact: true })).toHaveValue("Asia/Kolkata");
  await expect(setup.getByLabel("First session date")).toHaveValue("2026-11-16");
  await expect(setup.getByLabel("Local start time")).toHaveValue("17:00");
  await expect(setup.getByLabel("Last date for weekly sessions")).toHaveValue("2026-11-30");
  await expect(setup.getByRole("button", { name: "Create course, batch and weekly sessions", exact: true })).toBeEnabled();
  await setup.getByRole("button", { name: "Create course, batch and weekly sessions", exact: true }).click();
  await expect(setup.getByRole("button", { name: "Confirm course, batch and schedule", exact: true })).toBeVisible();
  expect(sql(`select count(*) from public.schedule_sessions where workspace_id='${workspace}'`)).toBe("3");
  await page.reload();
  await setup.getByRole("button", { name: "Load academies", exact: true }).click();
  await setup.getByLabel("Academy", { exact: true }).selectOption(workspace);
  await expect(setup.getByText("Fictional Clay Basics", { exact: false }).first()).toBeVisible();
  await setup.getByRole("button", { name: "Confirm course, batch and schedule", exact: true }).click();
  expect(sql(`select count(*) from public.schedule_sessions where workspace_id='${workspace}'`)).toBe("3");
  sql(`update public.workspace_memberships set status='suspended' where workspace_id='${workspace}' and user_id='${coach}'`);
  await page.reload();
  await expect(page).toHaveURL(/\/coach-access$/);
  await expect(page.getByText("Fictional Clay Basics")).toHaveCount(0);
  await page.goto("/login");
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await page.goto("/schedule");
  await expect(page).toHaveURL(/\/login$/);
});
}
