import { beforeEach, expect, it, vi } from "vitest";
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
const m = vi.hoisted(() => ({
  session: vi.fn(),
  academies: vi.fn(),
  children: vi.fn(),
  batches: vi.fn(),
  candidates: vi.fn(),
  roster: vi.fn(),
  save: vi.fn(),
  change: vi.fn(),
  parent: vi.fn(),
  boundary: null as null | (() => void),
}));
vi.mock("@/lib/families/actions", () => ({
  familySession: m.session,
  familyAcademies: m.academies,
  familyChildren: m.children,
}));
vi.mock("@/lib/enrollments/actions", () => ({
  listEnrollmentBatches: m.batches,
  listEnrollmentCandidates: m.candidates,
  listBatchEnrollments: m.roster,
  saveEnrollment: m.save,
  changeEnrollment: m.change,
  listParentEnrollments: m.parent,
}));
vi.mock("@/lib/auth/session-observer", () => ({
  observeSessionChanges: (f: () => void) => {
    m.boundary = f;
    return () => {};
  },
}));
import EnrollmentPanel from "./enrollment-panel";
import ParentClassesPanel from "./parent-classes-panel";
const actor = "11111111-1111-4111-8111-111111111111",
  workspace = "22222222-2222-4222-8222-222222222222",
  batch = "33333333-3333-4333-8333-333333333333",
  child = "44444444-4444-4444-8444-444444444444",
  enrollment = "55555555-5555-4555-8555-555555555555";
