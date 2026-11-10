import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { TodayPanel } from "./today-panel";
import { writePending } from "../attendance/pending";
const m = vi.hoisted(() => ({ session: vi.fn(), observe: vi.fn(), academies: vi.fn(), sessions: vi.fn(), load: vi.fn(), signals: vi.fn(), status: vi.fn(), save: vi.fn(), changed: undefined as undefined | (() => void) }));
vi.mock("@/lib/families/actions", () => ({ familySession: m.session }));
vi.mock("@/lib/auth/session-observer", () => ({ observeSessionChanges: m.observe }));
vi.mock("@/lib/attendance/actions", () => ({ listTodayAcademies: m.academies, listTodaySessions: m.sessions, loadAttendanceSheet: m.load, listSessionSignals: m.signals, attendanceRequestStatus: m.status, saveAttendance: m.save }));
const a = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", b = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", c = "cccccccc-cccc-4ccc-8ccc-cccccccccccc";
const session = { id: b, batchId: a, batchName: "Morning Art", courseName: "Art", startsAt: "2026-11-11T10:00:00Z", endsAt: "2026-11-11T11:00:00Z", status: "scheduled", version: 1, sheetVersion: 0, rosterSize: 3, rosterTooLarge: false, markedCount: 0, attendanceCurrent: false };
beforeEach(() => {
  vi.resetAllMocks();
  vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
  vi.setSystemTime(new Date("2026-11-10T20:30:00Z"));
  sessionStorage.clear();
  localStorage.clear();
  m.session.mockResolvedValue({ ok: true, data: a });
  m.observe.mockImplementation(cb => {
    m.changed = cb;
    return () => {
    };
  });
  m.academies.mockResolvedValue({ ok: true, data: { academies: [{ workspaceId: a, name: "River Academy", timeZone: "Asia/Kolkata" }, { workspaceId: b, name: "North Academy", timeZone: "UTC" }], nextAfter: null } });
  m.sessions.mockImplementation(async (_actor, input) => ({ ok: true, data: { date: input.date, timeZone: input.workspaceId === a ? "Asia/Kolkata" : "UTC", serverNow: "2026-11-10T20:30:00Z", sessions: [session], next: null } }));
  m.load.mockResolvedValue({ ok: false, kind: "forbidden" });
  m.signals.mockResolvedValue({ ok: true, data: { signals: [], next: null, serverNow: "2026-11-10T20:30:00Z" } });
});
it("autoloads coach academies and sessions using academy-local today and actual header", async () => {
  render(<TodayPanel />);
  await screen.findByRole("button", { name: "Open attendance for Morning Art" });
  expect(m.academies).toHaveBeenCalledWith(a, { after: null });
  expect(m.sessions).toHaveBeenCalledWith(a, { workspaceId: a, date: "2026-11-11", after: null });
  expect(screen.getAllByText("River Academy").length).toBeGreaterThan(0);
  expect(screen.getByLabelText("Session date")).toHaveValue("2026-11-11");
  expect(screen.getByText("3 enrolled children")).toBeVisible();
  expect(screen.queryByText(/Meera|Creative Room|Example data/)).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /End class|Capture/ })).not.toBeInTheDocument();
});
it("switches academy and seven-date strip without mutating attendance", async () => {
  render(<TodayPanel />);
  await screen.findByRole("button", { name: "Open attendance for Morning Art" });
  expect(screen.getAllByRole("button", { name: /Select session date/ })).toHaveLength(7);
  fireEvent.change(screen.getByLabelText("Academy"), { target: { value: b } });
  await waitFor(() => expect(m.sessions).toHaveBeenLastCalledWith(a, { workspaceId: b, date: "2026-11-10", after: null }));
  fireEvent.click(screen.getByRole("button", { name: /Select session date.*2026-11-09/ }));
  await waitFor(() => expect(m.sessions).toHaveBeenLastCalledWith(a, { workspaceId: b, date: "2026-11-09", after: null }));
  expect(m.save).not.toHaveBeenCalled();
});
it("loads bounded additional academy and session pages using explicit cursors", async () => {
  m.academies.mockResolvedValueOnce({ ok: true, data: { academies: [{ workspaceId: a, name: "River Academy", timeZone: "UTC" }], nextAfter: a } }).mockResolvedValue({ ok: true, data: { academies: [{ workspaceId: b, name: "North Academy", timeZone: "UTC" }], nextAfter: null } });
  m.sessions.mockResolvedValueOnce({ ok: true, data: { date: "2026-11-10", timeZone: "UTC", serverNow: "2026-11-10T20:30:00Z", sessions: [session], next: { startsAt: session.startsAt, id: b } } }).mockResolvedValue({ ok: true, data: { date: "2026-11-10", timeZone: "UTC", serverNow: "2026-11-10T20:30:00Z", sessions: [{ ...session, id: c, batchName: "Evening Art" }], next: null } });
  render(<TodayPanel />);
  await screen.findByRole("button", { name: "Load more sessions" });
  fireEvent.click(screen.getByRole("button", { name: "Load more academies" }));
  await screen.findByRole("option", { name: "North Academy" });
  expect(m.academies).toHaveBeenLastCalledWith(a, { after: a });
  fireEvent.click(screen.getByRole("button", { name: "Load more sessions" }));
  await screen.findByRole("button", { name: "Open attendance for Evening Art" });
  expect(m.sessions).toHaveBeenLastCalledWith(a, { workspaceId: a, date: "2026-11-10", after: { startsAt: session.startsAt, id: b } });
  expect(screen.getByRole("button", { name: "Open attendance for Morning Art" })).toBeVisible();
});
it("opens the selected real attendance sheet and supports explicit refresh", async () => {
  render(<TodayPanel />);
  fireEvent.click(await screen.findByRole("button", { name: "Open attendance for Morning Art" }));
  await waitFor(() => expect(m.load).toHaveBeenCalledWith(a, { workspaceId: a, sessionId: b }));
  fireEvent.click(screen.getByRole("button", { name: "Refresh Today" }));
  await waitFor(() => expect(m.academies).toHaveBeenCalledTimes(2));
});
it("discards late date promises and immediately clears private data on account change", async () => {
  let resolve!: (v: unknown) => void;
  render(<TodayPanel />);
  await screen.findByRole("button", { name: "Open attendance for Morning Art" });
  m.sessions.mockReturnValueOnce(new Promise(r => {
    resolve = r;
  }));
  fireEvent.change(screen.getByLabelText("Session date"), { target: { value: "2026-11-12" } });
  fireEvent.change(screen.getByLabelText("Session date"), { target: { value: "2026-11-13" } });
  await waitFor(() => expect(m.sessions).toHaveBeenLastCalledWith(a, { workspaceId: a, date: "2026-11-13", after: null }));
  await act(async () => resolve({ ok: true, data: { date: "2026-11-12", timeZone: "UTC", serverNow: "2026-11-10T20:30:00Z", sessions: [{ ...session, batchName: "Old private class" }], next: null } }));
  expect(screen.queryByText("Old private class")).not.toBeInTheDocument();
  m.session.mockResolvedValue({ ok: false });
  act(() => m.changed?.());
  expect(screen.queryByText("Morning Art")).not.toBeInTheDocument();
  expect(screen.queryByText("River Academy")).not.toBeInTheDocument();
});
it("renders honest empty no-assignment and unavailable-zone views", async () => {
  m.sessions.mockResolvedValue({ ok: true, data: { date: "2026-11-11", timeZone: "Asia/Kolkata", serverNow: "2026-11-10T20:30:00Z", sessions: [], next: null } });
  const v = render(<TodayPanel />);
  await screen.findByText("No sessions on this date.");
  v.unmount();
  m.academies.mockResolvedValue({ ok: true, data: { academies: [{ workspaceId: a, name: "Unset Academy", timeZone: null }], nextAfter: null } });
  render(<TodayPanel />);
  await screen.findByText(/time zone is unavailable/);
  expect(screen.getByRole("link", { name: "Set up classes" })).toHaveAttribute("href", "/schedule");
  expect(screen.queryByRole("button", { name: /Open attendance/ })).not.toBeInTheDocument();
});
it("restores an unresolved save on reload even before choosing a current session", async () => {
  writePending({ format: 1, actorId: a, requestId: c, payload: { operation: "save_attendance", workspace_id: a, session_id: b, expected_session_version: 1, expected_sheet_version: 0, roster_token: "a".repeat(64), records: [{ enrollment_id: a, child_id: b, status: "late" }] } });
  render(<TodayPanel />);
  await screen.findByRole("button", { name: "Check saved result" });
  expect(m.load).toHaveBeenCalledWith(a, { workspaceId: a, sessionId: b });
  expect(m.save).not.toHaveBeenCalled();
});
it("switches all Today and attendance copy to Hindi with hydration-safe initial English", async () => {
  render(<TodayPanel />);
  await screen.findByRole("button", { name: "Open attendance for Morning Art" });
  fireEvent.change(screen.getByLabelText("Page language / पृष्ठ की भाषा"), { target: { value: "hi" } });
  expect(screen.getByRole("heading", { name: "आज" })).toBeVisible();
  expect(screen.getByRole("button", { name: "आज की जानकारी रीफ़्रेश करें" })).toBeVisible();
  expect(screen.getByLabelText("सत्र की तारीख")).toHaveValue("2026-11-11");
});
it("shows a persistent success confirmation after an automatically restored save resolves", async () => {
  writePending({ format: 1, actorId: a, requestId: c, payload: { operation: "save_attendance", workspace_id: a, session_id: b, expected_session_version: 1, expected_sheet_version: 0, roster_token: "a".repeat(64), records: [{ enrollment_id: a, child_id: b, status: "late" }] } });
  m.status.mockResolvedValue({ ok: true, data: { state: "known", receipt: { requestId: c, sessionId: b, sheetVersion: 1, sessionVersion: 1, rosterToken: "a".repeat(64), savedAt: "2026-11-10T20:30:00Z", recordCount: 1 } } });
  render(<TodayPanel />);
  fireEvent.click(await screen.findByRole("button", { name: "Check saved result" }));
  await screen.findByText("Attendance saved.");
  expect(screen.queryByRole("button", { name: "Retry same request" })).not.toBeInTheDocument();
});
it("shows no-academy and redacted read failures without example fallback", async () => {
  m.academies.mockResolvedValue({ ok: true, data: { academies: [], nextAfter: null } });
  const v = render(<TodayPanel />);
  await screen.findByText(/No academy available/);
  expect(screen.queryByText("Morning Art")).not.toBeInTheDocument();
  v.unmount();
  m.academies.mockResolvedValue({ ok: false, kind: "unknown" });
  render(<TodayPanel />);
  await screen.findByText(/Unable to load this view/);
  expect(screen.queryByText("River Academy")).not.toBeInTheDocument();
});

