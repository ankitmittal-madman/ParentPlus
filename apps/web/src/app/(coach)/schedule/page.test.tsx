import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import SchedulePage from "./page";

describe("SchedulePage", () => {
  it("identifies the schedule as example data", () => {
    render(<SchedulePage />);
    expect(screen.getByRole("heading", { name: "Schedule" })).toBeInTheDocument();
    expect(screen.getByText(/example data.*not real classes/i)).toBeInTheDocument();
  });

  it("shows example course, batch and session time in a labelled list", () => {
    render(<SchedulePage />);
    const list = screen.getByRole("list", { name: "Example sessions" });
    expect(within(list).getByText("Clay Basics")).toBeInTheDocument();
    expect(within(list).getByText("Clay Juniors")).toBeInTheDocument();
    expect(within(list).getByText("Example Monday, 5:00 PM")).toBeInTheDocument();
  });
});
