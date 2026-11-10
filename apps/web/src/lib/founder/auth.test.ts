import { afterEach, beforeEach, expect, it, vi } from "vitest";
const mocks = vi.hoisted(() => ({ client: vi.fn(), generate: vi.fn(), verify: vi.fn() }));
vi.mock("@supabase/supabase-js", () => ({ createClient: mocks.client }));
import { requestFounderOtp, verifyFounderOtp } from "./auth";
beforeEach(() => {
  vi.resetAllMocks(); vi.stubEnv("NODE_ENV", "development"); vi.stubEnv("PARENTPLUS_FOUNDER_MODE", "true"); vi.stubEnv("NEXT_PUBLIC_FOUNDER_MODE", "true");
  vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "http://127.0.0.1:54321"); vi.stubEnv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "local-public"); vi.stubEnv("PARENTPLUS_LOCAL_SERVICE_KEY", "local-private");
  mocks.client.mockReturnValue({ auth: { admin: { generateLink: mocks.generate }, verifyOtp: mocks.verify } });
});
afterEach(() => vi.unstubAllEnvs());
it("accepts fictional requests without sending any email", async () => {
  expect((await requestFounderOtp("parent@example.test")).success).toBe(true); expect(mocks.client).not.toHaveBeenCalled();
});
it("rejects incorrect codes and real email addresses before provider access", async () => {
  expect((await verifyFounderOtp("parent@example.test", "000000")).success).toBe(false);
  expect((await verifyFounderOtp("parent@example.com", "123456")).success).toBe(false); expect(mocks.client).not.toHaveBeenCalled();
});
it("returns only ordinary session tokens after the local exchange", async () => {
  mocks.generate.mockResolvedValue({ data: { properties: { hashed_token: "one-time" } }, error: null });
  mocks.verify.mockResolvedValue({ data: { user: { id: "user" }, session: { access_token: "user-access", refresh_token: "user-refresh" } }, error: null });
  expect(await verifyFounderOtp("parent@example.test", "123456")).toEqual({ success: true, error: null, session: { access_token: "user-access", refresh_token: "user-refresh" } });
  expect(mocks.generate).toHaveBeenCalledWith({ type: "magiclink", email: "parent@example.test" });
});
it("never creates an admin client in production or for hosted Supabase", async () => {
  vi.stubEnv("NODE_ENV", "production"); expect((await verifyFounderOtp("parent@example.test", "123456")).success).toBe(false);
  vi.stubEnv("NODE_ENV", "development"); vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://example.supabase.co"); expect((await verifyFounderOtp("parent@example.test", "123456")).success).toBe(false);
  expect(mocks.client).not.toHaveBeenCalled();
});
it("redacts local admin errors and does not return partial credentials", async () => {
  mocks.generate.mockRejectedValue(new Error("local-private")); const result = await verifyFounderOtp("parent@example.test", "123456");
  expect(result.success).toBe(false); expect(result.session).toBeNull(); expect(JSON.stringify(result)).not.toContain("local-private");
});
