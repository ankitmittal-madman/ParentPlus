import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import CoachAccessPage from "./page";

const mocks = vi.hoisted(() => ({ replace: vi.fn(), signOut: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: mocks.replace }) }));
vi.mock("@/lib/auth/sign-out", () => ({ signOut: mocks.signOut }));

describe("coach access recovery", () => {
  afterEach(() => vi.resetAllMocks());

  it("explains what the user needs and signs out to login", async () => {
    mocks.signOut.mockResolvedValue({ success: true, error: null });
    render(<CoachAccessPage />);
    expect(screen.getByRole("heading", { name: "Coach access required" })).toBeVisible();
    expect(screen.getByText(/active coach membership in a workspace/i)).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Sign out" }));
    await waitFor(() => expect(mocks.replace).toHaveBeenCalledWith("/login"));
  });

  it("shows a safe error when sign-out cannot be confirmed", async () => {
    mocks.signOut.mockResolvedValue({ success: false, error: "Unable to confirm sign-out. Please try again." });
    render(<CoachAccessPage />);
    fireEvent.click(screen.getByRole("button", { name: "Sign out" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Unable to confirm sign-out. Please try again.");
    expect(mocks.replace).not.toHaveBeenCalled();
  });
});
