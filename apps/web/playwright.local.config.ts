import { defineConfig } from "@playwright/test";

// This suite deliberately uses real local Auth/PostgREST. No hosted endpoint.
if (process.env.PARENTPLUS_LOCAL_E2E !== "1" ||
    process.env.NEXT_PUBLIC_SUPABASE_URL !== "http://127.0.0.1:54321" ||
    process.env.NEXT_PUBLIC_ENABLE_LIVE_OTP !== "true") {
  throw new Error("Local E2E requires the explicitly selected loopback Supabase stack.");
}
export default defineConfig({
  testDir: "./e2e-local",
  timeout: 90_000,
  expect: { timeout: 15_000 },
  forbidOnly: true,
  workers: 1,
  retries: 0,
  reporter: [["line"], ["junit", { outputFile: "test-results/local-e2e-junit.xml" }]],
  outputDir: "test-results/local-e2e",
  use: {
    baseURL: "http://127.0.0.1:3192",
    serviceWorkers: "block",
    launchOptions: { executablePath: process.env.PARENTPLUS_CHROMIUM_PATH || "/usr/bin/chromium" },
    // Do not retain OTP/session-bearing traces or videos.
    trace: "off", video: "off", screenshot: "off",
  },
  webServer: {
    command: "npm run dev -- --hostname 127.0.0.1 --port 3192",
    url: "http://127.0.0.1:3192/login",
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
