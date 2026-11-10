import { beforeEach, expect, it, vi } from "vitest";
import {
  fireEvent,
  render,
  screen,
  waitFor,
  act,
} from "@testing-library/react";
const m = vi.hoisted(() => ({
  session: vi.fn(),
  academies: vi.fn(),
  roster: vi.fn(),
  issue: vi.fn(),
  preview: vi.fn(),
  children: vi.fn(),
  accept: vi.fn(),
  connections: vi.fn(),
  change: null as null | (() => void),
}));
vi.mock("@/lib/families/actions", () => ({
  familySession: m.session,
  familyAcademies: m.academies,
  familyRoster: m.roster,
  issueFamilyInvite: m.issue,
  previewFamilyInvite: m.preview,
  familyChildren: m.children,
  acceptFamilyInvite: m.accept,
  childAcademies: m.connections,
}));
vi.mock("@/lib/auth/session-observer", () => ({
  observeSessionChanges: (f: () => void) => {
    m.change = f;
    return () => {};
  },
}));
import StudentsPanel from "./students-panel";
import JoinPanel from "./join-panel";
import ParentConnectionsPanel from "./parent-connections-panel";
const actor = "11111111-1111-4111-8111-111111111111",
  id = "22222222-2222-4222-8222-222222222222";
beforeEach(() => {
  vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
  vi.clearAllMocks();
  sessionStorage.clear();
  localStorage.clear();
  history.replaceState(null, "", "/");
  m.session.mockResolvedValue({ ok: true, data: actor });
  m.academies.mockResolvedValue({ ok: true, data: [{ id, name: "Academy" }] });
  m.roster.mockResolvedValue({
    ok: true,
    data: [{ id, name: "Fictional Child", status: "active" }],
  });
  m.issue.mockResolvedValue({
    ok: true,
    data: { inviteId: id, expiresAt: "2026-11-24T12:00:00Z" },
  });
  m.preview.mockResolvedValue({
    ok: true,
    data: {
      academyName: "Academy",
      expiresAt: "2026-11-24T12:00:00Z",
      state: "pending",
    },
  });
  m.children.mockResolvedValue({
    ok: true,
    data: [{ id, name: "Fictional Child" }],
  });
  m.accept.mockResolvedValue({ ok: true, data: id });
});
it("loads saved students only after explicit academy selection", async () => {
  render(<StudentsPanel />);
  fireEvent.click(
    await screen.findByRole("button", { name: "Load academies" }),
  );
  await screen.findByRole("option", { name: "Academy" });
  fireEvent.change(screen.getByLabelText("Academy"), { target: { value: id } });
  fireEvent.click(screen.getByRole("button", { name: "Load students" }));
  expect(await screen.findByText("Fictional Child")).toBeVisible();
  expect(m.roster).toHaveBeenCalledWith(actor, id, null);
});
it("keeps invite request/token stable after uncertain response and double click", async () => {
  m.issue.mockRejectedValueOnce(
    new Error("synthetic server-action interruption"),
  );
  render(<StudentsPanel />);
  fireEvent.click(
    await screen.findByRole("button", { name: "Load academies" }),
  );
  await screen.findByRole("option", { name: "Academy" });
  fireEvent.change(screen.getByLabelText("Academy"), { target: { value: id } });
  fireEvent.click(screen.getByRole("button", { name: "Add a student" }));
  await screen.findByRole("alert");
  fireEvent.click(screen.getByRole("button", { name: "Retry invitation" }));
  await screen.findByLabelText("Family invite link");
  expect(m.issue.mock.calls[0]).toEqual(m.issue.mock.calls[1]);
  expect(localStorage.length).toBe(0);
});
it("hides roster and ignores a response arriving after account change", async () => {
  let done!: (v: unknown) => void;
  m.roster.mockImplementation(
    () =>
      new Promise((r) => {
        done = r;
      }),
  );
  render(<StudentsPanel />);
  fireEvent.click(
    await screen.findByRole("button", { name: "Load academies" }),
  );
  await screen.findByRole("option", { name: "Academy" });
  fireEvent.change(screen.getByLabelText("Academy"), { target: { value: id } });
  fireEvent.click(screen.getByRole("button", { name: "Load students" }));
  await waitFor(() => expect(m.roster).toHaveBeenCalled());
  act(() => m.change?.());
  await act(async () =>
    done({ ok: true, data: [{ id, name: "Private Child", status: "active" }] }),
  );
  expect(screen.queryByText("Private Child")).not.toBeInTheDocument();
});
it("strips the fragment and requires explicit parent confirmation", async () => {
  history.replaceState(null, "", "/join#" + "ab".repeat(32));
  render(<JoinPanel />);
  await waitFor(() => expect(location.hash).toBe(""));
  fireEvent.click(
    await screen.findByRole("button", { name: "Check invitation" }),
  );
  await screen.findByText("Academy");
  fireEvent.change(screen.getByLabelText("Your child"), {
    target: { value: id },
  });
  const confirm = screen.getByRole("button", {
    name: "Confirm academy connection",
  });
  expect(confirm).toBeDisabled();
  fireEvent.click(screen.getByLabelText(/I confirm this is my child/));
  fireEvent.click(confirm);
  expect(
    await screen.findByText(
      "Connection saved. Batch enrolment is a separate step.",
    ),
  ).toBeVisible();
  expect(m.accept).toHaveBeenCalledWith(actor, "ab".repeat(32), id);
});
it("offers the new feature in Hindi", async () => {
  render(<StudentsPanel />);
  fireEvent.change(screen.getByLabelText("Language / भाषा"), {
    target: { value: "hi" },
  });
  expect(
    screen.getByRole("button", { name: "अकादमियाँ लोड करें" }),
  ).toBeVisible();
});
it("blocks a real double click while invite issuance is unresolved", async () => {
  let finish!: (v: unknown) => void;
  m.issue.mockImplementation(
    () =>
      new Promise((r) => {
        finish = r;
      }),
  );
  render(<StudentsPanel />);
  fireEvent.click(
    await screen.findByRole("button", { name: "Load academies" }),
  );
  await screen.findByRole("option", { name: "Academy" });
  fireEvent.change(screen.getByLabelText("Academy"), { target: { value: id } });
  const add = screen.getByRole("button", { name: "Add a student" });
  fireEvent.click(add);
  fireEvent.click(add);
  expect(m.issue).toHaveBeenCalledTimes(1);
  await act(async () => finish({ ok: false }));
});
it("retains the selected child for an uncertain acceptance retry", async () => {
  m.children.mockResolvedValue({
    ok: true,
    data: [
      { id, name: "First Child" },
      { id: actor, name: "Second Child" },
    ],
  });
  m.accept.mockResolvedValueOnce({ ok: false });
  history.replaceState(null, "", "/join#" + "ab".repeat(32));
  render(<JoinPanel />);
  fireEvent.click(
    await screen.findByRole("button", { name: "Check invitation" }),
  );
  await screen.findByText("Academy");
  fireEvent.change(screen.getByLabelText("Your child"), {
    target: { value: id },
  });
  fireEvent.click(screen.getByLabelText(/I confirm this is my child/));
  fireEvent.click(
    screen.getByRole("button", { name: "Confirm academy connection" }),
  );
  await screen.findByText(/Connection result is unconfirmed/);
  expect(screen.getByLabelText("Your child")).toBeDisabled();
  expect(screen.getByLabelText("Your child")).toHaveValue(id);
  fireEvent.click(
    screen.getByRole("button", { name: "Confirm academy connection" }),
  );
  await screen.findByText(
    "Connection saved. Batch enrolment is a separate step.",
  );
  expect(m.accept.mock.calls[0]).toEqual(m.accept.mock.calls[1]);
});
it("ignores invitation details arriving after a session change", async () => {
  let finish!: (v: unknown) => void;
  m.preview.mockImplementation(
    () =>
      new Promise((r) => {
        finish = r;
      }),
  );
  history.replaceState(null, "", "/join#" + "ab".repeat(32));
  render(<JoinPanel />);
  fireEvent.click(
    await screen.findByRole("button", { name: "Check invitation" }),
  );
  await waitFor(() => expect(m.preview).toHaveBeenCalled());
  act(() => m.change?.());
  await act(async () =>
    finish({
      ok: true,
      data: {
        academyName: "Private Academy",
        expiresAt: "2026-11-24T12:00:00Z",
        state: "pending",
      },
    }),
  );
  expect(screen.queryByText("Private Academy")).not.toBeInTheDocument();
});

it("ignores parent connection profiles arriving after focus invalidation", async () => {
  let finish!: (v: unknown) => void;
  m.children.mockImplementation(
    () =>
      new Promise((r) => {
        finish = r;
      }),
  );
  render(<ParentConnectionsPanel />);
  fireEvent.click(
    await screen.findByRole("button", { name: "Load your child profiles" }),
  );
  await waitFor(() => expect(m.children).toHaveBeenCalled());
  fireEvent(window, new Event("focus"));
  await act(async () =>
    finish({ ok: true, data: [{ id, name: "Private Child" }] }),
  );
  expect(screen.queryByText("Private Child")).not.toBeInTheDocument();
});