const row = {
  id: enrollment,
  childId: child,
  childName: "Asha",
  status: "active",
  version: 1,
};
beforeEach(() => {
  vi.resetAllMocks();
  vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
  localStorage.clear();
  m.session.mockResolvedValue({ ok: true, data: actor });
  m.academies.mockResolvedValue({
    ok: true,
    data: [{ id: workspace, name: "Sunrise Academy" }],
  });
  m.children.mockResolvedValue({
    ok: true,
    data: [{ id: child, name: "Asha" }],
  });
  m.batches.mockResolvedValue({
    ok: true,
    data: [{ id: batch, name: "Morning", courseName: "Maths" }],
  });
  m.candidates.mockResolvedValue({
    ok: true,
    data: [{ id: child, name: "Asha" }],
  });
  m.roster.mockResolvedValue({ ok: true, data: [row] });
  m.save.mockResolvedValue({
    ok: true,
    data: { id: enrollment, status: "active", version: 1 },
  });
  m.change.mockResolvedValue({
    ok: true,
    data: { id: enrollment, status: "paused", version: 2 },
  });
  m.parent.mockResolvedValue({
    ok: true,
    data: [
      {
        id: enrollment,
        academyName: "Sunrise Academy",
        batchName: "Morning",
        courseName: "Maths",
        status: "active",
        version: 1,
      },
    ],
  });
});
it("automatically loads scoped academy batch chips and saved student cards without creating an enrolment", async () => {
  render(<EnrollmentPanel />);
  expect(
    await screen.findByRole("button", { name: "Morning" }),
  ).toHaveAttribute("aria-pressed", "true");
  expect(await screen.findByText("Asha", { selector: "h3" })).toBeVisible();
  expect(screen.getByLabelText("Academy for enrolment")).toHaveValue(workspace);
  expect(m.roster).toHaveBeenCalledWith(actor, workspace, batch, null);
  expect(m.save).not.toHaveBeenCalled();
});
it("explicitly enrols the selected connected child then refreshes real roster instead of applying receipt state", async () => {
  m.roster.mockResolvedValueOnce({ ok: true, data: [] }).mockResolvedValue({
    ok: true,
    data: [{ ...row, status: "paused", version: 2 }],
  });
  render(<EnrollmentPanel />);
  await screen.findByRole("button", { name: "Morning" });
  fireEvent.change(screen.getByLabelText("Connected child"), {
    target: { value: child },
  });
  fireEvent.click(screen.getByRole("button", { name: "Enrol child" }));
  expect(await screen.findByText("Paused")).toBeVisible();
  expect(m.save).toHaveBeenCalledWith(actor, {
    workspaceId: workspace,
    batchId: batch,
    childId: child,
    requestId: expect.any(String),
  });
});
it("freezes uncertain mutation payload UUID actor and version through retry and blocks double clicks", async () => {
  m.change.mockRejectedValueOnce(Error("network interruption"));
  m.roster.mockResolvedValueOnce({ ok: true, data: [row] }).mockResolvedValue({
    ok: true,
    data: [{ ...row, status: "withdrawn", version: 3 }],
  });
  render(<EnrollmentPanel />);
  await screen.findByText("Asha", { selector: "h3" });
  const card = screen.getByRole("article");
  fireEvent.change(within(card).getByLabelText("Reason"), {
    target: { value: "schedule_change" },
  });
  const pause = screen.getByRole("button", { name: "Pause enrolment" });
  fireEvent.click(pause);
  fireEvent.click(pause);
  await screen.findByRole("button", { name: "Check enrolment status" });
  expect(screen.getByLabelText("Connected child")).toBeDisabled();
  fireEvent.click(
    screen.getByRole("button", { name: "Check enrolment status" }),
  );
  expect(await screen.findByText("Withdrawn")).toBeVisible();
  expect(m.change).toHaveBeenCalledTimes(2);
  expect(m.change.mock.calls[1]).toEqual(m.change.mock.calls[0]);
  expect(m.change.mock.calls[0][1]).toMatchObject({
    enrollmentId: enrollment,
    status: "paused",
    expectedVersion: 1,
    reason: "schedule_change",
  });
});
it("requires a reason for pause and withdrawal and offers resume and complete only for live states", async () => {
  render(<EnrollmentPanel />);
  await screen.findByText("Asha", { selector: "h3" });
  expect(
    screen.getByRole("button", { name: "Pause enrolment" }),
  ).toBeDisabled();
  expect(
    screen.getByRole("button", { name: "Withdraw enrolment" }),
  ).toBeDisabled();
  expect(
    screen.getByRole("button", { name: "Complete enrolment" }),
  ).toBeEnabled();
  expect(
    screen.queryByRole("button", { name: "Resume enrolment" }),
  ).not.toBeInTheDocument();
});
it("keeps an uncertain operation for the original account across session invalidation", async () => {
  m.change.mockResolvedValueOnce({ ok: false });
  render(<EnrollmentPanel />);
  await screen.findByText("Asha", { selector: "h3" });
  fireEvent.click(screen.getByRole("button", { name: "Complete enrolment" }));
  await screen.findByRole("button", { name: "Check enrolment status" });
  m.session.mockResolvedValue({ ok: true, data: child });
  m.roster.mockResolvedValue({ ok: true, data: [] });
  act(() => m.boundary?.());
  await screen.findByText(/Sign in with the original account/);
  expect(
    screen.queryByText("Asha", { selector: "h3" }),
  ).not.toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Check enrolment status" }),
  ).toBeDisabled();
  expect(m.change).toHaveBeenCalledTimes(1);
  m.session.mockResolvedValue({ ok: true, data: actor });
  act(() => m.boundary?.());
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Check enrolment status" }),
    ).toBeEnabled(),
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Check enrolment status" }),
  );
  await waitFor(() => expect(m.change).toHaveBeenCalledTimes(2));
  expect(m.change.mock.calls[1]).toEqual(m.change.mock.calls[0]);
});
it("clears private reads and ignores late responses when focus re-verifies a signed-out session", async () => {
  let finish!: (value: unknown) => void;
  m.roster.mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  render(<EnrollmentPanel />);
  await waitFor(() => expect(m.roster).toHaveBeenCalled());
  m.session.mockResolvedValue({ ok: false });
  act(() => window.dispatchEvent(new Event("focus")));
  await act(async () => finish({ ok: true, data: [row] }));
  expect(
    screen.queryByText("Asha", { selector: "h3" }),
  ).not.toBeInTheDocument();
  expect(await screen.findByRole("alert")).toHaveTextContent(/Unable/);
});
it("shows focused read retry and reachable candidate and roster pagination", async () => {
  m.batches.mockResolvedValueOnce({ ok: false });
  render(<EnrollmentPanel />);
  await screen.findByRole("alert");
  fireEvent.click(screen.getByRole("button", { name: "Refresh enrolments" }));
  await screen.findByText("Asha", { selector: "h3" });
  m.candidates.mockResolvedValue({
    ok: true,
    data: Array.from({ length: 50 }, (_, i) => ({
      id: `child-${i}`,
      name: `Child ${i}`,
    })),
  });
  m.roster.mockResolvedValue({
    ok: true,
    data: Array.from({ length: 50 }, (_, i) => ({
      ...row,
      id: `enrolment-${i}`,
      childName: `Learner ${i}`,
    })),
  });
  fireEvent.click(screen.getByRole("button", { name: "Refresh enrolments" }));
  fireEvent.click(
    await screen.findByRole("button", { name: "More connected children" }),
  );
  await waitFor(() =>
    expect(m.candidates).toHaveBeenLastCalledWith(actor, workspace, "child-49"),
  );
  fireEvent.click(screen.getByRole("button", { name: "Next enrolments" }));
  await waitFor(() =>
    expect(m.roster).toHaveBeenLastCalledWith(
      actor,
      workspace,
      batch,
      "enrolment-49",
    ),
  );
});
it("automatically loads own child saved classes and refreshes on child selection", async () => {
  m.children.mockResolvedValue({
    ok: true,
    data: [
      { id: child, name: "Asha" },
      { id: workspace, name: "Dev" },
    ],
  });
  render(<ParentClassesPanel />);
  expect(await screen.findByText("Sunrise Academy")).toBeVisible();
  expect(screen.getByLabelText("Child for classes")).toHaveValue(child);
  fireEvent.change(screen.getByLabelText("Child for classes"), {
    target: { value: workspace },
  });
  await waitFor(() =>
    expect(m.parent).toHaveBeenLastCalledWith(actor, workspace),
  );
  expect(
    screen.queryByRole("button", { name: "Pause enrolment" }),
  ).not.toBeInTheDocument();
});
it("clears parent classes on session change and ignores a late parent response", async () => {
  let finish!: (value: unknown) => void;
  m.parent.mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  render(<ParentClassesPanel />);
  await waitFor(() => expect(m.parent).toHaveBeenCalled());
  m.session.mockResolvedValue({ ok: false });
  act(() => m.boundary?.());
  await act(async () =>
    finish({
      ok: true,
      data: [
        {
          id: enrollment,
          academyName: "Private Academy",
          batchName: "Morning",
          courseName: "Maths",
          status: "active",
          version: 1,
        },
      ],
    }),
  );
  expect(screen.queryByText("Private Academy")).not.toBeInTheDocument();
});
it("remembers distinct enrolment language without replacing family copy", async () => {
  render(<EnrollmentPanel />);
  await screen.findByRole("button", { name: "Morning" });
  fireEvent.change(
    screen.getByLabelText("Enrolment language / नामांकन की भाषा"),
    { target: { value: "hi" } },
  );
  expect(screen.getByRole("heading", { name: "बैच नामांकन" })).toBeVisible();
  expect(localStorage.getItem("parentplus:enrollment-language")).toBe("hi");
});
it("allows a pending request to recheck identity after a failed session without changing its payload", async () => {
  m.change.mockResolvedValueOnce({ ok: false });
  render(<EnrollmentPanel />);
  await screen.findByText("Asha", { selector: "h3" });
  fireEvent.click(screen.getByRole("button", { name: "Complete enrolment" }));
  await screen.findByRole("button", { name: "Check enrolment status" });
  m.session.mockResolvedValue({ ok: false });
  act(() => m.boundary?.());
  await screen.findByRole("alert");
  m.session.mockResolvedValue({ ok: true, data: actor });
  expect(
    screen.getByRole("button", { name: "Check enrolment status" }),
  ).toBeEnabled();
  fireEvent.click(
    screen.getByRole("button", { name: "Check enrolment status" }),
  );
  await waitFor(() => expect(m.change).toHaveBeenCalledTimes(2));
  expect(m.change.mock.calls[1]).toEqual(m.change.mock.calls[0]);
});
it("retries only the current roster after a confirmed operation whose refresh failed", async () => {
  m.roster
    .mockResolvedValueOnce({ ok: true, data: [row] })
    .mockResolvedValueOnce({ ok: false })
    .mockResolvedValue({
      ok: true,
      data: [{ ...row, status: "completed", version: 2 }],
    });
  render(<EnrollmentPanel />);
  await screen.findByText("Asha", { selector: "h3" });
  fireEvent.click(screen.getByRole("button", { name: "Complete enrolment" }));
  await screen.findByRole("alert");
  fireEvent.click(
    screen.getByRole("button", { name: "Check enrolment status" }),
  );
  expect(await screen.findByText("Completed")).toBeVisible();
  expect(m.change).toHaveBeenCalledTimes(1);
  expect(
    screen.queryByRole("button", { name: "Complete enrolment" }),
  ).not.toBeInTheDocument();
});
it("uses a fresh verified account before a write and does not replay into another account", async () => {
  render(<EnrollmentPanel />);
  await screen.findByText("Asha", { selector: "h3" });
  m.session.mockResolvedValue({ ok: true, data: child });
  fireEvent.click(screen.getByRole("button", { name: "Complete enrolment" }));
  expect(
    await screen.findByText(/Sign in with the original account/),
  ).toBeVisible();
  expect(m.change).not.toHaveBeenCalled();
  expect(
    screen.queryByText("Asha", { selector: "h3" }),
  ).not.toBeInTheDocument();
});
it("retains an uncertain save across focus with the original connected child and request UUID", async () => {
  m.save.mockResolvedValueOnce({ ok: false });
  render(<EnrollmentPanel />);
  await screen.findByRole("button", { name: "Morning" });
  fireEvent.change(screen.getByLabelText("Connected child"), {
    target: { value: child },
  });
  fireEvent.click(screen.getByRole("button", { name: "Enrol child" }));
  await screen.findByRole("alert");
  act(() => window.dispatchEvent(new Event("focus")));
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Check enrolment status" }),
    ).toBeEnabled(),
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Check enrolment status" }),
  );
  await waitFor(() => expect(m.save).toHaveBeenCalledTimes(2));
  expect(m.save.mock.calls[1]).toEqual(m.save.mock.calls[0]);
});
it("resumes paused enrolments with null reason and no action can reopen terminal states", async () => {
  m.roster
    .mockResolvedValueOnce({
      ok: true,
      data: [{ ...row, status: "paused", version: 4 }],
    })
    .mockResolvedValue({
      ok: true,
      data: [{ ...row, status: "active", version: 5 }],
    });
  render(<EnrollmentPanel />);
  await screen.findByText("Paused");
  fireEvent.click(screen.getByRole("button", { name: "Resume enrolment" }));
  expect(await screen.findByText("Active")).toBeVisible();
  expect(m.change.mock.calls[0][1]).toMatchObject({
    status: "active",
    expectedVersion: 4,
    reason: null,
  });
});
it("shows honest empty classes and recovers from a parent read error with refresh", async () => {
  m.parent
    .mockResolvedValueOnce({ ok: false })
    .mockResolvedValue({ ok: true, data: [] });
  render(<ParentClassesPanel />);
  await screen.findByRole("alert");
  fireEvent.click(screen.getByRole("button", { name: "Refresh classes" }));
  expect(
    await screen.findByText("No saved classes for this child."),
  ).toBeVisible();
});
it("does not load private data when session monitoring cannot start", async () => {
  vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "false");
  render(<EnrollmentPanel />);
  expect(
    screen.getByRole("button", { name: "Refresh enrolments" }),
  ).toBeDisabled();
  await act(async () => {});
  expect(m.session).not.toHaveBeenCalled();
  expect(m.roster).not.toHaveBeenCalled();
});
it("rechecks the original actor before releasing a definitively rejected operation", async () => {
  m.academies.mockResolvedValue({
    ok: true,
    data: [
      { id: workspace, name: "First Academy" },
      { id: enrollment, name: "Target Academy" },
    ],
  });
  m.batches.mockImplementation(async (_who: string, selected: string) => ({
    ok: true,
    data: [
      {
        id: selected === workspace ? batch : actor,
        name: "Morning",
        courseName: "Maths",
      },
    ],
  }));
  m.change.mockResolvedValueOnce({ ok: false, conflict: true });
  m.session
    .mockResolvedValueOnce({ ok: true, data: actor })
    .mockResolvedValueOnce({ ok: true, data: actor })
    .mockResolvedValueOnce({ ok: true, data: actor })
    .mockResolvedValue({ ok: true, data: child });
  render(<EnrollmentPanel />);
  await screen.findByText("Asha", { selector: "h3" });
  fireEvent.change(screen.getByLabelText("Academy for enrolment"), {
    target: { value: enrollment },
  });
  await waitFor(() =>
    expect(m.roster).toHaveBeenLastCalledWith(actor, enrollment, actor, null),
  );
  fireEvent.click(screen.getByRole("button", { name: "Complete enrolment" }));
  expect(
    await screen.findByText(/Sign in with the original account/),
  ).toBeVisible();
  expect(
    screen.queryByText("Asha", { selector: "h3" }),
  ).not.toBeInTheDocument();
  expect(m.roster).toHaveBeenCalledTimes(2);
  expect(m.change).toHaveBeenCalledTimes(1);
  m.session.mockResolvedValue({ ok: true, data: actor });
  act(() => m.boundary?.());
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Check enrolment status" }),
    ).toBeEnabled(),
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Check enrolment status" }),
  );
  await waitFor(() =>
    expect(
      screen.queryByRole("button", { name: "Check enrolment status" }),
    ).not.toBeInTheDocument(),
  );
  expect(m.change).toHaveBeenCalledTimes(1);
  expect(screen.getByLabelText("Academy for enrolment")).toHaveValue(
    enrollment,
  );
  expect(m.roster).toHaveBeenLastCalledWith(actor, enrollment, actor, null);
});
it("retains rejected intent until roster access recovers and never replays the rejected write", async () => {
  m.change.mockResolvedValueOnce({ ok: false, conflict: true });
  m.roster
    .mockResolvedValueOnce({ ok: true, data: [row] })
    .mockResolvedValueOnce({ ok: false })
    .mockResolvedValue({
      ok: true,
      data: [{ ...row, status: "paused", version: 2 }],
    });
  render(<EnrollmentPanel />);
  await screen.findByText("Asha", { selector: "h3" });
  fireEvent.click(screen.getByRole("button", { name: "Complete enrolment" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(/Unable/);
  fireEvent.click(
    screen.getByRole("button", { name: "Check enrolment status" }),
  );
  expect(await screen.findByText("Paused")).toBeVisible();
  expect(
    screen.getByRole("button", { name: "Refresh enrolments" }),
  ).toBeEnabled();
  expect(m.change).toHaveBeenCalledTimes(1);
});
