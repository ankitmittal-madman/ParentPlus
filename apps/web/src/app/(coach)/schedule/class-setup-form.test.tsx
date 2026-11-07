import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ClassSetupForm from "./class-setup-form";

const mocks = vi.hoisted(() => ({ run: vi.fn() }));
vi.mock("@/lib/scheduling/class-setup-operations", () => ({ runClassSetupOperation: mocks.run }));

const actor = "b0000000-0000-4000-8000-000000000001";
const workspace = "a0000000-0000-4000-8000-000000000001";
const intent = "e0000000-0000-4000-8000-000000000001";
const request = "e0000000-0000-4000-8000-000000000002";
const course = "c0000000-0000-4000-8000-000000000001";
const batch = "d0000000-0000-4000-8000-000000000001";
const schedule = { timeZone: "Asia/Kolkata", startDate: "2026-11-09", startTime: "17:30", endDate: "2026-11-23", durationMinutes: 60 };
const completion = { ok: true, operation: "complete", courseId: course, batchId: batch, ...schedule, occurrenceCount: 3 };

function fillSchedule() {
  fireEvent.change(screen.getByLabelText("First session date"), { target: { value: schedule.startDate } });
  fireEvent.change(screen.getByLabelText("Local start time"), { target: { value: schedule.startTime } });
  fireEvent.change(screen.getByLabelText("Last date for weekly sessions"), { target: { value: schedule.endDate } });
}

