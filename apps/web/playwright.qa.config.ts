import { defineConfig } from "@playwright/test";
import path from "node:path";

if (process.env.PARENTPLUS_FOUNDER_MODE !== "true" || process.env.NEXT_PUBLIC_SUPABASE_URL !== "http://127.0.0.1:54321" || !process.env.PARENTPLUS_QA_OUTPUT) {
  throw new Error("QA requires the local founder launcher and an explicit evidence directory.");
}
const output = process.env.PARENTPLUS_QA_OUTPUT;
export default defineConfig({
  testDir: "./e2e-qa", timeout: 90_000, expect: { timeout: 15_000 },
  forbidOnly: true, retries: 0, workers: 1, fullyParallel: false,
  outputDir: path.join(output, "raw"),
  reporter: [["line"], ["json", { outputFile: path.join(output, "playwright.json") }]],
  projects: [
    { name: "desktop", use: { viewport: { width: 1280, height: 900 } } },
    { name: "mobile", use: { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true } },
  ],
  use: {
    actionTimeout: 15000, navigationTimeout: 30000, baseURL: "http://127.0.0.1:3193", browserName: "chromium", headless: true,
    serviceWorkers: "block", trace: "off", video: "off", screenshot: "off",
    launchOptions: { executablePath: process.env.PARENTPLUS_CHROMIUM_PATH || undefined },
  },
  webServer: { command: "npm run dev -- --hostname 127.0.0.1 --port 3193", url: "http://127.0.0.1:3193/founder", reuseExistingServer: false, timeout: 120_000 },
});
