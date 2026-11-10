import { test, expect } from "@playwright/test";
import { installActionObserver, type Action } from "../e2e-qa/action-observer";

test("discovers an unclicked control revealed only by a style change", async ({ page }) => {
  const seen: Action[] = [];
  await page.exposeBinding("qaRecord", (_source, action: Action) => { seen.push(action); });
  await page.addInitScript(installActionObserver);
  await page.route("http://qa.invalid/", route => route.fulfill({ contentType: "text/html", body: '<!doctype html><button style="display:none" id="later">New untested action</button>' }));
  await page.goto("http://qa.invalid/");
  await page.locator("#later").evaluate((element: HTMLElement) => { element.style.display = "block"; });
  await expect.poll(() => seen.some(a => a.name === "New untested action" && a.kind === "observed")).toBe(true);
  expect(seen.some(a => a.name === "New untested action" && a.kind === "clicked")).toBe(false);
});

test("records action names without field values and keeps busy button identity", async ({ page }) => {
  const seen: Action[] = [];
  await page.exposeBinding("qaRecord", (_source, action: Action) => { seen.push(action); });
  await page.addInitScript(installActionObserver);
  await page.route("http://qa.invalid/", route => route.fulfill({ contentType: "text/html", body: '<!doctype html><input value="private-fixture-value"><button id="save">Create workspace</button>' }));
  await page.goto("http://qa.invalid/");
  await expect.poll(() => seen.some(a => a.name === "Create workspace" && a.kind === "observed")).toBe(true);
  await page.getByRole("button", { name: "Create workspace" }).click();
  await page.locator("#save").evaluate(element => { element.textContent = "Creating…"; });
  await expect.poll(() => seen.some(a => a.kind === "clicked" && a.name === "Create workspace")).toBe(true);
  expect(JSON.stringify(seen)).not.toContain("private-fixture-value");
  expect(seen.some(a => a.name === "Creating…")).toBe(false);
  await page.locator("#save").evaluate(element => { element.textContent = "Verifying..."; });
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  expect(seen.some(a => a.name === "Verifying...")).toBe(false);
});
