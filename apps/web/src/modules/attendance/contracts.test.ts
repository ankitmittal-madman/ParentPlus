import { expect, it } from "vitest";
import { canonicalAttendancePayload, canonicalSignalPayload, decodeSheet, decodeAttendanceReceipt, decodeSignals } from "./contracts";
import { decodeAcademies, decodeTodaySessions } from "../today/contracts";
const a = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", b = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", token = "a".repeat(64), time = "2026-11-10T12:00:00+00:00";
const record = { enrollment_id: a, child_id: b, status: "late" };
const payload = { operation: "save_attendance", workspace_id: a, session_id: b, expected_session_version: 1, expected_sheet_version: 0, roster_token: token, records: [record] };
const session = { id: b, batch_id: a, batch_name: "Morning", course_name: "Art", starts_at: time, ends_at: "2026-11-10T13:00:00Z", status: "scheduled", version: 1, sheet_version: 0, roster_size: 1, roster_too_large: false, marked_count: 0, attendance_current: false };
const sheet = { session, time_zone: "Asia/Kolkata", server_now: time, sheet_version: 0, saved_at: null, saved_roster_token: null, roster_token: token, roster_too_large: false, rows: [{ enrollment_id: a, enrollment_version: 1, child_id: b, child_name: "Asha", status: null, confirmed_at: null }] };
it("normalizes exact attendance payload UUIDs and sorted records without actor fields", () => {
  expect(canonicalAttendancePayload({ ...payload, workspace_id: a.toUpperCase(), records: [{ ...record, enrollment_id: b, child_id: a }, record] })).toEqual({ ...payload, records: [record, { ...record, enrollment_id: b, child_id: a }] });
  expect(canonicalAttendancePayload({ ...payload, actor_id: a })).toBeNull();
});
it("rejects malformed duplicate oversized attendance bodies and invalid versions", () => {
  for (const bad of [null, [], { ...payload, records: [] }, { ...payload, records: [record, record] }, { ...payload, records: [record, { ...record, enrollment_id: b, child_id: b.toUpperCase() }] }, { ...payload, records: [{ ...record, notes: "secret" }] }, { ...payload, records: Array(201).fill(record) }, { ...payload, expected_session_version: 1.5 }, { ...payload, expected_session_version: 2147483648 }, { ...payload, expected_sheet_version: -1 }, { ...payload, roster_token: token.toUpperCase() }])
    expect(canonicalAttendancePayload(bad)).toBeNull();
});
it("normalizes the exact signal payload and enforces reason nullability for all four reports", () => {
  const p = { operation: "send_parent_signal", child_id: a, workspace_id: a, session_id: b, expected_session_version: 1, type: "missing_today", reason: "unwell" };
  expect(canonicalSignalPayload(p)).toEqual(p);
  for (const type of ["running_late", "dropped_off", "picked_up"]) {
    expect(canonicalSignalPayload({ ...p, type, reason: null })).toEqual({ ...p, type, reason: null });
    expect(canonicalSignalPayload({ ...p, type })).toBeNull();
  }
  for (const reason of [null, "free text", undefined])
    expect(canonicalSignalPayload({ ...p, reason })).toBeNull();
  expect(canonicalSignalPayload({ ...p, request_id: a })).toBeNull();
});
it("decodes JSON objects UTC offsets and unmarked coherent sheets into camelCase", () => {
  expect(decodeSheet(sheet)).toMatchObject({ sheetVersion: 0, savedAt: null, rows: [{ enrollmentId: a, childId: b, status: null }], session: { batchName: "Morning" } });
  expect(decodeSheet([sheet])).toBeNull();
  expect(decodeSheet({ ...sheet, rows: [sheet.rows[0], sheet.rows[0]] })).toBeNull();
  expect(decodeSheet({ ...sheet, roster_token: undefined })).toBeNull();
  expect(decodeSheet({ ...sheet, rows: [{ ...sheet.rows[0], confirmed_at: time }] })).toBeNull();
});
it("accepts exactly two hundred roster rows and blocks malformed oversized or inconsistent sheet replies", () => {
  const rows = Array.from({ length: 200 }, (_, i) => ({ ...sheet.rows[0], enrollment_id: `00000000-0000-4000-8000-${String(i).padStart(12, "0")}`, child_id: `10000000-0000-4000-8000-${String(i).padStart(12, "0")}` }));
  expect(decodeSheet({ ...sheet, session: { ...session, roster_size: 200 }, rows })?.rows).toHaveLength(200);
  expect(decodeSheet({ ...sheet, rows: [...rows, rows[0]] })).toBeNull();
  expect(decodeSheet({ ...sheet, roster_too_large: true, roster_token: null, session: { ...session, roster_too_large: true, roster_size: null }, rows: [] })).toMatchObject({ rosterTooLarge: true, rows: [] });
  expect(decodeSheet({ ...sheet, roster_too_large: true })).toBeNull();
});
it("validates attendance receipts and exact known unknown recovery envelopes", () => {
  const r = { request_id: a, session_id: b, sheet_version: 1, session_version: 1, roster_token: token, saved_at: time, record_count: 1 };
  expect(decodeAttendanceReceipt({ ...r, private_note: "secret" })).toEqual({ requestId: a, sessionId: b, sheetVersion: 1, sessionVersion: 1, rosterToken: token, savedAt: time, recordCount: 1 });
  for (const bad of [{ ...r, record_count: 0 }, { ...r, sheet_version: 0 }, { ...r, saved_at: "yesterday" }, [r], {}])
    expect(decodeAttendanceReceipt(bad)).toBeNull();
});
it("bounds academy and session pages validates finite dates zones cursors and duplicate IDs", () => {
  expect(decodeAcademies({ academies: [{ workspace_id: a, name: "Academy", time_zone: null }], next_after: null })).toEqual({ academies: [{ workspaceId: a, name: "Academy", timeZone: null }], nextAfter: null });
  expect(decodeAcademies({ academies: Array(51).fill({ workspace_id: a, name: "Academy", time_zone: "UTC" }), next_after: null })).toBeNull();
  const p = { date: "2026-11-10", time_zone: "Asia/Kolkata", server_now: time, sessions: [session], next: null };
  expect(decodeTodaySessions(p)).toMatchObject({ date: "2026-11-10", sessions: [{ id: b }] });
  for (const bad of [{ ...p, date: "2026-02-30" }, { ...p, time_zone: "Mars/Bad" }, { ...p, next: {} }, { ...p, sessions: [session, session] }, { ...p, sessions: Array(51).fill(session) }, { ...p, sessions: [{ ...session, ends_at: "bad" }] }])
    expect(decodeTodaySessions(bad)).toBeNull();
});
it("validates bounded latest parent reports reason pairs actor identities and cursors", () => {
  const s = { id: a, child_id: b, actor_id: a, type: "missing_today", reason: "unwell", created_at: time };
  expect(decodeSignals({ signals: [s], next: null, server_now: time })).toMatchObject({ signals: [{ childId: b, actorId: a, type: "missing_today" }] });
  for (const signals of [[s, s], [{ ...s, reason: null }], [{ ...s, type: "dropped_off", reason: "other" }], Array(51).fill(s)])
    expect(decodeSignals({ signals, next: null, server_now: time })).toBeNull();
  expect(decodeSignals({ signals: [], next: { child_id: b }, server_now: time })).toBeNull();
});
it("accepts exact fifty-row pages with advancing cursors and rejects fifty-one unique rows", () => {
  const key = (i: number) => `00000000-0000-4000-8000-${String(i).padStart(12, "0")}`;
  const academies = Array.from({ length: 51 }, (_, i) => ({ workspace_id: key(i), name: `Academy ${i}`, time_zone: "UTC" }));
  expect(decodeAcademies({ academies: academies.slice(0, 50), next_after: key(49) })?.academies).toHaveLength(50);
  expect(decodeAcademies({ academies, next_after: null })).toBeNull();
  const sessions = Array.from({ length: 51 }, (_, i) => ({ ...session, id: key(i) }));
  expect(decodeTodaySessions({ date: "2026-11-10", time_zone: "UTC", server_now: time, sessions: sessions.slice(0, 50), next: { starts_at: time, id: key(49) } })?.sessions).toHaveLength(50);
  expect(decodeTodaySessions({ date: "2026-11-10", time_zone: "UTC", server_now: time, sessions, next: null })).toBeNull();
  const signals = Array.from({ length: 51 }, (_, i) => ({ id: key(i), child_id: key(i), actor_id: a, type: "running_late", reason: null, created_at: time }));
  expect(decodeSignals({ signals: signals.slice(0, 50), next: { child_id: key(49), actor_id: a }, server_now: time })?.signals).toHaveLength(50);
  expect(decodeSignals({ signals, next: null, server_now: time })).toBeNull();
});
it("rejects out-of-order pages impossible current flags and sessions outside the returned local date", () => {
  expect(decodeAcademies({ academies: [{ workspace_id: b, name: "B", time_zone: "UTC" }, { workspace_id: a, name: "A", time_zone: "UTC" }], next_after: null })).toBeNull();
  expect(decodeTodaySessions({ date: "2026-11-10", time_zone: "UTC", server_now: time, sessions: [{ ...session, id: b }, { ...session, id: a }], next: null })).toBeNull();
  expect(decodeTodaySessions({ date: "2026-11-11", time_zone: "UTC", server_now: time, sessions: [session], next: null })).toBeNull();
  expect(decodeTodaySessions({ date: "2026-11-10", time_zone: "UTC", server_now: time, sessions: [{ ...session, attendance_current: true }], next: null })).toBeNull();
  expect(decodeSignals({ signals: [{ id: b, child_id: b, actor_id: a, type: "running_late", reason: null, created_at: time }, { id: a, child_id: a, actor_id: a, type: "running_late", reason: null, created_at: time }], next: null, server_now: time })).toBeNull();
});
it("accepts UTC instants across the supported academy-local date boundaries", () => {
  const early = { ...session, starts_at: "1999-12-31T12:00:00Z", ends_at: "1999-12-31T13:00:00Z" };
  expect(decodeTodaySessions({ date: "2000-01-01", time_zone: "Pacific/Kiritimati", server_now: time, sessions: [early], next: null })?.sessions).toHaveLength(1);
  const late = { ...session, starts_at: "2101-01-01T02:00:00Z", ends_at: "2101-01-01T03:00:00Z" };
  expect(decodeTodaySessions({ date: "2100-12-31", time_zone: "Pacific/Honolulu", server_now: time, sessions: [late], next: null })?.sessions).toHaveLength(1);
});
it("fails closed when any required sheet session row or receipt field is missing", () => {
  const without = (v: object, k: string) => Object.fromEntries(Object.entries(v).filter(([name]) => name !== k));
  for (const k of Object.keys(sheet))
    expect(decodeSheet(without(sheet, k))).toBeNull();
  for (const k of Object.keys(session))
    expect(decodeSheet({ ...sheet, session: without(session, k) })).toBeNull();
  for (const k of Object.keys(sheet.rows[0]))
    expect(decodeSheet({ ...sheet, rows: [without(sheet.rows[0], k)] })).toBeNull();
  const receipt = { request_id: a, session_id: b, sheet_version: 1, session_version: 1, roster_token: token, saved_at: time, record_count: 1 };
  for (const k of Object.keys(receipt))
    expect(decodeAttendanceReceipt(without(receipt, k))).toBeNull();
});
it("keeps academies with an invalid configured zone visible as unavailable without inventing a zone", () => {
  expect(decodeAcademies({ academies: [{ workspace_id: a, name: "Academy", time_zone: "Invalid/Zone" }], next_after: null })).toEqual({ academies: [{ workspaceId: a, name: "Academy", timeZone: null }], nextAfter: null });
  expect(decodeAcademies({ academies: [{ workspace_id: a, name: "Academy", time_zone: 42 }], next_after: null })).toBeNull();
});
it("preserves SQL microseconds when ordering complete session pages despite reverse UUID order", () => {
  const sessions = [{ ...session, id: b, starts_at: "2026-11-10T12:00:00.000001Z" }, { ...session, id: a, starts_at: "2026-11-10T12:00:00.000002+00:00" }];
  expect(decodeTodaySessions({ date: "2026-11-10", time_zone: "UTC", server_now: time, sessions, next: null })?.sessions.map(s => s.id)).toEqual([b, a]);
  expect(decodeTodaySessions({ date: "2026-11-10", time_zone: "UTC", server_now: time, sessions: [...sessions].reverse(), next: null })).toBeNull();
});
it("accepts positive submillisecond session durations and rejects equivalent zero-length UTC instants", () => {
  const precise = { ...session, starts_at: "2026-11-10T12:00:00.000001Z", ends_at: "2026-11-10T12:00:00.000002+00:00" };
  expect(decodeTodaySessions({ date: "2026-11-10", time_zone: "UTC", server_now: time, sessions: [precise], next: null })?.sessions).toHaveLength(1);
  expect(decodeTodaySessions({ date: "2026-11-10", time_zone: "UTC", server_now: time, sessions: [{ ...precise, ends_at: "2026-11-10T12:00:00.000001+00:00" }], next: null })).toBeNull();
});
