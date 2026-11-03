import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { requestEmailOtp } from "./request-email-otp";

const mocks = vi.hoisted(() => ({
  createClient: vi.fn(),
  signInWithOtp: vi.fn(),
}));

vi.mock("../supabase/browser", () => ({
  createClient: mocks.createClient,
}));

describe("requestEmailOtp", () => {
  beforeEach(() => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "false");
    mocks.signInWithOtp.mockReset();
    mocks.createClient.mockReset();
    mocks.createClient.mockReturnValue({
      auth: { signInWithOtp: mocks.signInWithOtp },
    });
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("blocks OTP delivery by default", async () => {
    const result = await requestEmailOtp("test@example.com");

    expect(result.success).toBe(false);
    expect(result.error).toContain("not enabled");
    expect(mocks.createClient).not.toHaveBeenCalled();
  });

  it("rejects invalid email without calling Supabase", async () => {
    const result = await requestEmailOtp("invalid-email");

    expect(result.success).toBe(false);
    expect(mocks.createClient).not.toHaveBeenCalled();
  });

  it("normalizes email and prevents automatic signup", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    mocks.signInWithOtp.mockResolvedValue({ error: null });

    const result = await requestEmailOtp(" TEST@EXAMPLE.COM ");

    expect(result.success).toBe(true);
    expect(mocks.signInWithOtp).toHaveBeenCalledWith({
      email: "test@example.com",
      options: { shouldCreateUser: false },
    });
  });

  it("handles Supabase errors without exposing details", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    mocks.signInWithOtp.mockResolvedValue({
      error: { message: "Internal provider error" },
    });

    const result = await requestEmailOtp("test@example.com");

    expect(result.success).toBe(false);
    expect(result.error).not.toContain("Internal provider error");
  });

  it("handles unexpected client failures", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    mocks.createClient.mockImplementation(() => {
      throw new Error("Client unavailable");
    });

    const result = await requestEmailOtp("test@example.com");

    expect(result.success).toBe(false);
    expect(result.error).toContain("Unable to send");
  });

  it("does not call Supabase when delivery is disabled", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "false");

    await requestEmailOtp("test@example.com");

    expect(mocks.createClient).not.toHaveBeenCalled();
    expect(mocks.signInWithOtp).not.toHaveBeenCalled();
  });
});
