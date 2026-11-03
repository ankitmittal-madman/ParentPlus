import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { observeSessionChanges } from "./session-observer";

const mocks = vi.hoisted(() => ({ createClient: vi.fn(), onAuthStateChange: vi.fn(), unsubscribe: vi.fn() }));
vi.mock("../supabase/browser", () => ({ createClient: mocks.createClient }));

describe("observeSessionChanges", () => {
  beforeEach(() => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "false");
    mocks.createClient.mockReset();
    mocks.onAuthStateChange.mockReset();
    mocks.unsubscribe.mockReset();
    mocks.createClient.mockReturnValue({ auth: { onAuthStateChange: mocks.onAuthStateChange } });
    mocks.onAuthStateChange.mockReturnValue({ data: { subscription: { unsubscribe: mocks.unsubscribe } } });
  });
  afterEach(() => vi.unstubAllEnvs());

  it("does not subscribe when live authentication is disabled", () => {
    const cleanup = observeSessionChanges(vi.fn());
    cleanup();
    expect(mocks.createClient).not.toHaveBeenCalled();
  });

  it("ignores the initial event and reports later auth changes", () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    const changed = vi.fn();
    observeSessionChanges(changed);
    const callback = mocks.onAuthStateChange.mock.calls[0][0];
    callback("INITIAL_SESSION", { access_token: "never-use" });
    expect(changed).not.toHaveBeenCalled();
    callback("SIGNED_OUT", null);
    expect(changed).toHaveBeenCalledTimes(1);
    expect(changed).toHaveBeenCalledWith("SIGNED_OUT");
  });

  it("unsubscribes from provider notifications", () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    const cleanup = observeSessionChanges(vi.fn());
    cleanup();
    expect(mocks.unsubscribe).toHaveBeenCalledOnce();
  });
});
