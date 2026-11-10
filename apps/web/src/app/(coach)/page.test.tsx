import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Home from "./page";

describe("Coach dashboard", () => {
  it("opens real Today without demo records or fake class actions", () => {
    render(<Home />);
    expect(screen.getByRole("heading", { name: "Today" })).toBeVisible();
    expect(screen.queryByText(/Example data|Meera|Clay Juniors|The Creative Room/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Start class|End class|Capture/ })).not.toBeInTheDocument();
  });
});
