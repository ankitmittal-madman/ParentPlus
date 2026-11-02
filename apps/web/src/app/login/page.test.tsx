import { describe, expect, it } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import LoginPage from "./page";

describe("LoginPage", () => {
  it("renders an accessible email form", () => {
    render(<LoginPage />);

    expect(
      screen.getByRole("heading", { name: "Welcome to Parent Plus" })
    ).toBeInTheDocument();

    expect(
      screen.getByRole("textbox", { name: "Email address" })
    ).toBeInTheDocument();

    expect(
      screen.getByRole("button", { name: "Continue" })
    ).toBeInTheDocument();
  });

  it("rejects invalid email input", () => {
    render(<LoginPage />);

    fireEvent.change(
      screen.getByRole("textbox", { name: "Email address" }),
      { target: { value: "invalid-email" } }
    );

    fireEvent.click(screen.getByRole("button", { name: "Continue" }));

    expect(
      screen.getByRole("alert")
    ).toHaveTextContent("Enter a valid email address.");
  });

  it("accepts a valid email without sending an OTP", () => {
    render(<LoginPage />);

    fireEvent.change(
      screen.getByRole("textbox", { name: "Email address" }),
      { target: { value: " TEST@EXAMPLE.COM " } }
    );

    fireEvent.click(screen.getByRole("button", { name: "Continue" }));

    expect(
      screen.getByRole("status")
    ).toHaveTextContent("Email accepted.");

    expect(
      screen.getByRole("textbox", { name: "Email address" })
    ).toHaveValue("test@example.com");
  });
});
