import { afterEach, expect, it, vi } from "vitest";
import settings from "../../../founder-testing.config.json";
afterEach(() => { vi.unstubAllEnvs(); vi.resetModules(); });
it("enables dummy OTP and implemented features for Vercel testing builds", async () => {
  vi.stubEnv("VERCEL", "1"); vi.stubEnv("PARENTPLUS_APP_STAGE", "testing"); vi.resetModules();
  const { default: config } = await import("../../../next.config");
  expect(config.env?.NEXT_PUBLIC_FOUNDER_MODE).toBe("true");
  expect(config.env?.PARENTPLUS_ENABLE_CHILD_CREATION).toBe("true");
  expect(config.env?.NEXT_PUBLIC_SUPABASE_URL).toBe("https://fmavpazczahxeusqbxuh.supabase.co");
});
it("does not force testing mode after an explicit launch-stage build", async () => {
  vi.stubEnv("VERCEL", "1"); vi.stubEnv("PARENTPLUS_APP_STAGE", "launch"); vi.resetModules();
  const { default: config } = await import("../../../next.config"); expect(config.env).toBeUndefined();
});
it("contains only non-secret testing defaults and an anon-role public key", () => {
  expect(Object.keys(settings).some(k => /SERVICE_KEY|SERVICE_ROLE|PASSWORD|TOKEN/.test(k))).toBe(false);
  const payload = JSON.parse(Buffer.from(settings.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY.split('.')[1], "base64url").toString());
  expect(payload.role).toBe("anon"); expect(payload.ref).toBe("fmavpazczahxeusqbxuh");
});
