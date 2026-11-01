import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { DashboardStats } from "./dashboard-stats";

describe("DashboardStats", () => {
  it("renders all three summary cards", () => {
    render(<DashboardStats />);

    expect(screen.getByText("Fees collected")).toBeInTheDocument();
    expect(screen.getByText("Attendance")).toBeInTheDocument();
    expect(screen.getByText("Parents engaged")).toBeInTheDocument();
  });

  it("renders the expected demonstration values", () => {
    render(<DashboardStats />);

    expect(screen.getByText("72%")).toBeInTheDocument();
    expect(screen.getByText("91%")).toBeInTheDocument();
    expect(screen.getByText("86%")).toBeInTheDocument();
  });
});
