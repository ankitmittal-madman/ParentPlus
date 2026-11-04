import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { verifyEmailOtp } from "./verify-email-otp";

const mocks = vi.hoisted(() => ({
  createClient: vi.fn(),
  verifyOtp: vi.fn(),
}));

vi.mock("../supabase/browser", () => ({
  createClient: mocks.createClient,
}));

describe("verifyEmailOtp", () => {
  beforeEach(() => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "false");
    mocks.verifyOtp.mockReset();
    mocks.createClient.mockReset();
    mocks.createClient.mockReturnValue({
      auth: { verifyOtp: mocks.verifyOtp },
    });
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("rejects invalid email without calling Supabase", async () => {
    const result = await verifyEmailOtp("invalid", "123456");

    expect(result.success).toBe(false);
    expect(mocks.createClient).not.toHaveBeenCalled();
  });

  it("rejects invalid OTP formats", async () => {
    for (const token of ["12345", "1234567", "abcdef", "12 456"]) {
      const result = await verifyEmailOtp("test@example.com", token);
      expect(result.success).toBe(false);
    }

    expect(mocks.createClient).not.toHaveBeenCalled();
  });

  it("blocks verification when live OTP is disabled", async () => {
    const result = await verifyEmailOtp("test@example.com", "123456");

    expect(result.success).toBe(false);
    expect(result.error).toContain("not enabled");
    expect(mocks.createClient).not.toHaveBeenCalled();
  });

  it("verifies a valid OTP when explicitly enabled", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");

    mocks.verifyOtp.mockResolvedValue({
      data: {
        user: { id: "test-user" },
        session: { access_token: "mock-token" },
      },
      error: null,
    });

    const result = await verifyEmailOtp(" TEST@EXAMPLE.COM ", "123456");

    expect(result.success).toBe(true);
    expect(mocks.verifyOtp).toHaveBeenCalledWith({
      email: "test@example.com",
      token: "123456",
      type: "email",
    });
  });

  it("accepts a pasted six-digit code with surrounding or internal spaces", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    mocks.verifyOtp.mockResolvedValue({ data: { user: { id: "test-user" }, session: { access_token: "mock-token" } }, error: null });
    const result = await verifyEmailOtp("parent@example.com", " 123 456 ");
    expect(result.success).toBe(true);
    expect(mocks.verifyOtp).toHaveBeenCalledWith({ email: "parent@example.com", token: "123456", type: "email" });
  });

  it("rejects expired or incorrect OTP responses", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");

    mocks.verifyOtp.mockResolvedValue({
      data: { user: null, session: null },
      error: { message: "Token expired" },
    });

    const result = await verifyEmailOtp("test@example.com", "123456");

    expect(result.success).toBe(false);
    expect(result.error).not.toContain("Token expired");
  });

  it("rejects missing sessions", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");

    mocks.verifyOtp.mockResolvedValue({
      data: { user: { id: "test-user" }, session: null },
      error: null,
    });

    const result = await verifyEmailOtp("test@example.com", "123456");

    expect(result.success).toBe(false);
  });

  it("handles unexpected client failures", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");

    mocks.createClient.mockImplementation(() => {
      throw new Error("Client unavailable");
    });

    const result = await verifyEmailOtp("test@example.com", "123456");

    expect(result.success).toBe(false);
    expect(result.error).toContain("Verification failed");
  });
});
