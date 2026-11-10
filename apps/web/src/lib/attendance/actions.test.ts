import { beforeEach, expect, it, vi } from "vitest";
import { GoTrueClient, AuthApiError, AuthSessionMissingError, AuthUnknownError, AuthRetryableFetchError } from "@supabase/supabase-js";
const m = vi.hoisted(() => ({ create: vi.fn(), getUser: vi.fn(), rpc: vi.fn() }));
vi.mock("@/lib/supabase/server", () => ({ createClient: m.create }));
import { listTodayAcademies, listTodaySessions, loadAttendanceSheet, saveAttendance, attendanceRequestStatus, listSessionSignals } from "./actions";
const a = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", b = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", t = "2026-11-10T12:00:00+00:00", token = "a".repeat(64);
const payload = { operation: "save_attendance", workspace_id: a, session_id: b, expected_session_version: 1, expected_sheet_version: 0, roster_token: token, records: [{ enrollment_id: a, child_id: b, status: "present" }] };
const write = { requestId: a, payload };
const receipt = { request_id: a, session_id: b, sheet_version: 1, session_version: 1, roster_token: token, saved_at: t, record_count: 1 };
const session = { id: b, batch_id: a, batch_name: "Morning", course_name: "Art", starts_at: t, ends_at: "2026-11-10T13:00:00Z", status: "scheduled", version: 1, sheet_version: 0, roster_size: 0, roster_too_large: false, marked_count: 0, attendance_current: false };
const cases = [
  { call: () => listTodayAcademies(a, { after: null }), rpc: "app_today_academies", args: { p_after: null }, reply: { academies: [{ workspace_id: a, name: "Academy", time_zone: "Asia/Kolkata" }], next_after: null }, want: { academies: [{ workspaceId: a, name: "Academy", timeZone: "Asia/Kolkata" }], nextAfter: null } },
  { call: () => listTodaySessions(a, { workspaceId: a, date: "2026-11-10", after: null }), rpc: "app_today_sessions", args: { p_workspace_id: a, p_date: "2026-11-10", p_after_start: null, p_after_id: null }, reply: { date: "2026-11-10", time_zone: "Asia/Kolkata", server_now: t, sessions: [session], next: null }, want: { date: "2026-11-10", timeZone: "Asia/Kolkata", serverNow: t, sessions: [{ id: b, batchId: a, batchName: "Morning", courseName: "Art", startsAt: t, endsAt: "2026-11-10T13:00:00Z", status: "scheduled", version: 1, sheetVersion: 0, rosterSize: 0, rosterTooLarge: false, markedCount: 0, attendanceCurrent: false }], next: null } },
  { call: () => loadAttendanceSheet(a, { workspaceId: a, sessionId: b }), rpc: "app_attendance_sheet", args: { p_workspace_id: a, p_session_id: b }, reply: { session, time_zone: "Asia/Kolkata", server_now: t, sheet_version: 0, saved_at: null, saved_roster_token: null, roster_token: token, roster_too_large: false, rows: [] }, want: { session: { id: b, batchId: a, batchName: "Morning", courseName: "Art", startsAt: t, endsAt: "2026-11-10T13:00:00Z", status: "scheduled", version: 1, sheetVersion: 0, rosterSize: 0, rosterTooLarge: false, markedCount: 0, attendanceCurrent: false }, timeZone: "Asia/Kolkata", serverNow: t, sheetVersion: 0, savedAt: null, savedRosterToken: null, rosterToken: token, rosterTooLarge: false, rows: [] } },
  { call: () => saveAttendance(a, write), rpc: "app_save_attendance", args: { p_workspace_id: a, p_session_id: b, p_expected_session_version: 1, p_expected_sheet_version: 0, p_roster_token: token, p_records: payload.records, p_request_id: a }, reply: receipt, want: { requestId: a, sessionId: b, sheetVersion: 1, sessionVersion: 1, rosterToken: token, savedAt: t, recordCount: 1 } },
  { call: () => attendanceRequestStatus(a, write), rpc: "app_attendance_request_status", args: { p_workspace_id: a, p_session_id: b, p_request_id: a, p_payload: payload }, reply: { state: "known", receipt }, want: { state: "known", receipt: { requestId: a, sessionId: b, sheetVersion: 1, sessionVersion: 1, rosterToken: token, savedAt: t, recordCount: 1 } } },
  { call: () => listSessionSignals(a, { workspaceId: a, sessionId: b, after: null }), rpc: "app_session_parent_signals", args: { p_workspace_id: a, p_session_id: b, p_after_child: null, p_after_actor: null }, reply: { signals: [{ id: a, child_id: b, actor_id: a, type: "missing_today", reason: "unwell", created_at: t }], next: null, server_now: t }, want: { signals: [{ id: a, childId: b, actorId: a, type: "missing_today", reason: "unwell", createdAt: t }], next: null, serverNow: t } }
];
beforeEach(() => {
  vi.resetAllMocks();
  m.create.mockResolvedValue({ auth: { getUser: m.getUser }, rpc: m.rpc });
  m.getUser.mockResolvedValue({ data: { user: { id: a } }, error: null });
});
async function projects(i: number) {
  const c = cases[i];
  m.rpc.mockResolvedValue({ data: { ...c.reply, private_note: "secret" }, error: null });
  expect(await c.call()).toEqual({ ok: true, data: c.want });
  expect(m.rpc).toHaveBeenCalledWith(c.rpc, c.args);
}
async function fence(i: number) {
  for (const user of [{ id: b }, null]) {
    m.getUser.mockResolvedValue({ data: { user }, error: null });
    expect(await cases[i].call()).toEqual({ ok: false, kind: "forbidden" });
  }
  expect(m.rpc).not.toHaveBeenCalled();
}
async function malformed(i: number) {
  for (const data of [null, {}, [cases[i].reply]]) {
    m.rpc.mockResolvedValue({ data, error: null });
    expect(await cases[i].call()).toEqual({ ok: false, kind: "unknown" });
  }
  m.rpc.mockRejectedValue({ code: "40001", message: "private" });
  expect(await cases[i].call()).toEqual({ ok: false, kind: "unknown" });
}
it("maps app_today_academies exact JSON object and arguments", () => projects(0));
it("maps app_today_sessions exact JSON object and arguments", () => projects(1));
it("maps app_attendance_sheet exact JSON object and arguments", () => projects(2));
it("maps app_save_attendance canonical records and receipt", () => projects(3));
it("maps app_attendance_request_status complete payload and receipt", () => projects(4));
it("maps app_session_parent_signals cursor and provenance", () => projects(5));
it("fences app_today_academies expected actor against getUser", () => fence(0));
it("fences app_today_sessions expected actor against getUser", () => fence(1));
it("fences app_attendance_sheet expected actor against getUser", () => fence(2));
it("fences app_save_attendance expected actor against getUser", () => fence(3));
it("fences app_attendance_request_status expected actor against getUser", () => fence(4));
it("fences app_session_parent_signals expected actor against getUser", () => fence(5));
it("rejects malformed app_today_academies and redacts transport failures", () => malformed(0));
it("rejects malformed app_today_sessions and redacts transport failures", () => malformed(1));
it("rejects malformed app_attendance_sheet and redacts transport failures", () => malformed(2));
it("keeps malformed app_save_attendance and thrown errors unknown", () => malformed(3));
it("keeps malformed app_attendance_request_status and thrown errors unknown", () => malformed(4));
it("rejects malformed app_session_parent_signals and redacts transport failures", () => malformed(5));
it("classifies only definitive structured SQL rejections and never leaks messages", async () => {
  for (const [code, kind] of [["22023", "invalid"], ["42501", "forbidden"], ["40001", "conflict"], ["23505", "conflict"], ["40P01", "unknown"], ["25001", "unknown"], [40001, "unknown"], [undefined, "unknown"]]) {
    m.rpc.mockResolvedValue({ data: null, error: { code, message: "private child SQL", details: "secret" } });
    expect(await saveAttendance(a, write)).toEqual({ ok: false, kind });
    expect(await attendanceRequestStatus(a, write)).toEqual({ ok: false, kind });
  }
});
it("validates IDs dates complete cursor pairs and canonical bodies before opening a client", async () => {
  for (const call of [() => listTodayAcademies("bad", { after: null }), () => listTodayAcademies(a, { after: "bad" }), () => listTodaySessions(a, { workspaceId: a, date: "2026-02-30", after: null }), () => listTodaySessions(a, { workspaceId: a, date: "1999-01-01", after: null }), () => listTodaySessions(a, { workspaceId: a, date: "2026-11-10", after: { startsAt: t } }), () => loadAttendanceSheet(a, { workspaceId: a, sessionId: null }), () => listSessionSignals(a, { workspaceId: a, sessionId: b, after: { childId: b } }), () => saveAttendance(a, { ...write, payload: { ...payload, actor_id: a } }), () => attendanceRequestStatus(a, { ...write, requestId: "bad" })])
    expect(await call()).toEqual({ ok: false, kind: "invalid" });
  expect(m.create).not.toHaveBeenCalled();
});
it("passes both non-null session and signal cursor components", async () => {
  m.rpc.mockResolvedValue({ data: { date: "2026-11-10", time_zone: "UTC", server_now: t, sessions: [], next: null }, error: null });
  expect((await listTodaySessions(a, { workspaceId: a, date: "2026-11-10", after: { startsAt: t, id: b } })).ok).toBe(true);
  expect(m.rpc).toHaveBeenLastCalledWith("app_today_sessions", { p_workspace_id: a, p_date: "2026-11-10", p_after_start: t, p_after_id: b });
  m.rpc.mockResolvedValue({ data: { signals: [], next: null, server_now: t }, error: null });
  expect((await listSessionSignals(a, { workspaceId: a, sessionId: b, after: { childId: b, actorId: a } })).ok).toBe(true);
  expect(m.rpc).toHaveBeenLastCalledWith("app_session_parent_signals", { p_workspace_id: a, p_session_id: b, p_after_child: b, p_after_actor: a });
});
it("rejects mismatched request session count token and version receipts", async () => {
  for (const changed of [{ request_id: b }, { session_id: a }, { record_count: 2 }, { roster_token: "b".repeat(64) }, { session_version: 2 }, { sheet_version: 3 }]) {
    m.rpc.mockResolvedValue({ data: { ...receipt, ...changed }, error: null });
    expect(await saveAttendance(a, write)).toEqual({ ok: false, kind: "unknown" });
    m.rpc.mockResolvedValue({ data: { state: "known", receipt: { ...receipt, ...changed } }, error: null });
    expect(await attendanceRequestStatus(a, write)).toEqual({ ok: false, kind: "unknown" });
  }
});
it("keeps an unknown recovery state distinct from success and rejects wrong-scope reads", async () => {
  m.rpc.mockResolvedValue({ data: { state: "unknown", receipt: null }, error: null });
  expect(await attendanceRequestStatus(a, write)).toEqual({ ok: true, data: { state: "unknown", receipt: null } });
  m.rpc.mockResolvedValue({ data: { ...cases[1].reply, date: "2026-11-11" }, error: null });
  expect(await cases[1].call()).toEqual({ ok: false, kind: "unknown" });
  m.rpc.mockResolvedValue({ data: { ...cases[2].reply, session: { ...session, id: a } }, error: null });
  expect(await cases[2].call()).toEqual({ ok: false, kind: "unknown" });
});
it("rejects auth errors and redacts client creation failures", async () => {
  m.getUser.mockResolvedValue({ data: { user: { id: a } }, error: { message: "private" } });
  expect(await cases[0].call()).toEqual({ ok: false, kind: "unknown" });
  m.create.mockRejectedValue(Error("credential secret"));
  expect(await cases[3].call()).toEqual({ ok: false, kind: "unknown" });
  expect(m.rpc).not.toHaveBeenCalled();
});
it("rejects non-advancing academy session and report cursor pages", async () => {
  m.rpc.mockResolvedValue({ data: cases[0].reply, error: null });
  expect(await listTodayAcademies(a, { after: b })).toEqual({ ok: false, kind: "unknown" });
  m.rpc.mockResolvedValue({ data: cases[1].reply, error: null });
  expect(await listTodaySessions(a, { workspaceId: a, date: "2026-11-10", after: { startsAt: t, id: b } })).toEqual({ ok: false, kind: "unknown" });
  m.rpc.mockResolvedValue({ data: cases[5].reply, error: null });
  expect(await listSessionSignals(a, { workspaceId: a, sessionId: b, after: { childId: b, actorId: a } })).toEqual({ ok: false, kind: "unknown" });
});
it("preserves SQL microseconds for advancing and nonadvancing session cursor pages", async () => {
  m.rpc.mockResolvedValue({ data: { ...cases[1].reply, sessions: [{ ...session, id: a, starts_at: "2026-11-10T12:00:00.000002+00:00" }] }, error: null });
  expect((await listTodaySessions(a, { workspaceId: a, date: "2026-11-10", after: { startsAt: "2026-11-10T12:00:00.000001Z", id: b } })).ok).toBe(true);
  m.rpc.mockResolvedValue({ data: { ...cases[1].reply, sessions: [{ ...session, id: b, starts_at: "2026-11-10T12:00:00.000001Z" }] }, error: null });
  expect(await listTodaySessions(a, { workspaceId: a, date: "2026-11-10", after: { startsAt: "2026-11-10T12:00:00.000002+00:00", id: a } })).toEqual({ ok: false, kind: "unknown" });
});

