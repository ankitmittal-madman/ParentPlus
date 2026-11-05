import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { signOut } from "./sign-out";
import { AuthClient } from "@supabase/supabase-js";

const mocks = vi.hoisted(() => ({ createClient: vi.fn(), signOut: vi.fn() }));
vi.mock("../supabase/browser", () => ({ createClient: mocks.createClient }));

describe("signOut", () => {
  beforeEach(() => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "false");
    mocks.signOut.mockReset();
    mocks.createClient.mockReset();
    mocks.createClient.mockReturnValue({ auth: { signOut: mocks.signOut } });
  });
  afterEach(() => vi.unstubAllEnvs());

  it("does not call the provider when live authentication is disabled", async () => {
    expect((await signOut()).success).toBe(false);
    expect(mocks.createClient).not.toHaveBeenCalled();
  });

  it("signs out only the current local session", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    mocks.signOut.mockResolvedValue({ error: null });
    expect((await signOut()).success).toBe(true);
    expect(mocks.signOut).toHaveBeenCalledWith({ scope: "local" });
  });

  it("does not expose provider error details", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    mocks.signOut.mockResolvedValue({ error: { message: "private provider detail" } });
    const result = await signOut();
    expect(result.success).toBe(false);
    expect(result.error).not.toContain("private provider detail");
  });

  it("handles unexpected provider failures", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    mocks.createClient.mockImplementation(() => { throw new Error("private provider detail"); });
    const result = await signOut();
    expect(result.success).toBe(false);
    expect(result.error).not.toContain("private provider detail");
  });
  it("reports uncertainty when the SDK clears local state before a provider error", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    const key = "synthetic-auth-session";
    const values = new Map<string, string>([[key, JSON.stringify({
      access_token: "synthetic-access", refresh_token: "synthetic-refresh",
      expires_at: Math.floor(Date.now() / 1000) + 3600, expires_in: 3600,
      token_type: "bearer", user: { id: "synthetic-user" },
    })]]);
    const storage = {
      getItem: (name: string) => values.get(name) ?? null,
      setItem: (name: string, value: string) => { values.set(name, value); },
      removeItem: (name: string) => { values.delete(name); },
    };
    const client = new AuthClient({
      url: "http://127.0.0.1:1", storageKey: key, storage,
      persistSession: true, autoRefreshToken: false, detectSessionInUrl: false,
      fetch: async () => new Response(JSON.stringify({ msg: "synthetic failure" }), {
        status: 500, headers: { "content-type": "application/json" },
      }),
    });
    await client.initialize();
    expect(values.has(key)).toBe(true);
    mocks.createClient.mockReturnValue({ auth: client });
    const result = await signOut();
    expect(result.success).toBe(false);
    expect(result.error).toContain("confirm sign-out");
    expect(values.has(key)).toBe(false);
  });

});
