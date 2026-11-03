import { AuthSessionMissingError } from "@supabase/supabase-js";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getSessionStatus } from "./session-status";

const mocks = vi.hoisted(() => ({ createClient: vi.fn(), getUser: vi.fn() }));
vi.mock("../supabase/browser", () => ({ createClient: mocks.createClient }));

describe("getSessionStatus", () => {
  beforeEach(() => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "false");
    mocks.getUser.mockReset();
    mocks.createClient.mockReset();
    mocks.createClient.mockReturnValue({ auth: { getUser: mocks.getUser } });
  });
  afterEach(() => vi.unstubAllEnvs());

  it("does not contact the provider when live authentication is disabled", async () => {
    expect(await getSessionStatus()).toEqual({ state: "signed-out" });
    expect(mocks.createClient).not.toHaveBeenCalled();
  });

  it("accepts a user confirmed by the provider", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    mocks.getUser.mockResolvedValue({ data: { user: { id: "synthetic-user", email_confirmed_at: null } }, error: null });
    expect(await getSessionStatus()).toEqual({ state: "signed-in" });
    expect(mocks.getUser).toHaveBeenCalledOnce();
  });

  it("treats a missing session as signed out", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    mocks.getUser.mockResolvedValue({ data: { user: null }, error: new AuthSessionMissingError() });
    expect(await getSessionStatus()).toEqual({ state: "signed-out" });
  });

  it("treats provider errors as unavailable without exposing details", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    mocks.getUser.mockResolvedValue({ data: { user: null }, error: { message: "private detail" } });
    expect(await getSessionStatus()).toEqual({ state: "unavailable" });
  });

  it("rejects a provider response without a valid user", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    mocks.getUser.mockResolvedValue({ data: { user: null }, error: null });
    expect(await getSessionStatus()).toEqual({ state: "unavailable" });
  });

  it("treats unexpected failures as unavailable", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    mocks.createClient.mockImplementation(() => { throw new Error("private detail"); });
    expect(await getSessionStatus()).toEqual({ state: "unavailable" });
  });
});
