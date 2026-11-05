import { defineConfig } from "@playwright/test";
import { execFileSync } from "node:child_process";

if (process.env.PARENTPLUS_SYNTHETIC_BROWSER !== "1" ||
    process.env.NEXT_PUBLIC_SUPABASE_URL !== "http://localhost:3191" ||
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY !== "synthetic-public-key" ||
    process.env.NEXT_PUBLIC_ENABLE_LIVE_OTP !== "true" ||
    process.env.PARENTPLUS_ENABLE_CHILD_CREATION !== "true" ||
    process.env.PARENTPLUS_ENABLE_PARENT_CHILD_LIST !== "true") {
  throw new Error("The enabled browser suite requires the isolated synthetic provider.");
}
if (!process.env.PARENTPLUS_CHROMIUM_PATH) throw new Error("An explicit local Chromium executable is required.");
const links = JSON.parse(execFileSync("/usr/sbin/ip", ["-j", "link", "show"], { encoding: "utf8" }));
if (links.length !== 1 || links[0].ifname !== "lo") throw new Error("Enabled browser checks require a loopback-only namespace.");
for (const family of ["-4", "-6"]) {
  const routes = JSON.parse(execFileSync("/usr/sbin/ip", ["-j", family, "route", "show", "table", "all"], { encoding: "utf8" }));
  if (routes.some((route) => (route.dev && route.dev !== "lo") || route.dst === "default")) throw new Error("Enabled browser checks require loopback-only routes.");
}

export default defineConfig({
  testDir: "./e2e-enabled",
  testMatch: "parent-enabled.spec.mjs",
  outputDir: "./test-results/playwright-enabled",
  forbidOnly: true,
  retries: 0,
  workers: 1,
  reporter: [["line"], ["junit", { outputFile: "test-results/playwright-enabled-junit.xml" }]],
  use: {
    baseURL: "http://127.0.0.1:3190",
    browserName: "chromium",
    serviceWorkers: "block",
    launchOptions: { executablePath: process.env.PARENTPLUS_CHROMIUM_PATH },
  },
});
