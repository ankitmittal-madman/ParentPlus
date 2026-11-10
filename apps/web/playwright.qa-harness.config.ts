import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e-qa-harness", workers: 1, retries: 0, forbidOnly: true,
  reporter: [["line"]], outputDir: "../../test-results/qa/harness",
  use: { headless: true, browserName: "chromium", launchOptions: { executablePath: process.env.PARENTPLUS_CHROMIUM_PATH || undefined } },
});
