import { test as base, expect, type Page } from "@playwright/test";
import { randomUUID } from "node:crypto";
import { writeFileSync } from "node:fs";

import { installActionObserver, type Action } from "./action-observer";
export const test = base.extend<{ evidence: void }>({
  evidence: [async ({ page, context }, runFixture, info) => {
    const actions: Action[] = [];
    await context.route("**/*", route => ["http://127.0.0.1:3193", "http://127.0.0.1:54321"].includes(new URL(route.request().url()).origin) ? route.continue() : route.abort());
    await page.exposeBinding("qaRecord", (_source, action: Action) => {
      if (typeof action?.route === "string" && typeof action.name === "string" && ["observed", "clicked"].includes(action.kind)) actions.push({ route: action.route.slice(0, 120), name: action.name.slice(0, 120), kind: action.kind });
    });
    await page.addInitScript(installActionObserver);
    try { await runFixture(); }
    finally {
      const unique = [...new Map(actions.map(a => [JSON.stringify(a), a])).values()];
      const actionFile = info.outputPath("ui-actions.json");
      writeFileSync(actionFile, JSON.stringify(unique));
      await info.attach("ui-actions", { path: actionFile, contentType: "application/json" });
      if (!page.isClosed()) {
        const file = info.outputPath("outcome.png");
        await page.screenshot({ path: file, fullPage: true, timeout: 10000, mask: [page.locator('input[autocomplete="one-time-code"], [data-private="invite-link"]')] });
        await info.attach("outcome", { path: file, contentType: "image/png" });
      }
    }
  }, { auto: true }],
});
export { expect };
export const emailFor = () => `qa-${randomUUID()}@example.test`;
export async function login(page: Page, email = emailFor()) {
  await test.step("Sign in using fictional email and dummy OTP", async () => {
    await page.goto("/login");
    await page.getByLabel("Email address").fill(email);
    await page.getByRole("button", { name: "Continue", exact: true }).click();
    await page.getByLabel("Verification code").fill("123456");
    await page.getByRole("button", { name: "Verify code", exact: true }).click();
    await expect(page.getByText("Signed in.", { exact: true })).toBeVisible();
  });
  return email;
}
export async function workspace(page: Page, type = "independent") {
  const name = `QA ${type} ${randomUUID().slice(0, 8)}`;
  await test.step(`Create ${type} workspace through the app`, async () => {
    await page.goto("/coach-onboarding");
    await page.getByRole("button", { name: "Check workspace setup", exact: true }).click();
    await page.getByLabel("Workspace name").fill(name);
    await page.getByLabel("Workspace type").selectOption(type);
    await page.getByRole("button", { name: "Create workspace", exact: true }).click();
    await expect(page.getByText("Workspace setup confirmed.", { exact: true })).toBeVisible();
  });
  return name;
}
export async function child(page: Page, name = "Fictional QA Child", acknowledge = true) {
  await test.step("Create child profile and confirm the saved result", async () => {
    await page.goto("/parent/children");
    await page.getByRole("button", { name: "Check creation status", exact: true }).click();
    await page.getByLabel("Child name").fill(name);
    await page.getByRole("button", { name: "Create profile", exact: true }).click();
    await expect(page.getByText(`Profile: ${name}`, { exact: true })).toBeVisible();
    if (acknowledge) {
      await page.getByRole("button", { name: "Confirm result", exact: true }).click();
      await expect(page.getByText("Result confirmed", { exact: true })).toBeVisible();
    }
  });
}
export async function setup(page: Page) {
  await page.goto("/schedule");
  const panel = page.getByRole("region", { name: "Check class setup", exact: true });
  await panel.getByRole("button", { name: "Load academies", exact: true }).click();
  await panel.getByLabel("Academy", { exact: true }).selectOption({ index: 1 });
  return panel;
}
export async function schedule(page: Page, course = "QA Clay Basics") {
  const panel = await setup(page);
  await test.step("Save a three-session weekly class in the database", async () => {
    await panel.getByLabel("Course name", { exact: true }).fill(course);
    await panel.getByLabel("Batch name", { exact: true }).fill("QA Juniors");
    const zone = panel.getByLabel("Academy time zone", { exact: true });
    if (await zone.isEnabled()) await zone.fill("Asia/Kolkata");
    await panel.getByLabel("First session date").fill("2026-11-16");
    await panel.getByLabel("Local start time").fill("17:00");
    await panel.getByLabel("Last date for weekly sessions").fill("2026-11-30");
    await panel.getByRole("button", { name: "Create course, batch and weekly sessions", exact: true }).click();
    await expect(panel.getByText("Weekly schedule: 3 sessions", { exact: true })).toBeVisible();
  });
  return panel;
}
export async function membership(page: Page, email: string, name: string, status: string, role = "owner") {
  await page.goto("/founder");
  await page.getByRole("button", { name: "Refresh test records" }).click();
  await page.getByLabel("Test account").selectOption({ label: email });
  await page.getByLabel("Test workspace").selectOption({ label: name });
  await page.getByLabel("Role", { exact: true }).selectOption(role);
  await page.getByLabel("Access status").selectOption(status);
  await page.getByRole("button", { name: "Apply test access" }).click();
  await expect(page.getByRole("status")).toContainText("Test membership updated");
}
