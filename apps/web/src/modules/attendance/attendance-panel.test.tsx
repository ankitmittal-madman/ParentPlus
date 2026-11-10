import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { AttendancePanel } from "./attendance-panel";
import { readPending, writePending, type PendingOperation } from "./pending";
import type { AttendanceSheet } from "./contracts";
const m = vi.hoisted(() => ({ session: vi.fn(), observe: vi.fn(), load: vi.fn(), save: vi.fn(), status: vi.fn(), signals: vi.fn(), saved: vi.fn(), changed: undefined as undefined | (() => void) }));
vi.mock("@/lib/families/actions", () => ({ familySession: m.session }));
vi.mock("@/lib/auth/session-observer", () => ({ observeSessionChanges: m.observe }));
vi.mock("@/lib/attendance/actions", () => ({ loadAttendanceSheet: m.load, saveAttendance: m.save, attendanceRequestStatus: m.status, listSessionSignals: m.signals }));
const a = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", b = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", c = "cccccccc-cccc-4ccc-8ccc-cccccccccccc", time = "2026-11-10T12:00:00Z", token = "a".repeat(64);
const sheet: AttendanceSheet = { session: { id: b, batchId: a, batchName: "Morning", courseName: "Art", startsAt: time, endsAt: "2026-11-10T13:00:00Z", status: "scheduled", version: 1, sheetVersion: 0, rosterSize: 2, rosterTooLarge: false, markedCount: 0, attendanceCurrent: false }, timeZone: "Asia/Kolkata", serverNow: time, sheetVersion: 0, savedAt: null, savedRosterToken: null, rosterToken: token, rosterTooLarge: false, rows: [{ enrollmentId: a, enrollmentVersion: 1, childId: b, childName: "Asha", status: null, confirmedAt: null }, { enrollmentId: b, enrollmentVersion: 1, childId: c, childName: "Dev", status: null, confirmedAt: null }] };
const pending: PendingOperation = { format: 1, actorId: a, requestId: c, payload: { operation: "save_attendance", workspace_id: a, session_id: b, expected_session_version: 1, expected_sheet_version: 0, roster_token: token, records: [{ enrollment_id: a, child_id: b, status: "present" }, { enrollment_id: b, child_id: c, status: "late" }] } };
const receipt = { requestId: c, sessionId: b, sheetVersion: 1, sessionVersion: 1, rosterToken: token, savedAt: time, recordCount: 2 };
const open = () => render(<AttendancePanel actorId={a} workspaceId={a} sessionId={b} onSaved={m.saved} />);
const mark = (status: string, child: string) => screen.getByRole("button", { name: `${status} for ${child}` });
beforeEach(() => {
  vi.restoreAllMocks();
  vi.resetAllMocks();
  vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
  sessionStorage.clear();
  m.session.mockResolvedValue({ ok: true, data: a });
  m.observe.mockImplementation(cb => {
    m.changed = cb;
    return () => {
    };
  });
  m.load.mockResolvedValue({ ok: true, data: sheet });
  m.signals.mockResolvedValue({ ok: true, data: { signals: [], next: null, serverNow: time } });
  m.save.mockResolvedValue({ ok: false, kind: "unknown" });
  m.status.mockResolvedValue({ ok: true, data: { state: "unknown", receipt: null } });
});
it("autoloads a verified complete roster without implicitly marking any child", async () => {
  open();
  await screen.findByText("Asha");
  expect(mark("Present", "Asha")).toHaveAttribute("aria-pressed", "false");
  expect(screen.getByRole("button", { name: "Save attendance" })).toBeDisabled();
  expect(m.save).not.toHaveBeenCalled();
  expect(m.load).toHaveBeenCalledWith(a, { workspaceId: a, sessionId: b });
});
it("supports P L A and More marks and requires every row before saving", async () => {
  open();
  await screen.findByText("Asha");
  fireEvent.click(mark("Late", "Asha"));
  fireEvent.click(screen.getByLabelText("More marks for Dev"));
  fireEvent.click(mark("Excused", "Dev"));
  expect(mark("Excused", "Dev")).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByRole("button", { name: "Save attendance" })).toBeEnabled();
  fireEvent.click(mark("Make-up", "Dev"));
  expect(mark("Make-up", "Dev")).toHaveAttribute("aria-pressed", "true");
  expect(m.save).not.toHaveBeenCalled();
});
it("Mark all present fills only unmarked rows preserving explicitly selected exceptions", async () => {
  open();
  await screen.findByText("Asha");
  fireEvent.click(mark("Late", "Asha"));
  fireEvent.click(screen.getByRole("button", { name: "Mark all present" }));
  expect(mark("Late", "Asha")).toHaveAttribute("aria-pressed", "true");
  expect(mark("Present", "Dev")).toHaveAttribute("aria-pressed", "true");
  expect(m.save).not.toHaveBeenCalled();
});
it("reviews parent reports and applies absence suggestions only to unmarked missing rows", async () => {
  m.signals.mockResolvedValue({ ok: true, data: { signals: [{ id: a, childId: b, actorId: a, type: "missing_today", reason: "unwell", createdAt: time }, { id: b, childId: c, actorId: a, type: "missing_today", reason: "other", createdAt: time }], next: null, serverNow: time } });
  open();
  await screen.findByText("Asha");
  await waitFor(() => expect(m.signals).toHaveBeenCalled());
  fireEvent.click(mark("Late", "Asha"));
  fireEvent.click(screen.getByRole("button", { name: "Review parent signals" }));
  expect(screen.getAllByText(/Parent report/).length).toBeGreaterThan(0);
  fireEvent.click(screen.getByRole("button", { name: "Apply absent suggestions" }));
  expect(mark("Late", "Asha")).toHaveAttribute("aria-pressed", "true");
  expect(mark("Absent", "Dev")).toHaveAttribute("aria-pressed", "true");
  expect(m.save).not.toHaveBeenCalled();
});
it("persists before sending and retries the exact original key and full body after unknown status", async () => {
  let original: unknown;
  m.save.mockImplementation(async (actor, input) => {
    expect(readPending(a, "attendance")).toMatchObject({ kind: "pending", value: { actorId: actor, requestId: input.requestId, payload: input.payload } });
    original ??= input;
    return { ok: false, kind: "unknown" };
  });
  open();
  await screen.findByText("Asha");
  fireEvent.click(screen.getByRole("button", { name: "Mark all present" }));
  fireEvent.click(screen.getByRole("button", { name: "Save attendance" }));
  await screen.findByText(/Save result is unconfirmed/);
  expect(mark("Late", "Asha")).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "Check saved result" }));
  await screen.findByText(/Save result is unconfirmed/);
  expect(m.status).toHaveBeenCalledWith(a, original);
  fireEvent.click(screen.getByRole("button", { name: "Retry same request" }));
  await waitFor(() => expect(m.save).toHaveBeenCalledTimes(2));
  expect(m.save.mock.calls[1][1]).toEqual(original);
  expect(readPending(a, "attendance").kind).toBe("pending");
});
it("restores a dropped reply after reload and resolves old receipt by fetching the current sheet", async () => {
  writePending(pending);
  m.status.mockResolvedValue({ ok: true, data: { state: "known", receipt } });
  const newer = { ...sheet, sheetVersion: 3, savedAt: time, savedRosterToken: token, session: { ...sheet.session, sheetVersion: 3 }, rows: sheet.rows.map(r => ({ ...r, status: "absent", confirmedAt: time })) };
  m.load.mockResolvedValueOnce({ ok: true, data: sheet }).mockResolvedValue({ ok: true, data: newer });
  open();
  await screen.findByText("Asha");
  fireEvent.click(screen.getByRole("button", { name: "Check saved result" }));
  await screen.findByText("Attendance saved.");
  expect(mark("Absent", "Asha")).toHaveAttribute("aria-pressed", "true");
  expect(mark("Present", "Asha")).toHaveAttribute("aria-pressed", "false");
  expect(readPending(a, "attendance")).toEqual({ kind: "none" });
  expect(m.saved).toHaveBeenCalledTimes(1);
});
it("refreshes a definitive conflict and asks for review without merging edited marks", async () => {
  m.save.mockResolvedValue({ ok: false, kind: "conflict" });
  m.load.mockResolvedValueOnce({ ok: true, data: sheet }).mockResolvedValue({ ok: true, data: { ...sheet, rows: sheet.rows.map(r => ({ ...r, status: "absent", confirmedAt: time })) } });
  open();
  await screen.findByText("Asha");
  fireEvent.click(screen.getByRole("button", { name: "Mark all present" }));
  fireEvent.click(screen.getByRole("button", { name: "Save attendance" }));
  await screen.findByText(/Attendance changed. Review/);
  expect(mark("Absent", "Asha")).toHaveAttribute("aria-pressed", "true");
  expect(readPending(a, "attendance")).toEqual({ kind: "none" });
  expect(m.saved).not.toHaveBeenCalled();
});
it("keeps corrupt recovery state quarantined and blocks replacement writes", async () => {
  sessionStorage.setItem(`parentplus:attendance-pending:${a}`, "broken");
  open();
  await screen.findByText("Asha");
  expect(screen.getByText(/Saved recovery data cannot be read/)).toBeVisible();
  expect(screen.getByRole("button", { name: "Save attendance" })).toBeDisabled();
  expect(m.save).not.toHaveBeenCalled();
});
it("warns and retains the original operation in memory when storage is unavailable", async () => {
  vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
    throw Error("denied");
  });
  let input: unknown;
  m.save.mockImplementation(async (_actor, v) => {
    input = v;
    return { ok: false, kind: "unknown" };
  });
  const first = open();
  await screen.findByText("Asha");
  fireEvent.click(screen.getByRole("button", { name: "Mark all present" }));
  fireEvent.click(screen.getByRole("button", { name: "Save attendance" }));
  await screen.findByText(/Keep this tab open/);
  first.unmount();
  open();
  await screen.findByText("Asha");
  expect(screen.getByRole("button", { name: "Save attendance" })).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "Retry same request" }));
  await waitFor(() => expect(m.save).toHaveBeenCalledTimes(2));
  expect(m.save.mock.calls[1][1]).toEqual(input);
  m.status.mockResolvedValue({ ok: true, data: { state: "known", receipt } });
  fireEvent.click(screen.getByRole("button", { name: "Check saved result" }));
  await screen.findByText("Attendance saved.");
});
it("hides private rows on account change and ignores late save callbacks while retaining recovery", async () => {
  let resolve!: (v: unknown) => void;
  m.save.mockReturnValue(new Promise(r => {
    resolve = r;
  }));
  open();
  await screen.findByText("Asha");
  fireEvent.click(screen.getByRole("button", { name: "Mark all present" }));
  fireEvent.click(screen.getByRole("button", { name: "Save attendance" }));
  await waitFor(() => expect(readPending(a, "attendance").kind).toBe("pending"));
  m.session.mockResolvedValue({ ok: true, data: c });
  act(() => m.changed?.());
  expect(screen.queryByText("Asha")).not.toBeInTheDocument();
  await act(async () => resolve({ ok: true, data: receipt }));
  expect(screen.queryByText("Attendance saved.")).not.toBeInTheDocument();
  expect(m.saved).not.toHaveBeenCalled();
  expect(readPending(a, "attendance").kind).toBe("pending");
});
it("ignores late roster promises after a session switch", async () => {
  let resolve!: (v: unknown) => void;
  m.load.mockReturnValueOnce(new Promise(r => {
    resolve = r;
  }));
  const v = open();
  await waitFor(() => expect(m.load).toHaveBeenCalled());
  m.load.mockResolvedValue({ ok: true, data: { ...sheet, session: { ...sheet.session, id: c }, rows: sheet.rows.map(r => ({ ...r, childName: "New child" })) } });
  v.rerender(<AttendancePanel actorId={a} workspaceId={a} sessionId={c} onSaved={m.saved} />);
  await screen.findAllByText("New child");
  await act(async () => resolve({ ok: true, data: sheet }));
  expect(screen.queryByText("Asha")).not.toBeInTheDocument();
});
it("shows an honest empty roster without offering an empty save", async () => {
  m.load.mockResolvedValue({ ok: true, data: { ...sheet, session: { ...sheet.session, rosterSize: 0 }, rows: [] } });
  open();
  await screen.findByText(/No enrolled children/);
  expect(screen.getByRole("button", { name: "Save attendance" })).toBeDisabled();
});
it("shows cancelled sessions read only and preserves saved history", async () => {
  m.load.mockResolvedValue({ ok: true, data: { ...sheet, session: { ...sheet.session, status: "cancelled" } } });
  open();
  await screen.findByText(/This session is cancelled/);
  expect(mark("Present", "Asha")).toBeDisabled();
  expect(screen.getByRole("button", { name: "Save attendance" })).toBeDisabled();
});
it("blocks a roster above two hundred without displaying a partial editable list", async () => {
  m.load.mockResolvedValue({ ok: true, data: { ...sheet, rosterTooLarge: true, rosterToken: null, session: { ...sheet.session, rosterTooLarge: true, rosterSize: null }, rows: [] } });
  open();
  await screen.findByText(/more than 200 active enrolments/);
  expect(screen.queryByText("Asha")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Save attendance" })).toBeDisabled();
});
it("saves the complete two hundred row roster in one explicit operation", async () => {
  const rows = Array.from({ length: 200 }, (_, i) => ({ ...sheet.rows[0], enrollmentId: `00000000-0000-4000-8000-${String(i).padStart(12, "0")}`, childId: `10000000-0000-4000-8000-${String(i).padStart(12, "0")}`, childName: `Child ${i}` }));
  m.load.mockResolvedValue({ ok: true, data: { ...sheet, session: { ...sheet.session, rosterSize: 200 }, rows } });
  open();
  await screen.findByText("Child 199");
  fireEvent.click(screen.getByRole("button", { name: "Mark all present" }));
  fireEvent.click(screen.getByRole("button", { name: "Save attendance" }));
  await waitFor(() => expect(m.save).toHaveBeenCalled());
  expect(m.save.mock.calls[0][1].payload.records).toHaveLength(200);
});
it("polls signals only while visible without resetting dirty attendance marks", async () => {
  vi.useFakeTimers();
  open();
  await act(async () => {
    await vi.advanceTimersByTimeAsync(0);
  });
  expect(screen.getByText("Asha")).toBeVisible();
  fireEvent.click(mark("Late", "Asha"));
  await act(async () => {
    await vi.advanceTimersByTimeAsync(15000);
  });
  expect(m.signals.mock.calls.length).toBeGreaterThan(1);
  expect(mark("Late", "Asha")).toHaveAttribute("aria-pressed", "true");
  Object.defineProperty(document, "visibilityState", { configurable: true, value: "hidden" });
  act(() => document.dispatchEvent(new Event("visibilitychange")));
  const n = m.signals.mock.calls.length;
  await act(async () => {
    await vi.advanceTimersByTimeAsync(30000);
  });
  expect(m.signals).toHaveBeenCalledTimes(n);
  vi.useRealTimers();
  Object.defineProperty(document, "visibilityState", { configurable: true, value: "visible" });
});
it("reloads the saved sheet after a confirmed write and clears only its original pending operation", async () => {
  m.save.mockResolvedValue({ ok: true, data: receipt });
  m.load.mockResolvedValueOnce({ ok: true, data: sheet }).mockResolvedValue({ ok: true, data: { ...sheet, rows: sheet.rows.map(r => ({ ...r, status: "present", confirmedAt: time })) } });
  open();
  await screen.findByText("Asha");
  fireEvent.click(screen.getByRole("button", { name: "Mark all present" }));
  fireEvent.click(screen.getByRole("button", { name: "Save attendance" }));
  await screen.findByText("Attendance saved.");
  expect(readPending(a, "attendance")).toEqual({ kind: "none" });
  expect(m.load).toHaveBeenCalledTimes(2);
  expect(m.saved).toHaveBeenCalledTimes(1);
  expect(mark("Present", "Asha")).toHaveAttribute("aria-pressed", "true");
});
it("does not turn late drop or pickup reports into attendance suggestions", async () => {
  m.signals.mockResolvedValue({ ok: true, data: { signals: [{ id: a, childId: b, actorId: a, type: "running_late", reason: null, createdAt: time }, { id: b, childId: c, actorId: a, type: "dropped_off", reason: null, createdAt: time }], next: null, serverNow: time } });
  open();
  await screen.findByText("Asha");
  fireEvent.click(screen.getByRole("button", { name: "Review parent signals" }));
  fireEvent.click(screen.getByRole("button", { name: "Apply absent suggestions" }));
  expect(mark("Present", "Asha")).toHaveAttribute("aria-pressed", "false");
  expect(mark("Late", "Asha")).toHaveAttribute("aria-pressed", "false");
  expect(mark("Absent", "Dev")).toHaveAttribute("aria-pressed", "false");
  expect(screen.getByRole("button", { name: "Save attendance" })).toBeDisabled();
});