describe("ClassSetupForm", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.spyOn(crypto, "randomUUID").mockReturnValue(request);
  });
  afterEach(() => vi.restoreAllMocks());

  it("reserves and atomically completes a weekly course and batch schedule", async () => {
    const refresh = vi.fn().mockResolvedValue(undefined);
    mocks.run
      .mockResolvedValueOnce({ ok: true, operation: "generation", generation: 2, available: true })
      .mockResolvedValueOnce({ ok: true, operation: "reserve", intentId: intent, disposition: "created", state: "pending", generation: 2 })
      .mockResolvedValueOnce(completion);
    render(<ClassSetupForm actorId={actor} workspaceId={workspace} timeZone="Asia/Kolkata" recovery={{ ok: true, state: "unknown" }} refresh={refresh} />);
    fireEvent.change(screen.getByLabelText("Course name"), { target: { value: "Art Basics" } });
    fireEvent.change(screen.getByLabelText("Batch name"), { target: { value: "Monday learners" } });
    fillSchedule();
    fireEvent.click(screen.getByRole("button", { name: "Create course, batch and weekly sessions" }));

    await waitFor(() => expect(mocks.run).toHaveBeenCalledTimes(3));
    expect(mocks.run).toHaveBeenNthCalledWith(1, { operation: "generation", workspaceId: workspace, expectedActorId: actor });
    expect(mocks.run).toHaveBeenNthCalledWith(2, {
      operation: "reserve", workspaceId: workspace, expectedActorId: actor, generation: 2,
      requestId: request, courseName: "Art Basics", batchName: "Monday learners",
    });
    expect(mocks.run).toHaveBeenNthCalledWith(3, { operation: "complete", workspaceId: workspace, expectedActorId: actor, intentId: intent, schedule });
    expect(await screen.findByRole("status")).toHaveTextContent("3 weekly sessions");
    expect(screen.getByText("This creates 3 weekly sessions, including the first date and any matching week on the end date.")).toBeInTheDocument();
    expect(refresh).toHaveBeenCalledOnce();
  });

  it("does not begin when another academy setup is still unresolved", async () => {
    const refresh = vi.fn().mockResolvedValue(undefined);
    mocks.run.mockResolvedValue({ ok: true, operation: "generation", generation: 2, available: false });
    render(<ClassSetupForm actorId={actor} workspaceId={workspace} timeZone="Asia/Kolkata" recovery={{ ok: true, state: "unknown" }} refresh={refresh} />);
    fireEvent.change(screen.getByLabelText("Course name"), { target: { value: "Art" } });
    fireEvent.change(screen.getByLabelText("Batch name"), { target: { value: "Monday learners" } });
    fillSchedule();
    fireEvent.click(screen.getByRole("button", { name: "Create course, batch and weekly sessions" }));
    expect(await screen.findByRole("status")).toHaveTextContent("already being resolved");
    expect(mocks.run).toHaveBeenCalledTimes(1);
    expect(refresh).toHaveBeenCalledOnce();
  });

  it("requires an explicit academy time zone when one is not configured", () => {
    render(<ClassSetupForm actorId={actor} workspaceId={workspace} timeZone={null} recovery={{ ok: true, state: "unknown" }} refresh={vi.fn()} />);
    expect(screen.getByLabelText("Academy time zone")).toHaveValue("");
    expect(screen.getByText("Choose the academy’s time zone. It sets the local time for every weekly session.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create course, batch and weekly sessions" })).toBeDisabled();
  });

  it("finishes a recovered pending setup without reserving a second class", async () => {
    const refresh = vi.fn().mockResolvedValue(undefined);
    mocks.run.mockResolvedValue(completion);
    render(<ClassSetupForm actorId={actor} workspaceId={workspace} timeZone="Asia/Kolkata" recovery={{ ok: true, state: "pending", intentId: intent, priorIntentId: null, requestId: null, courseName: "Art", batchName: "Monday learners", schedule: null }} refresh={refresh} />);
    fillSchedule();
    fireEvent.click(screen.getByRole("button", { name: "Finish course, batch and schedule" }));
    await waitFor(() => expect(mocks.run).toHaveBeenCalledWith({ operation: "complete", workspaceId: workspace, expectedActorId: actor, intentId: intent, schedule }));
    expect(mocks.run).toHaveBeenCalledTimes(1);
    expect(refresh).toHaveBeenCalledOnce();
    expect(screen.queryByLabelText("Course name")).not.toBeInTheDocument();
  });

  it("asks the manager to choose another local time across a clock change", async () => {
    render(<ClassSetupForm actorId={actor} workspaceId={workspace} timeZone="America/New_York" recovery={{ ok: true, state: "unknown" }} refresh={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Course name"), { target: { value: "Art" } });
    fireEvent.change(screen.getByLabelText("Batch name"), { target: { value: "Sunday" } });
    fireEvent.change(screen.getByLabelText("First session date"), { target: { value: "2026-03-08" } });
    fireEvent.change(screen.getByLabelText("Local start time"), { target: { value: "02:30" } });
    fireEvent.change(screen.getByLabelText("Last date for weekly sessions"), { target: { value: "2026-03-08" } });
    fireEvent.click(screen.getByRole("button", { name: "Create course, batch and weekly sessions" }));
    expect(await screen.findByRole("status")).toHaveTextContent("nonexistent local time on 2026-03-08");
    expect(mocks.run).not.toHaveBeenCalled();
  });

  it("requires explicit acknowledgement after the saved weekly schedule is recovered", async () => {
    const refresh = vi.fn().mockResolvedValue(undefined);
    mocks.run.mockResolvedValue({ ok: true, operation: "acknowledge" });
    render(<ClassSetupForm actorId={actor} workspaceId={workspace} timeZone="Asia/Kolkata" recovery={{ ok: true, state: "completed", intentId: intent, priorIntentId: null, requestId: null, courseName: "Art", batchName: "Monday learners", courseId: course, batchId: batch, acknowledged: false, schedule: { ...schedule, occurrenceCount: 3 } }} refresh={refresh} />);
    expect(screen.getByLabelText("Saved weekly schedule")).toHaveTextContent("3 sessions");
    fireEvent.click(screen.getByRole("button", { name: "Confirm course, batch and schedule" }));
    await waitFor(() => expect(mocks.run).toHaveBeenCalledWith({ operation: "acknowledge", workspaceId: workspace, expectedActorId: actor, intentId: intent }));
    expect(refresh).toHaveBeenCalledOnce();
    expect(screen.queryByLabelText("Course name")).not.toBeInTheDocument();
  });
});
