import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Home from "./page";

describe("Coach dashboard", () => {
  it("clearly identifies sample data and does not offer a fake class action", () => {
    render(<Home />);
    expect(screen.getByText(/example data.*not real classes or records/i)).toBeVisible();
    expect(screen.getAllByText("Clay Juniors").length).toBeGreaterThan(0);
    expect(screen.queryByText("Start class")).not.toBeInTheDocument();
    expect(screen.queryByText("›")).not.toBeInTheDocument();
  });
});
