import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import SchedulePage from "./page";

vi.mock("./class-recovery-gate", () => ({ default: () => null }));

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

  it("requires both practice names without showing a preview", () => {
    render(<SchedulePage />);
    fireEvent.change(screen.getByLabelText("Course name"), { target: { value: "  " } });
    fireEvent.click(screen.getByRole("button", { name: "Preview class setup" }));
    expect(screen.getByRole("alert")).toHaveTextContent(/enter both/i);
    expect(screen.getByLabelText("Course name")).toHaveAccessibleDescription("Enter both a course name and a batch name.");
    expect(screen.getByLabelText("Batch name")).toHaveAttribute("aria-invalid", "true");
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("shows a clearly unsaved preview of trimmed names", () => {
    render(<SchedulePage />);
    fireEvent.change(screen.getByLabelText("Course name"), { target: { value: " Dance " } });
    fireEvent.change(screen.getByLabelText("Batch name"), { target: { value: " Beginners " } });
    fireEvent.click(screen.getByRole("button", { name: "Preview class setup" }));
    expect(screen.getByRole("status")).toHaveTextContent("Dance");
    expect(screen.getByRole("status")).toHaveTextContent("Beginners");
    expect(screen.getByRole("status")).toHaveTextContent(/not saved/i);
  });

  it("removes an outdated preview when a name changes", () => {
    render(<SchedulePage />);
    fireEvent.change(screen.getByLabelText("Course name"), { target: { value: "Dance" } });
    fireEvent.change(screen.getByLabelText("Batch name"), { target: { value: "Beginners" } });
    fireEvent.click(screen.getByRole("button", { name: "Preview class setup" }));
    expect(screen.getByRole("status")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Batch name"), { target: { value: "Advanced" } });
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });


  it("rejects a practice name beyond the length limit", () => {
    render(<SchedulePage />);
    fireEvent.change(screen.getByLabelText("Course name"), { target: { value: "A".repeat(121) } });
    fireEvent.change(screen.getByLabelText("Batch name"), { target: { value: "Beginners" } });
    fireEvent.click(screen.getByRole("button", { name: "Preview class setup" }));
    expect(screen.getByRole("alert")).toHaveTextContent(/120 characters/i);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });


  it("marks only the missing practice name invalid", () => {
    render(<SchedulePage />);
    fireEvent.change(screen.getByLabelText("Course name"), { target: { value: "Dance" } });
    fireEvent.click(screen.getByRole("button", { name: "Preview class setup" }));
    expect(screen.getByLabelText("Course name")).not.toHaveAttribute("aria-invalid", "true");
    expect(screen.getByLabelText("Batch name")).toHaveAttribute("aria-invalid", "true");
  });

});
