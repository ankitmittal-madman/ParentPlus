import { describe, expect, it } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { CoachHeader } from "./coach-header";

describe("CoachHeader", () => {
  it("displays the application and academy names", () => {
    render(<CoachHeader />);

    expect(screen.getByText("Parent Plus Coach")).toBeInTheDocument();
    expect(screen.getByText("The Creative Room")).toBeInTheDocument();
  });

  it("uses a semantic header element", () => {
    render(<CoachHeader />);

    expect(screen.getByRole("banner")).toBeInTheDocument();
  });

  it("opens a menu with links to existing pages", () => {
    render(<CoachHeader />);

    const menu = screen.getByText("Open menu");
    const details = menu.closest("details");
    expect(details).not.toHaveAttribute("open");
    fireEvent.click(menu);
    expect(details).toHaveAttribute("open");
    expect(screen.getByRole("link", { name: "Today" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: "Schedule" })).toHaveAttribute("href", "/schedule");
    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/login");
  });
});
