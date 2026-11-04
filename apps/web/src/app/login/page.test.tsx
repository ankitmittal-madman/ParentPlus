import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import LoginPage from "./page";

const mocks = vi.hoisted(() => ({
  requestEmailOtp: vi.fn(),
  verifyEmailOtp: vi.fn(),
  signOut: vi.fn(),
  getSessionStatus: vi.fn(),
  observeSessionChanges: vi.fn(),
}));

vi.mock("@/lib/auth/request-email-otp", () => ({
  requestEmailOtp: mocks.requestEmailOtp,
}));

vi.mock("@/lib/auth/verify-email-otp", () => ({ verifyEmailOtp: mocks.verifyEmailOtp }));

vi.mock("@/lib/auth/sign-out", () => ({ signOut: mocks.signOut }));

vi.mock("@/lib/auth/session-status", () => ({ getSessionStatus: mocks.getSessionStatus }));

vi.mock("@/lib/auth/session-observer", () => ({ observeSessionChanges: mocks.observeSessionChanges }));

describe("LoginPage", () => {
  beforeEach(() => {
    mocks.requestEmailOtp.mockReset();
    mocks.verifyEmailOtp.mockReset();
    mocks.signOut.mockReset();
    mocks.getSessionStatus.mockReset();
    mocks.observeSessionChanges.mockReset();
    mocks.observeSessionChanges.mockReturnValue(() => {});
    mocks.getSessionStatus.mockResolvedValue({ state: "signed-out" });
  });

  afterEach(() => vi.unstubAllEnvs());

  it("renders an accessible email form", () => {
    render(<LoginPage />);

    expect(screen.getByRole("heading", {
      name: "Welcome to Parent Plus",
    })).toBeInTheDocument();

    expect(screen.getByRole("textbox", {
      name: "Email address",
    })).toBeInTheDocument();
  });

  it("hides account creation while it is disabled", () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_ACCOUNT_SIGNUP", "false");
    render(<LoginPage />);
    expect(screen.queryByRole("button", { name: "Create account" })).not.toBeInTheDocument();
  });

  it("requests signup only after explicitly selecting account creation", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_ACCOUNT_SIGNUP", "true");
    mocks.requestEmailOtp.mockResolvedValue({ success: true, error: null });
    render(<LoginPage />);
    fireEvent.click(screen.getByRole("button", { name: "Create account" }));
    fireEvent.change(screen.getByLabelText("Email address"), { target: { value: " PARENT@EXAMPLE.COM " } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    await waitFor(() => expect(mocks.requestEmailOtp).toHaveBeenCalledWith("parent@example.com", "sign-up"));
    expect(await screen.findByLabelText("Verification code")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Sign in instead" }));
    expect(screen.queryByLabelText("Verification code")).not.toBeInTheDocument();
  });

  it("completes the local signup code flow only after verification succeeds", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_ACCOUNT_SIGNUP", "true");
    mocks.requestEmailOtp.mockResolvedValue({ success: true, error: null });
    mocks.verifyEmailOtp.mockResolvedValue({ success: true, error: null });
    render(<LoginPage />);
    fireEvent.click(screen.getByRole("button", { name: "Create account" }));
    fireEvent.change(screen.getByLabelText("Email address"), { target: { value: "parent@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(screen.queryByText("Signed in.")).not.toBeInTheDocument();
    fireEvent.change(await screen.findByLabelText("Verification code"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Verify code" }));
    expect(await screen.findByText("Signed in.")).toBeInTheDocument();
    expect(mocks.verifyEmailOtp).toHaveBeenCalledWith("parent@example.com", "123456");
  });

  it("prevents changing signup mode during an in-flight request", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_ACCOUNT_SIGNUP", "true");
    let finish!: (value: { success: boolean; error: null }) => void;
    mocks.requestEmailOtp.mockReturnValue(new Promise((resolve) => { finish = resolve; }));
    render(<LoginPage />);
    fireEvent.click(screen.getByRole("button", { name: "Create account" }));
    fireEvent.change(screen.getByLabelText("Email address"), { target: { value: "parent@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(screen.getByRole("button", { name: "Sign in instead" })).toBeDisabled();
    await act(async () => finish({ success: true, error: null }));
    expect(await screen.findByLabelText("Verification code")).toBeInTheDocument();
    expect(mocks.requestEmailOtp).toHaveBeenCalledTimes(1);
  });

  it("returns to sign-in mode after a provider sign-in event interrupts signup verification", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    vi.stubEnv("NEXT_PUBLIC_ENABLE_ACCOUNT_SIGNUP", "true");
    let notify!: (event: string) => void;
    let finish!: (value: { success: boolean; error: null }) => void;
    mocks.observeSessionChanges.mockImplementation((callback) => { notify = callback; return () => {}; });
    mocks.getSessionStatus.mockResolvedValueOnce({ state: "signed-out" }).mockResolvedValueOnce({ state: "signed-in" });
    mocks.requestEmailOtp.mockResolvedValue({ success: true, error: null });
    mocks.verifyEmailOtp.mockReturnValue(new Promise((resolve) => { finish = resolve; }));
    mocks.signOut.mockResolvedValue({ success: true, error: null });
    render(<LoginPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Create account" }));
    fireEvent.change(screen.getByLabelText("Email address"), { target: { value: "parent@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    fireEvent.change(await screen.findByLabelText("Verification code"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Verify code" }));
    act(() => notify("SIGNED_IN"));
    await act(async () => finish({ success: true, error: null }));
    fireEvent.click(await screen.findByRole("button", { name: "Sign out" }));
    expect(await screen.findByRole("button", { name: "Create account" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Email address"), { target: { value: "other@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    await waitFor(() => expect(mocks.requestEmailOtp).toHaveBeenLastCalledWith("other@example.com"));
  });

  it("keeps repeat code requests in explicitly selected signup mode", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_ACCOUNT_SIGNUP", "true");
    mocks.requestEmailOtp.mockResolvedValue({ success: true, error: null });
    render(<LoginPage />);
    fireEvent.click(screen.getByRole("button", { name: "Create account" }));
    fireEvent.change(screen.getByLabelText("Email address"), { target: { value: "parent@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    fireEvent.click(await screen.findByRole("button", { name: "Request another code" }));
    await waitFor(() => expect(mocks.requestEmailOtp).toHaveBeenCalledTimes(2));
    expect(mocks.requestEmailOtp).toHaveBeenLastCalledWith("parent@example.com", "sign-up");
  });

  it("rejects invalid email without calling OTP service", async () => {
    render(<LoginPage />);

    fireEvent.change(screen.getByRole("textbox", {
      name: "Email address",
    }), { target: { value: "invalid-email" } });

    fireEvent.click(screen.getByRole("button", {
      name: "Continue",
    }));

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Enter a valid email address."
    );
    expect(mocks.requestEmailOtp).not.toHaveBeenCalled();
  });

  it("requests OTP with normalized email", async () => {
    mocks.requestEmailOtp.mockResolvedValue({
      success: true,
      error: null,
    });

    render(<LoginPage />);

    fireEvent.change(screen.getByRole("textbox", {
      name: "Email address",
    }), { target: { value: " TEST@EXAMPLE.COM " } });

    fireEvent.click(screen.getByRole("button", {
      name: "Continue",
    }));

    await waitFor(() => {
      expect(mocks.requestEmailOtp).toHaveBeenCalledWith(
        "test@example.com"
      );
    });

    expect(await screen.findByRole("status")).toHaveTextContent(
      "Verification request accepted."
    );
  });

  it("focuses the code field after an accepted verification request", async () => {
    mocks.requestEmailOtp.mockResolvedValue({ success: true, error: null });
    render(<LoginPage />);
    fireEvent.change(screen.getByLabelText("Email address"), { target: { value: "parent@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    const code = await screen.findByLabelText("Verification code");
    await waitFor(() => expect(code).toHaveFocus());
  });

  it("allows requesting another code after an accepted request", async () => {
    mocks.requestEmailOtp.mockResolvedValue({ success: true, error: null });
    render(<LoginPage />);
    fireEvent.change(screen.getByLabelText("Email address"), { target: { value: "parent@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    fireEvent.click(await screen.findByRole("button", { name: "Request another code" }));
    await waitFor(() => expect(mocks.requestEmailOtp).toHaveBeenCalledTimes(2));
    expect(await screen.findByText(/Verification request accepted/)).toBeInTheDocument();
    expect(await screen.findByLabelText("Verification code")).toBeInTheDocument();
  });

  it("clearly offers another code request and reports a failed retry", async () => {
    mocks.requestEmailOtp.mockResolvedValueOnce({ success: true, error: null }).mockResolvedValueOnce({ success: false, error: "Unable to send verification code. Please try again." });
    render(<LoginPage />);
    fireEvent.change(screen.getByLabelText("Email address"), { target: { value: " TEST@EXAMPLE.COM " } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    fireEvent.change(await screen.findByLabelText("Verification code"), { target: { value: "123456" } });
    fireEvent.click(await screen.findByRole("button", { name: "Request another code" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Unable to confirm the latest request");
    expect(mocks.requestEmailOtp).toHaveBeenCalledTimes(2);
    expect(mocks.requestEmailOtp).toHaveBeenLastCalledWith("test@example.com");
    expect(screen.queryByText(/Verification request accepted/)).not.toBeInTheDocument();
    expect(screen.getByLabelText("Verification code")).toHaveValue("123456");
    expect(screen.getByRole("status")).toHaveTextContent(/latest request could not be confirmed/i);
  });

  it("keeps the entered code when a repeat request throws", async () => {
    mocks.requestEmailOtp.mockResolvedValueOnce({ success: true, error: null }).mockRejectedValueOnce(new Error("private provider detail"));
    render(<LoginPage />);
    fireEvent.change(screen.getByLabelText("Email address"), { target: { value: "parent@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    fireEvent.change(await screen.findByLabelText("Verification code"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Request another code" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Unable to confirm the latest request");
    expect(screen.getByLabelText("Verification code")).toHaveValue("123456");
    expect(screen.queryByText(/private provider detail/)).not.toBeInTheDocument();
    expect(screen.queryByText("Signed in.")).not.toBeInTheDocument();
  });

  it("ignores a failed repeat request after an account change", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    let notify!: (event: string) => void;
    let finish!: (value: { success: boolean; error: string }) => void;
    mocks.observeSessionChanges.mockImplementation((callback) => { notify = callback; return () => {}; });
    mocks.getSessionStatus.mockResolvedValueOnce({ state: "signed-out" }).mockResolvedValueOnce({ state: "signed-in" });
    mocks.requestEmailOtp.mockResolvedValueOnce({ success: true, error: null }).mockReturnValueOnce(new Promise((resolve) => { finish = resolve; }));
    render(<LoginPage />);
    fireEvent.change(await screen.findByLabelText("Email address"), { target: { value: "old@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    fireEvent.change(await screen.findByLabelText("Verification code"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Request another code" }));
    act(() => notify("SIGNED_IN"));
    await act(async () => finish({ success: false, error: "private provider detail" }));
    expect(await screen.findByRole("button", { name: "Sign out" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Verification code")).not.toBeInTheDocument();
    expect(screen.queryByText(/private provider detail/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Unable to confirm the latest request/)).not.toBeInTheDocument();
  });

  it("shows service errors without claiming delivery", async () => {
    mocks.requestEmailOtp.mockResolvedValue({
      success: false,
      error: "Email verification is not enabled in this environment.",
    });

    render(<LoginPage />);

    fireEvent.change(screen.getByRole("textbox", {
      name: "Email address",
    }), { target: { value: "test@example.com" } });

    fireEvent.click(screen.getByRole("button", {
      name: "Continue",
    }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "not enabled"
    );
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("prevents duplicate requests while loading", async () => {
    let resolveRequest!: (value: {
      success: boolean;
      error: null;
    }) => void;

    mocks.requestEmailOtp.mockReturnValue(
      new Promise((resolve) => {
        resolveRequest = resolve;
      })
    );

    render(<LoginPage />);

    fireEvent.change(screen.getByRole("textbox", {
      name: "Email address",
    }), { target: { value: "test@example.com" } });

    fireEvent.click(screen.getByRole("button", {
      name: "Continue",
    }));

    expect(screen.getByRole("button", {
      name: "Sending...",
    })).toBeDisabled();

    expect(mocks.requestEmailOtp).toHaveBeenCalledTimes(1);

    resolveRequest({ success: true, error: null });

    expect(await screen.findByRole("status")).toBeInTheDocument();
  });
  it("verifies the requested email code and reports success", async () => {
    mocks.requestEmailOtp.mockResolvedValue({ success: true, error: null });
    mocks.verifyEmailOtp.mockResolvedValue({ success: true, error: null });
    render(<LoginPage />);
    fireEvent.change(screen.getByLabelText("Email address"), { target: { value: " TEST@EXAMPLE.COM " } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    fireEvent.change(await screen.findByLabelText("Verification code"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Verify code" }));
    await waitFor(() => expect(screen.getByText("Signed in.")).toHaveFocus());
    expect(mocks.verifyEmailOtp).toHaveBeenCalledWith("test@example.com", "123456");
  });

  it("associates rejected code errors with the code field", async () => {
    mocks.requestEmailOtp.mockResolvedValue({ success: true, error: null });
    mocks.verifyEmailOtp.mockResolvedValue({ success: false, error: "Verification failed. Check your code or request a new one." });
    render(<LoginPage />);
    fireEvent.change(screen.getByLabelText("Email address"), { target: { value: "test@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    fireEvent.change(await screen.findByLabelText("Verification code"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Verify code" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Verification failed");
    expect(screen.getByLabelText("Verification code")).toHaveAccessibleDescription("Verification failed. Check your code or request a new one.");
    expect(screen.getByLabelText("Email address")).not.toHaveAttribute("aria-invalid", "true");
    expect(screen.queryByText("Signed in.")).not.toBeInTheDocument();
  });

  it("clears the requested code when the email changes", async () => {
    mocks.requestEmailOtp.mockResolvedValue({ success: true, error: null });
    render(<LoginPage />);
    fireEvent.change(screen.getByLabelText("Email address"), { target: { value: "test@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    fireEvent.change(await screen.findByLabelText("Verification code"), { target: { value: "123456" } });
    fireEvent.change(screen.getByLabelText("Email address"), { target: { value: "other@example.com" } });
    expect(screen.queryByLabelText("Verification code")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(await screen.findByLabelText("Verification code")).toHaveValue("");
    expect(mocks.verifyEmailOtp).not.toHaveBeenCalled();
  });

  it("prevents duplicate verification and email changes while verifying", async () => {
    mocks.requestEmailOtp.mockResolvedValue({ success: true, error: null });
    let finish!: (result: { success: boolean; error: null }) => void;
    mocks.verifyEmailOtp.mockReturnValue(new Promise((resolve) => { finish = resolve; }));
    render(<LoginPage />);
    fireEvent.change(screen.getByLabelText("Email address"), { target: { value: "test@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    fireEvent.change(await screen.findByLabelText("Verification code"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Verify code" }));
    expect(screen.getByLabelText("Email address")).toBeDisabled();
    const button = screen.getByRole("button", { name: "Verifying..." });
    expect(button).toBeDisabled();
    fireEvent.submit(button.closest("form")!);
    expect(mocks.verifyEmailOtp).toHaveBeenCalledTimes(1);
    finish({ success: true, error: null });
    expect(await screen.findByText("Signed in.")).toBeInTheDocument();
  });

  it("returns to email entry only after successful sign-out", async () => {
    mocks.requestEmailOtp.mockResolvedValue({ success: true, error: null });
    mocks.verifyEmailOtp.mockResolvedValue({ success: true, error: null });
    mocks.signOut.mockResolvedValue({ success: true, error: null });
    render(<LoginPage />);
    fireEvent.change(screen.getByLabelText("Email address"), { target: { value: "test@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    fireEvent.change(await screen.findByLabelText("Verification code"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Verify code" }));
    expect(await screen.findByRole("button", { name: "Sign out" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Email address")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Sign out" }));
    expect(await screen.findByLabelText("Email address")).toHaveValue("");
    await waitFor(() => expect(screen.getByLabelText("Email address")).toHaveFocus());
    expect(screen.queryByText("Signed in.")).not.toBeInTheDocument();
  });

  it("does not claim a verified session when sign-out fails", async () => {
    mocks.requestEmailOtp.mockResolvedValue({ success: true, error: null });
    mocks.verifyEmailOtp.mockResolvedValue({ success: true, error: null });
    mocks.signOut.mockResolvedValue({ success: false, error: "Unable to confirm sign-out. Please try again." });
    render(<LoginPage />);
    fireEvent.change(screen.getByLabelText("Email address"), { target: { value: "test@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    fireEvent.change(await screen.findByLabelText("Verification code"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Verify code" }));
    fireEvent.click(await screen.findByRole("button", { name: "Sign out" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Unable to confirm sign-out");
    expect(screen.queryByText("Signed in.")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Check session" })).toBeEnabled();
    expect(screen.queryByLabelText("Email address")).not.toBeInTheDocument();
  });

  it("prevents duplicate sign-out while pending", async () => {
    mocks.requestEmailOtp.mockResolvedValue({ success: true, error: null });
    mocks.verifyEmailOtp.mockResolvedValue({ success: true, error: null });
    let finish!: (value: { success: boolean; error: null }) => void;
    mocks.signOut.mockReturnValue(new Promise((resolve) => { finish = resolve; }));
    render(<LoginPage />);
    fireEvent.change(screen.getByLabelText("Email address"), { target: { value: "test@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    fireEvent.change(await screen.findByLabelText("Verification code"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Verify code" }));
    fireEvent.click(await screen.findByRole("button", { name: "Sign out" }));
    const button = screen.getByRole("button", { name: "Signing out..." });
    expect(button).toBeDisabled();
    fireEvent.click(button);
    expect(mocks.signOut).toHaveBeenCalledTimes(1);
    finish({ success: true, error: null });
    expect(await screen.findByLabelText("Email address")).toBeInTheDocument();
  });

  it("restores the verified view for a provider-confirmed user", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    mocks.getSessionStatus.mockResolvedValue({ state: "signed-in" });
    render(<LoginPage />);
    expect(await screen.findByRole("button", { name: "Sign out" })).toBeInTheDocument();
    expect(screen.getByText("Signed in.")).toBeInTheDocument();
    expect(screen.queryByText("Email verified.")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Email address")).not.toBeInTheDocument();
  });

  it("blocks sign-in while the session status is being checked", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    let finish!: (value: { state: string }) => void;
    mocks.getSessionStatus.mockReturnValue(new Promise((resolve) => { finish = resolve; }));
    render(<LoginPage />);
    expect(screen.queryByLabelText("Email address")).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Checking");
    finish({ state: "signed-out" });
    expect(await screen.findByLabelText("Email address")).toBeInTheDocument();
  });

  it("shows an unavailable state and retries a failed session check", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    mocks.getSessionStatus.mockResolvedValueOnce({ state: "unavailable" }).mockResolvedValueOnce({ state: "signed-out" });
    render(<LoginPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Unable to check your session");
    expect(screen.queryByLabelText("Email address")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    await waitFor(() => expect(screen.getByLabelText("Email address")).toHaveFocus());
    expect(mocks.getSessionStatus).toHaveBeenCalledTimes(2);
  });

  it("ignores a stale session check after a later auth change", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    let notify!: (event: string) => void;
    mocks.observeSessionChanges.mockImplementation((callback) => { notify = callback; return () => {}; });
    let finish!: (value: { state: string }) => void;
    mocks.getSessionStatus.mockReturnValueOnce(new Promise((resolve) => { finish = resolve; }))
      .mockResolvedValueOnce({ state: "signed-out" });
    render(<LoginPage />);
    expect(screen.getByRole("status")).toHaveTextContent("Checking");
    act(() => notify("SIGNED_OUT"));
    expect(mocks.getSessionStatus).toHaveBeenCalledTimes(1);
    expect(await screen.findByLabelText("Email address")).toBeInTheDocument();
    await act(async () => { finish({ state: "signed-in" }); });
    expect(screen.queryByRole("button", { name: "Sign out" })).not.toBeInTheDocument();
  });

  it("does not apply a stale verification result after an auth change", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    let notify!: (event: string) => void;
    mocks.observeSessionChanges.mockImplementation((callback) => { notify = callback; return () => {}; });
    mocks.requestEmailOtp.mockResolvedValue({ success: true, error: null });
    let finish!: (value: { success: boolean; error: null }) => void;
    mocks.verifyEmailOtp.mockReturnValue(new Promise((resolve) => { finish = resolve; }));
    render(<LoginPage />);
    fireEvent.change(await screen.findByLabelText("Email address"), { target: { value: "test@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    fireEvent.change(await screen.findByLabelText("Verification code"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Verify code" }));
    act(() => notify("SIGNED_OUT"));
    await act(async () => { finish({ success: true, error: null }); });
    await waitFor(() => expect(mocks.getSessionStatus).toHaveBeenCalledTimes(2));
    expect(await screen.findByLabelText("Email address")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Sign out" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Verification code")).not.toBeInTheDocument();
  });

  it("preserves sign-out uncertainty when an auth event occurs during a failed sign-out", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    let notify!: (event: string) => void;
    mocks.observeSessionChanges.mockImplementation((callback) => { notify = callback; return () => {}; });
    mocks.getSessionStatus.mockResolvedValue({ state: "signed-in" });
    let finish!: (value: { success: boolean; error: string }) => void;
    mocks.signOut.mockReturnValue(new Promise((resolve) => { finish = resolve; }));
    render(<LoginPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Sign out" }));
    act(() => notify("SIGNED_OUT"));
    await act(async () => { finish({ success: false, error: "Unable to confirm sign-out. Please try again." }); });
    expect(await screen.findByRole("alert")).toHaveTextContent("Unable to confirm sign-out");
    expect(screen.queryByText("Signed in.")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Sign out" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Check session" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Email address")).not.toBeInTheDocument();
  });

  it("unsubscribes and ignores a pending session result after unmount", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    const cleanup = vi.fn();
    mocks.observeSessionChanges.mockReturnValue(cleanup);
    let finish!: (value: { state: string }) => void;
    mocks.getSessionStatus.mockReturnValue(new Promise((resolve) => { finish = resolve; }));
    const view = render(<LoginPage />);
    view.unmount();
    expect(cleanup).toHaveBeenCalledOnce();
    await act(async () => { finish({ state: "signed-in" }); });
    expect(screen.queryByText("Signed in.")).not.toBeInTheDocument();
  });

  it("rechecks the provider after an auth event during successful verification", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    let notify!: (event: string) => void;
    mocks.observeSessionChanges.mockImplementation((callback) => { notify = callback; return () => {}; });
    mocks.getSessionStatus.mockResolvedValueOnce({ state: "signed-out" }).mockResolvedValueOnce({ state: "signed-in" });
    mocks.requestEmailOtp.mockResolvedValue({ success: true, error: null });
    let finish!: (value: { success: boolean; error: null }) => void;
    mocks.verifyEmailOtp.mockReturnValue(new Promise((resolve) => { finish = resolve; }));
    render(<LoginPage />);
    fireEvent.change(await screen.findByLabelText("Email address"), { target: { value: "test@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    fireEvent.change(await screen.findByLabelText("Verification code"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Verify code" }));
    act(() => notify("SIGNED_OUT"));
    await act(async () => { finish({ success: true, error: null }); });
    expect(await screen.findByRole("button", { name: "Sign out" })).toBeInTheDocument();
    expect(mocks.getSessionStatus).toHaveBeenCalledTimes(2);
  });

  it("fails closed and retries when the auth subscription cannot start", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    mocks.observeSessionChanges.mockImplementationOnce(() => { throw new Error("private detail"); })
      .mockReturnValue(() => {});
    render(<LoginPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Unable to check your session");
    expect(screen.queryByLabelText("Email address")).not.toBeInTheDocument();
    expect(mocks.getSessionStatus).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByLabelText("Email address")).toBeInTheDocument();
  });

  it("clears the prior email when sign-out emits an event before completing", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    let notify!: (event: string) => void;
    mocks.observeSessionChanges.mockImplementation((callback) => { notify = callback; return () => {}; });
    mocks.getSessionStatus.mockResolvedValue({ state: "signed-out" });
    mocks.requestEmailOtp.mockResolvedValue({ success: true, error: null });
    mocks.verifyEmailOtp.mockResolvedValue({ success: true, error: null });
    let finish!: (value: { success: boolean; error: null }) => void;
    mocks.signOut.mockReturnValue(new Promise((resolve) => { finish = resolve; }));
    render(<LoginPage />);
    fireEvent.change(await screen.findByLabelText("Email address"), { target: { value: "first@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    fireEvent.change(await screen.findByLabelText("Verification code"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Verify code" }));
    fireEvent.click(await screen.findByRole("button", { name: "Sign out" }));
    act(() => notify("SIGNED_OUT"));
    await act(async () => { finish({ success: true, error: null }); });
    expect(await screen.findByLabelText("Email address")).toHaveValue("");
  });

  it("requires a fresh session check after an account change during failed sign-out", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    let notify!: (event: string) => void;
    mocks.observeSessionChanges.mockImplementation((callback) => { notify = callback; return () => {}; });
    mocks.getSessionStatus.mockResolvedValue({ state: "signed-in" });
    let finish!: (value: { success: boolean; error: string }) => void;
    mocks.signOut.mockReturnValue(new Promise((resolve) => { finish = resolve; }));
    render(<LoginPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Sign out" }));
    act(() => notify("SIGNED_IN"));
    await act(async () => { finish({ success: false, error: "Unable to confirm sign-out. Please try again." }); });
    expect(await screen.findByRole("button", { name: "Check session" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Sign out" })).not.toBeInTheDocument();
    expect(mocks.signOut).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "Check session" }));
    expect(await screen.findByRole("button", { name: "Sign out" })).toBeInTheDocument();
    expect(screen.getByText("Signed in.")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(mocks.getSessionStatus).toHaveBeenCalledTimes(2);
    expect(mocks.signOut).toHaveBeenCalledTimes(1);
  });

  it("ignores a stale code request after an account change", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    let notify!: (event: string) => void;
    mocks.observeSessionChanges.mockImplementation((callback) => { notify = callback; return () => {}; });
    mocks.getSessionStatus.mockResolvedValueOnce({ state: "signed-out" }).mockResolvedValueOnce({ state: "signed-in" });
    let finish!: (value: { success: boolean; error: null }) => void;
    mocks.requestEmailOtp.mockReturnValue(new Promise((resolve) => { finish = resolve; }));
    render(<LoginPage />);
    fireEvent.change(await screen.findByLabelText("Email address"), { target: { value: "old@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    act(() => notify("SIGNED_IN"));
    await act(async () => { finish({ success: true, error: null }); });
    expect(await screen.findByRole("button", { name: "Sign out" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Verification code")).not.toBeInTheDocument();
  });

  it("preserves email entry across a token refresh notification", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    let notify!: (event: string) => void;
    mocks.observeSessionChanges.mockImplementation((callback) => { notify = callback; return () => {}; });
    mocks.getSessionStatus.mockResolvedValue({ state: "signed-out" });
    render(<LoginPage />);
    fireEvent.change(await screen.findByLabelText("Email address"), { target: { value: "test@example.com" } });
    act(() => notify("TOKEN_REFRESHED"));
    await waitFor(() => expect(mocks.getSessionStatus).toHaveBeenCalledTimes(2));
    expect(await screen.findByLabelText("Email address")).toHaveValue("test@example.com");
  });

  it("rechecks a signed-in session when the user returns to the tab", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    mocks.getSessionStatus.mockResolvedValueOnce({ state: "signed-in" }).mockResolvedValueOnce({ state: "signed-out" });
    render(<LoginPage />);
    expect(await screen.findByRole("button", { name: "Sign out" })).toBeInTheDocument();
    act(() => { window.dispatchEvent(new Event("focus")); });
    expect(await screen.findByLabelText("Email address")).toHaveValue("");
    expect(screen.queryByRole("button", { name: "Sign out" })).not.toBeInTheDocument();
    expect(mocks.getSessionStatus).toHaveBeenCalledTimes(2);
  });

  it("does not recheck a session on focus when live authentication is disabled", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "false");
    render(<LoginPage />);
    act(() => { window.dispatchEvent(new Event("focus")); });
    expect(screen.getByLabelText("Email address")).toBeInTheDocument();
    expect(mocks.getSessionStatus).not.toHaveBeenCalled();
  });

  it("preserves a code being entered when the user returns from email", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    mocks.getSessionStatus.mockResolvedValue({ state: "signed-out" });
    mocks.requestEmailOtp.mockResolvedValue({ success: true, error: null });
    render(<LoginPage />);
    fireEvent.change(await screen.findByLabelText("Email address"), { target: { value: "test@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    const code = await screen.findByLabelText("Verification code");
    fireEvent.change(code, { target: { value: "123" } });
    act(() => { window.dispatchEvent(new Event("focus")); });
    await waitFor(() => expect(mocks.getSessionStatus).toHaveBeenCalledTimes(2));
    expect(await screen.findByLabelText("Verification code")).toHaveValue("123");
    expect(mocks.requestEmailOtp).toHaveBeenCalledTimes(1);
  });

  it("preserves an in-flight code request when the user returns to the tab", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    mocks.getSessionStatus.mockResolvedValue({ state: "signed-out" });
    let finish!: (result: { success: boolean; error: null }) => void;
    mocks.requestEmailOtp.mockReturnValue(new Promise((resolve) => { finish = resolve; }));
    render(<LoginPage />);
    fireEvent.change(await screen.findByLabelText("Email address"), { target: { value: "test@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    act(() => { window.dispatchEvent(new Event("focus")); });
    await act(async () => { finish({ success: true, error: null }); });
    await waitFor(() => expect(mocks.getSessionStatus).toHaveBeenCalledTimes(2));
    await screen.findByLabelText("Verification code");
    await waitFor(() => expect(screen.getByLabelText("Verification code")).toHaveFocus());
    expect(mocks.requestEmailOtp).toHaveBeenCalledTimes(1);
  });

  it("clears a pending code when resume revalidation finds a signed-in session", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    mocks.getSessionStatus.mockResolvedValueOnce({ state: "signed-out" }).mockResolvedValueOnce({ state: "signed-in" });
    mocks.requestEmailOtp.mockResolvedValue({ success: true, error: null });
    render(<LoginPage />);
    fireEvent.change(await screen.findByLabelText("Email address"), { target: { value: "test@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    fireEvent.change(await screen.findByLabelText("Verification code"), { target: { value: "123" } });
    act(() => { window.dispatchEvent(new Event("focus")); });
    expect(await screen.findByRole("button", { name: "Sign out" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Verification code")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Email address")).not.toBeInTheDocument();
  });

  it("keeps sign-out uncertain when focus occurs before a failed sign-out", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    mocks.getSessionStatus.mockResolvedValue({ state: "signed-in" });
    let finish!: (value: { success: boolean; error: string }) => void;
    mocks.signOut.mockReturnValue(new Promise((resolve) => { finish = resolve; }));
    render(<LoginPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Sign out" }));
    act(() => { window.dispatchEvent(new Event("focus")); });
    await act(async () => { finish({ success: false, error: "Unable to confirm sign-out. Please try again." }); });
    expect(await screen.findByRole("button", { name: "Check session" })).toBeInTheDocument();
    expect(screen.queryByText("Signed in.")).not.toBeInTheDocument();
    expect(mocks.getSessionStatus).toHaveBeenCalledTimes(1);
  });

  it("blocks an entered code on resume errors and restores it after retry", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    mocks.getSessionStatus.mockResolvedValueOnce({ state: "signed-out" }).mockResolvedValueOnce({ state: "unavailable" }).mockResolvedValueOnce({ state: "signed-out" });
    mocks.requestEmailOtp.mockResolvedValue({ success: true, error: null });
    render(<LoginPage />);
    fireEvent.change(await screen.findByLabelText("Email address"), { target: { value: "test@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    fireEvent.change(await screen.findByLabelText("Verification code"), { target: { value: "123" } });
    act(() => { window.dispatchEvent(new Event("focus")); });
    expect(await screen.findByRole("alert")).toHaveTextContent("Unable to check your session");
    expect(screen.queryByLabelText("Verification code")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByLabelText("Verification code")).toHaveValue("123");
  });

  it("ignores an old resume result after a newer auth event", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    let notify!: (event: string) => void;
    mocks.observeSessionChanges.mockImplementation((callback) => { notify = callback; return () => {}; });
    let finish!: (value: { state: string }) => void;
    mocks.getSessionStatus.mockResolvedValueOnce({ state: "signed-out" })
      .mockReturnValueOnce(new Promise((resolve) => { finish = resolve; }))
      .mockResolvedValueOnce({ state: "signed-in" });
    render(<LoginPage />);
    expect(await screen.findByLabelText("Email address")).toBeInTheDocument();
    act(() => { window.dispatchEvent(new Event("focus")); });
    await waitFor(() => expect(mocks.getSessionStatus).toHaveBeenCalledTimes(2));
    act(() => notify("SIGNED_IN"));
    expect(await screen.findByRole("button", { name: "Sign out" })).toBeInTheDocument();
    await act(async () => { finish({ state: "signed-out" }); });
    expect(screen.getByRole("button", { name: "Sign out" })).toBeInTheDocument();
  });

  it("rechecks after a verification completes while the tab is returning", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    mocks.getSessionStatus.mockResolvedValueOnce({ state: "signed-out" }).mockResolvedValueOnce({ state: "signed-in" });
    mocks.requestEmailOtp.mockResolvedValue({ success: true, error: null });
    let finish!: (value: { success: boolean; error: null }) => void;
    mocks.verifyEmailOtp.mockReturnValue(new Promise((resolve) => { finish = resolve; }));
    render(<LoginPage />);
    fireEvent.change(await screen.findByLabelText("Email address"), { target: { value: "test@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    fireEvent.change(await screen.findByLabelText("Verification code"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Verify code" }));
    act(() => { window.dispatchEvent(new Event("focus")); });
    await act(async () => { finish({ success: true, error: null }); });
    await waitFor(() => expect(mocks.getSessionStatus).toHaveBeenCalledTimes(2));
    expect(await screen.findByRole("button", { name: "Sign out" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Verification code")).not.toBeInTheDocument();
  });

  it("coalesces focus and visibility rechecks before they start", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    mocks.getSessionStatus.mockResolvedValue({ state: "signed-out" });
    render(<LoginPage />);
    expect(await screen.findByLabelText("Email address")).toBeInTheDocument();
    act(() => {
      window.dispatchEvent(new Event("focus"));
      document.dispatchEvent(new Event("visibilitychange"));
    });
    await waitFor(() => expect(mocks.getSessionStatus).toHaveBeenCalledTimes(2));
    expect(await screen.findByLabelText("Email address")).toBeInTheDocument();
  });

  it("ignores an in-flight session result when the user returns during the check", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    let finish!: (value: { state: string }) => void;
    mocks.getSessionStatus.mockReturnValueOnce(new Promise((resolve) => { finish = resolve; }))
      .mockResolvedValueOnce({ state: "signed-out" });
    render(<LoginPage />);
    expect(screen.getByRole("status")).toHaveTextContent("Checking");
    act(() => { window.dispatchEvent(new Event("focus")); });
    await act(async () => { finish({ state: "signed-in" }); });
    expect(await screen.findByLabelText("Email address")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Sign out" })).not.toBeInTheDocument();
    expect(mocks.getSessionStatus).toHaveBeenCalledTimes(2);
  });

});
