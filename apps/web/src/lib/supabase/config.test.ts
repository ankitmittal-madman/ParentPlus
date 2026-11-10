import { afterEach, expect, it, vi } from "vitest";
import { getSupabaseConfig } from "./config";
afterEach(() => vi.unstubAllEnvs());
it("allows HTTP only for exact loopback hosts and allows HTTPS", () => {
  for (const url of ["http://localhost:54321", "http://127.0.0.1:54321", "http://[::1]:54321", "https://example.supabase.co"]) {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", url);
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "public-key");
    expect(getSupabaseConfig().url).toBe(url);
  }
});
it("rejects remote HTTP, non-HTTP protocols and embedded credentials", () => {
  for (const url of ["http://example.supabase.co", "ftp://localhost", "https://user:secret@example.com"]) {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", url);
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "public-key");
    expect(() => getSupabaseConfig()).toThrow();
  }
});
it("blocks founder clients from using an unrelated project", () => {
  vi.stubEnv("NEXT_PUBLIC_FOUNDER_MODE", "true");
  vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://abcdefghijklmnopqrst.supabase.co");
  vi.stubEnv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "public-key");
  vi.stubEnv("NEXT_PUBLIC_FOUNDER_TEST_PROJECT_REF", "abcdefghijklmnopqrst");
  expect(() => getSupabaseConfig()).toThrow("selected test backend");
});
