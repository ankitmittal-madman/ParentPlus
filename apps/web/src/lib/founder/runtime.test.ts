import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { founderConfig } from "./runtime";
beforeEach(() => {
  vi.stubEnv("NODE_ENV", "development"); vi.stubEnv("PARENTPLUS_FOUNDER_MODE", "true");
  vi.stubEnv("NEXT_PUBLIC_FOUNDER_MODE", "true"); vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "http://127.0.0.1:54321");
  vi.stubEnv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "local-public"); vi.stubEnv("PARENTPLUS_LOCAL_SERVICE_KEY", "local-private");
});
afterEach(() => vi.unstubAllEnvs());
it("enables explicitly configured local development", () => expect(founderConfig()?.url).toBe("http://127.0.0.1:54321"));
it("refuses production even with founder flags enabled", () => { vi.stubEnv("NODE_ENV", "production"); expect(founderConfig()).toBeNull(); });
it("refuses hosted endpoints and disabled server mode", () => {
  vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://example.supabase.co"); expect(founderConfig()).toBeNull();
  vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "http://127.0.0.1:54321"); vi.stubEnv("PARENTPLUS_FOUNDER_MODE", "false"); expect(founderConfig()).toBeNull();
});
it("supports an explicitly configured hosted testing build with the selected backend", () => {
  vi.stubEnv("NODE_ENV", "production"); vi.stubEnv("PARENTPLUS_APP_STAGE", "testing");
  vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://fmavpazczahxeusqbxuh.supabase.co");
  vi.stubEnv("NEXT_PUBLIC_FOUNDER_TEST_PROJECT_REF", "fmavpazczahxeusqbxuh");
  vi.stubEnv("PARENTPLUS_TEST_SERVICE_KEY", "separate-test-private");
  expect(founderConfig()?.url).toBe("https://fmavpazczahxeusqbxuh.supabase.co");
});
it("refuses an unrelated hosted project even in testing mode", () => {
  vi.stubEnv("NODE_ENV", "production"); vi.stubEnv("PARENTPLUS_APP_STAGE", "testing");
  vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://abcdefghijklmnopqrst.supabase.co");
  vi.stubEnv("NEXT_PUBLIC_FOUNDER_TEST_PROJECT_REF", "abcdefghijklmnopqrst");
  vi.stubEnv("PARENTPLUS_TEST_SERVICE_KEY", "protected-private");
  expect(founderConfig()).toBeNull();
});
it("does not mistake a launched build or mismatched backend for a testing app", () => {
  vi.stubEnv("NODE_ENV", "production"); vi.stubEnv("PARENTPLUS_APP_STAGE", "launch");
  vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://fmavpazczahxeusqbxuh.supabase.co");
  vi.stubEnv("NEXT_PUBLIC_FOUNDER_TEST_PROJECT_REF", "fmavpazczahxeusqbxuh");
  vi.stubEnv("PARENTPLUS_TEST_SERVICE_KEY", "separate-test-private");
  expect(founderConfig()).toBeNull();
  vi.stubEnv("PARENTPLUS_APP_STAGE", "testing"); vi.stubEnv("NEXT_PUBLIC_FOUNDER_TEST_PROJECT_REF", "differentprojectrefxx");
  expect(founderConfig()).toBeNull();
});
