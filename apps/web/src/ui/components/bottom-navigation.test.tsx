import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { BottomNavigation } from "./bottom-navigation";

const mockPathname = vi.hoisted(() => ({
  current: "/",
}));

vi.mock("next/navigation", () => ({
  usePathname: () => mockPathname.current,
}));

describe("BottomNavigation", () => {
  it("renders all five navigation links", () => {
    mockPathname.current = "/";
    render(<BottomNavigation />);

    const routes = [
      ["Today", "/"],
      ["Schedule", "/schedule"],
      ["Post", "/post"],
      ["Students", "/students"],
      ["Fees", "/fees"],
    ];

    for (const [label, href] of routes) {
      expect(screen.getByRole("link", { name: label })).toHaveAttribute(
        "href",
        href
      );
    }
  });

  it("highlights the current route", () => {
    mockPathname.current = "/schedule";
    render(<BottomNavigation />);

    expect(screen.getByRole("link", { name: "Schedule" })).toHaveAttribute(
      "aria-current",
      "page"
    );

    expect(screen.getByRole("link", { name: "Today" })).not.toHaveAttribute(
      "aria-current"
    );
  });
});