it("keeps the actual SDK returned retryable 503 verification result unknown before any attendance RPC", async () => {
  const sdk = new GoTrueClient({ url: "http://synthetic.invalid/auth/v1", persistSession: false, autoRefreshToken: false, detectSessionInUrl: false, fetch: async () => new Response('{"message":"synthetic infrastructure outage"}', { status: 503, headers: { "Content-Type": "application/json" } }) });
  const response = await sdk.getUser("synthetic-offline-jwt");
  expect(response.error).toBeInstanceOf(AuthRetryableFetchError);
  expect(response.error).toMatchObject({ name: "AuthRetryableFetchError", status: 503 });
  m.getUser.mockResolvedValue(response);
  for (const c of cases) expect(await c.call()).toEqual({ ok: false, kind: "unknown" });
  expect(m.rpc).not.toHaveBeenCalled();
});
it("keeps ambiguous timeout throttling unknown and malformed authentication failures nondefinitive", async () => {
  for (const error of [new AuthUnknownError("private", Error("private")), new AuthApiError("private", 429, "over_request_rate_limit"), new AuthApiError("private", 408, "request_timeout"), new AuthApiError("private", 503, "bad_jwt"), new AuthApiError("private", 400, "unexpected_failure"), { name: "AuthRetryableFetchError", status: 0 }, { message: "private" }]) {
    m.getUser.mockResolvedValue({ data: { user: { id: a } }, error });
    expect(await saveAttendance(a, write)).toEqual({ ok: false, kind: "unknown" });
    expect(await attendanceRequestStatus(a, write)).toEqual({ ok: false, kind: "unknown" });
  }
  expect(m.rpc).not.toHaveBeenCalled();
});
it("retains definitive SDK session denial and verified actor mismatch without calling an RPC", async () => {
  for (const error of [new AuthSessionMissingError(), new AuthApiError("private", 401, "bad_jwt"), new AuthApiError("private", 403, "user_banned"), new AuthApiError("private", 400, "session_expired")]) {
    m.getUser.mockResolvedValue({ data: { user: null }, error });
    expect(await saveAttendance(a, write)).toEqual({ ok: false, kind: "forbidden" });
    expect(await attendanceRequestStatus(a, write)).toEqual({ ok: false, kind: "forbidden" });
  }
  m.getUser.mockResolvedValue({ data: { user: { id: b } }, error: null });
  expect(await saveAttendance(a, write)).toEqual({ ok: false, kind: "forbidden" });
  expect(m.rpc).not.toHaveBeenCalled();
});