function seedRestoredRejection(kind: "conflict" | "forbidden") {
  writePending({ format: 1, actorId: a, requestId: c, payload: { operation: "save_attendance", workspace_id: a, session_id: b, expected_session_version: 1, expected_sheet_version: 0, roster_token: "a".repeat(64), records: [{ enrollment_id: a, child_id: b, status: "late" }] } });
  m.status.mockResolvedValue({ ok: false, kind });
  m.sessions.mockImplementation(async (_actor, input) => ({ ok: true, data: { date: input.date, timeZone: input.workspaceId === a ? "Asia/Kolkata" : "UTC", serverNow: "2026-11-10T20:30:00Z", sessions: input.workspaceId === a ? [session, { ...session, id: c, batchName: "Evening Art" }] : [{ ...session, id: c, batchName: "North class" }], next: null } }));
  m.load.mockImplementation(async (_actor, input) => ({ ok: true, data: { session: { ...session, id: input.sessionId, rosterSize: 1 }, timeZone: input.workspaceId === a ? "Asia/Kolkata" : "UTC", serverNow: "2026-11-10T20:30:00Z", sheetVersion: 0, savedAt: null, savedRosterToken: null, rosterToken: "a".repeat(64), rosterTooLarge: false, rows: [{ enrollmentId: a, enrollmentVersion: 1, childId: input.sessionId === b ? b : c, childName: input.sessionId === b ? "Original child" : "New child", status: null, confirmedAt: null }] } }));
}
it("releases restored conflict recovery before opening another real session without claiming success", async () => {
  seedRestoredRejection("conflict");
  render(<TodayPanel />);
  await screen.findByText("Original child");
  fireEvent.click(screen.getByRole("button", { name: "Check saved result" }));
  await screen.findByText(/Attendance changed. Review/);
  expect(screen.queryByText("Attendance saved.")).not.toBeInTheDocument();
  expect(sessionStorage.getItem(`parentplus:attendance-pending:${a}`)).toBeNull();
  fireEvent.click(await screen.findByRole("button", { name: "Open attendance for Evening Art" }));
  await screen.findByText("New child");
  expect(screen.queryByText("Original child")).not.toBeInTheDocument();
  expect(m.load).toHaveBeenCalledWith(a, { workspaceId: a, sessionId: c });
});
it("releases restored forbidden recovery before opening another academy without claiming success", async () => {
  seedRestoredRejection("forbidden");
  render(<TodayPanel />);
  await screen.findByText("Original child");
  fireEvent.click(screen.getByRole("button", { name: "Check saved result" }));
  await screen.findByText(/Save was rejected/);
  expect(screen.queryByText("Attendance saved.")).not.toBeInTheDocument();
  expect(sessionStorage.getItem(`parentplus:attendance-pending:${a}`)).toBeNull();
  fireEvent.change(screen.getByLabelText("Academy"), { target: { value: b } });
  fireEvent.click(await screen.findByRole("button", { name: "Open attendance for North class" }));
  await screen.findByText("New child");
  expect(screen.queryByText("Original child")).not.toBeInTheDocument();
  expect(m.load).toHaveBeenCalledWith(a, { workspaceId: b, sessionId: c });
});
async function cancelInitialSessionRead(scope: "date" | "academy") {
  let resolve!: (v: unknown) => void;
  m.sessions.mockReturnValueOnce(new Promise(r => { resolve = r; }));
  render(<TodayPanel />);
  await waitFor(() => expect(m.sessions).toHaveBeenCalledTimes(1));
  if (scope === "academy") fireEvent.change(screen.getByLabelText("Academy"), { target: { value: b } });
  else fireEvent.change(screen.getByLabelText("Session date"), { target: { value: "2026-11-12" } });
  await screen.findByRole("button", { name: "Open attendance for Morning Art" });
  expect(screen.getByRole("button", { name: "Refresh Today" })).toBeEnabled();
  expect(screen.queryByText("Loading…")).not.toBeInTheDocument();
  await act(async () => resolve({ ok: true, data: { date: "2026-11-11", timeZone: "Asia/Kolkata", serverNow: "2026-11-10T20:30:00Z", sessions: [{ ...session, batchName: "Stale initial class" }], next: null } }));
  expect(screen.queryByText("Stale initial class")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Refresh Today" })).toBeEnabled();
  expect(screen.queryByText("Loading…")).not.toBeInTheDocument();
}
it("releases initial loading ownership when academy changes during a delayed session read", () => cancelInitialSessionRead("academy"));
it("releases initial loading ownership when date changes during a delayed session read", () => cancelInitialSessionRead("date"));
it("cancels delayed academy pagination on scope change without stranding refresh or loading", async () => {
  const academies = [{ workspaceId: a, name: "River Academy", timeZone: "Asia/Kolkata" }, { workspaceId: b, name: "North Academy", timeZone: "UTC" }, ...Array.from({ length: 48 }, (_, i) => ({ workspaceId: `c0000000-0000-4000-8000-${String(i).padStart(12, "0")}`, name: `Academy ${i}`, timeZone: "UTC" }))];
  let resolve!: (v: unknown) => void;
  m.academies.mockResolvedValueOnce({ ok: true, data: { academies, nextAfter: academies[49].workspaceId } }).mockReturnValueOnce(new Promise(r => { resolve = r; }));
  render(<TodayPanel />);
  await screen.findByRole("button", { name: "Open attendance for Morning Art" });
  fireEvent.click(screen.getByRole("button", { name: "Load more academies" }));
  await waitFor(() => expect(m.academies).toHaveBeenCalledTimes(2));
  fireEvent.change(screen.getByLabelText("Academy"), { target: { value: b } });
  await screen.findByRole("button", { name: "Open attendance for Morning Art" });
  expect(screen.getByRole("button", { name: "Refresh Today" })).toBeEnabled();
  expect(screen.getByRole("button", { name: "Load more academies" })).toBeEnabled();
  expect(screen.queryByText("Loading…")).not.toBeInTheDocument();
  await act(async () => resolve({ ok: true, data: { academies: [{ workspaceId: "dddddddd-dddd-4ddd-8ddd-dddddddddddd", name: "Stale academy", timeZone: "UTC" }], nextAfter: null } }));
  expect(screen.queryByRole("option", { name: "Stale academy" })).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Refresh Today" })).toBeEnabled();
});
it("keeps unknown restored requests bound to the original operation while another session is selected", async () => {
  seedRestoredRejection("conflict");
  m.status.mockResolvedValue({ ok: true, data: { state: "unknown", receipt: null } });
  render(<TodayPanel />);
  await screen.findByText("Original child");
  fireEvent.click(screen.getByRole("button", { name: "Check saved result" }));
  await screen.findByText(/Save result is unconfirmed/);
  fireEvent.click(await screen.findByRole("button", { name: "Open attendance for Evening Art" }));
  expect(screen.getByText("Original child")).toBeVisible();
  expect(screen.queryByText("New child")).not.toBeInTheDocument();
  expect(JSON.parse(sessionStorage.getItem(`parentplus:attendance-pending:${a}`)!)).toMatchObject({ actorId: a, requestId: c, payload: { operation: "save_attendance", workspace_id: a, session_id: b } });
  expect(m.load).not.toHaveBeenCalledWith(a, { workspaceId: a, sessionId: c });
  expect(m.save).not.toHaveBeenCalled();
});
