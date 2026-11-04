import { defineConfig } from "@playwright/test";

if (process.env.NEXT_PUBLIC_ENABLE_LIVE_OTP === "true") {
  throw new Error("Browser tests require live OTP to be disabled.");
}

export default defineConfig({
  testDir: "./e2e",
  outputDir: "./test-results/playwright",
  forbidOnly: true,
  retries: 0,
  workers: 1,
  reporter: [["line"], ["junit", { outputFile: "test-results/playwright-junit.xml" }]],
  use: {
    baseURL: "http://127.0.0.1:3189",
    browserName: "chromium",
    serviceWorkers: "block",
    launchOptions: { executablePath: process.env.PARENTPLUS_CHROMIUM_PATH || undefined },
  },
  webServer: {
    command: "npm run start -- --hostname 127.0.0.1 --port 3189",
    url: "http://127.0.0.1:3189/login",
    reuseExistingServer: false,
    timeout: 30000,
    env: { NEXT_PUBLIC_ENABLE_LIVE_OTP: "false", PARENTPLUS_ENABLE_PARENT_CHILD_LIST: "false" },
  },
});
