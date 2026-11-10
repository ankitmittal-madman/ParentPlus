import { execFileSync } from "node:child_process";
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

test("redacts an invitation from an actual failed navigation diagnostic", async ({ page }) => {
  const secret="bd".repeat(32);
  let failure="";
  try { await page.goto("http://127.0.0.1:1/join#"+secret); } catch(error) { failure=String(error); }
  expect(failure.includes(secret)).toBe(true);
  const sanitised=execFileSync("python3",["-c","import sys; sys.path.insert(0, '../../scripts/qa'); from report import redact; print(redact(sys.stdin.read()))"],{input:failure,encoding:"utf8"});
  expect(sanitised.includes(secret)).toBe(false);
  expect(sanitised).toContain("[redacted invite]");
});

test("groups dynamic roster controls by explicit action while preserving accessible child names", async ({ page }) => {
  const seen: Action[] = [];
  await page.exposeBinding("qaRecord", (_source, action: Action) => { seen.push(action); });
  await page.addInitScript(installActionObserver);
  await page.route("http://qa.invalid/", route => route.fulfill({ contentType: "text/html", body: '<!doctype html><button data-qa-action="Mark present" aria-label="Mark Fictional A present"><span>P</span></button><button data-qa-action="Mark present" aria-label="Mark Fictional B present">P</button><button>Unmapped new action</button>' }));
  await page.goto("http://qa.invalid/");
  await expect(page.getByRole("button", { name: "Mark Fictional A present", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Mark Fictional A present", exact: true }).locator("span").click();
  await page.getByRole("button", { name: "Mark Fictional B present", exact: true }).click();
  await expect.poll(() => seen.filter(a => a.kind === "clicked" && a.name === "Mark present").length).toBe(2);
  expect(seen.some(a => a.kind === "observed" && a.name === "Unmapped new action")).toBe(true);
  await expect(page.getByRole("button", { name: "Mark Fictional B present", exact: true })).toBeVisible();
});

test("observes renamed explicit actions and keeps empty action attributes discoverable", async ({ page }) => {
  const seen: Action[] = [];
  await page.exposeBinding("qaRecord", (_source, action: Action) => { seen.push(action); });
  await page.addInitScript(installActionObserver);
  await page.route("http://qa.invalid/", route => route.fulfill({ contentType: "text/html", body: '<!doctype html><button id="action" data-qa-action="Load sessions">Load this day</button><button data-qa-action="   ">Ordinary fallback action</button>' }));
  await page.goto("http://qa.invalid/");
  await expect.poll(() => seen.some(a => a.name === "Load sessions" && a.kind === "observed")).toBe(true);
  await page.locator("#action").evaluate(element => element.setAttribute("data-qa-action", "Refresh sessions"));
  await expect.poll(() => seen.some(a => a.name === "Refresh sessions" && a.kind === "observed")).toBe(true);
  await expect.poll(() => seen.some(a => a.name === "Ordinary fallback action" && a.kind === "observed")).toBe(true);
});
