import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import LoginPage from "./page";

const mocks = vi.hoisted(() => ({
  requestEmailOtp: vi.fn(),
}));

vi.mock("@/lib/auth/request-email-otp", () => ({
  requestEmailOtp: mocks.requestEmailOtp,
}));

describe("LoginPage", () => {
  beforeEach(() => {
    mocks.requestEmailOtp.mockReset();
  });

  it("renders an accessible email form", () => {
    render(<LoginPage />);

    expect(screen.getByRole("heading", {
      name: "Welcome to Parent Plus",
    })).toBeInTheDocument();

    expect(screen.getByRole("textbox", {
      name: "Email address",
    })).toBeInTheDocument();
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
});
