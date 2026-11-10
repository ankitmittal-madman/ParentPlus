import { defineConfig } from "@playwright/test";
if (process.env.PARENTPLUS_FOUNDER_MODE !== "true" || process.env.NEXT_PUBLIC_SUPABASE_URL !== "http://127.0.0.1:54321") throw new Error("Founder tests require the local launcher.");
export default defineConfig({
  testDir: "./e2e-founder", timeout: 90_000, expect: { timeout: 15_000 }, workers: 1, retries: 0, forbidOnly: true,
  reporter: [["line"], ["junit", { outputFile: "test-results/founder-junit.xml" }]], outputDir: "test-results/founder",
  use: { baseURL: "http://127.0.0.1:3193", serviceWorkers: "block", trace: "off", video: "off", screenshot: "off", launchOptions: { executablePath: process.env.PARENTPLUS_CHROMIUM_PATH || "/usr/bin/chromium" } },
  webServer: { command: "npm run dev -- --hostname 127.0.0.1 --port 3193", url: "http://127.0.0.1:3193/founder", reuseExistingServer: false, timeout: 120_000 },
});
