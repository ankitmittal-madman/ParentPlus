import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
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
});
