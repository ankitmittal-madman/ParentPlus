"use server";
import { createClient } from "@/lib/supabase/server";
import { isAuthApiError, isAuthSessionMissingError } from "@supabase/supabase-js";
import { canonicalAttendancePayload, decodeSheet, decodeAttendanceReceipt, decodeRequestStatus, decodeSignals, type Result, type AttendancePayload, type AttendanceReceipt, type AttendanceSheet, type RequestStatus, type SignalPage } from "@/modules/attendance/contracts";
import { decodeAcademies, decodeTodaySessions, type AcademyPage, type TodayPage } from "@/modules/today/contracts";
import { object, uuid, id, date, timestamp, exact, sessionOrder, signalOrder } from "@/modules/attendance/validation";
const invalid = { ok: false, kind: "invalid" } as const;
/** Only documented session denials are definitive; provider/transport failures preserve recovery. */
function definitiveAuthDenial(error: unknown): boolean {
  return isAuthSessionMissingError(error) || (
    isAuthApiError(error) && [400, 401, 403].includes(error.status) &&
    ["bad_jwt", "no_authorization", "user_not_found", "user_banned", "session_not_found", "session_expired"].includes(error.code ?? "")
  );
}
async function call<T>(actor: unknown, rpc: string, args: Record<string, unknown>, decode: (v: unknown) => T | null): Promise<Result<T>> {
  if (!uuid(actor))
    return invalid;
  try {
    const client = await createClient();
    const { data: auth, error: authError } = await client.auth.getUser();
    if (authError)
      return { ok: false, kind: definitiveAuthDenial(authError) ? "forbidden" : "unknown" };
    if (!uuid(auth.user?.id) || id(auth.user.id) !== id(actor))
      return { ok: false, kind: "forbidden" };
    const { data, error } = await client.rpc(rpc, args);
    if (error) {
      const code = error.code;
      return { ok: false, kind: code === "22023" ? "invalid" : code === "42501" ? "forbidden" : code === "40001" || code === "23505" ? "conflict" : "unknown" };
    }
    const result = decode(data);
    return result === null ? { ok: false, kind: "unknown" } : { ok: true, data: result };
  }
  catch {
    return { ok: false, kind: "unknown" };
  }
}
export async function listTodayAcademies(actor: unknown, input: unknown): Promise<Result<AcademyPage>> {
  if (!object(input) || !exact(input, ["after"]) || !(input.after === null || uuid(input.after)))
    return invalid;
  const after = input.after === null ? null : id(input.after);
  return call(actor, "app_today_academies", { p_after: after }, v => {
    const p = decodeAcademies(v);
    return p && (!after || p.academies.every(a => a.workspaceId > after)) ? p : null;
  });
}
export async function listTodaySessions(actor: unknown, input: unknown): Promise<Result<TodayPage>> {
  if (!object(input) || !exact(input, ["workspaceId", "date", "after"]) || !uuid(input.workspaceId) || !date(input.date))
    return invalid;
  const after = input.after;
  if (after !== null && (!object(after) || !exact(after, ["startsAt", "id"]) || !timestamp(after.startsAt) || !uuid(after.id)))
    return invalid;
  return call(actor, "app_today_sessions", {
    p_workspace_id: id(input.workspaceId), p_date: input.date, p_after_start: after === null ? null : (after as Record<string, unknown>).startsAt, p_after_id: after === null ? null : id((after as {
      id: string;
    }).id)
  }, v => {
    const p = decodeTodaySessions(v);
    return p && p.date === input.date && (after === null || p.sessions.every(s => sessionOrder(s, after as {
      startsAt: string;
      id: string;
    }) > 0)) ? p : null;
  });
}
export async function loadAttendanceSheet(actor: unknown, input: unknown): Promise<Result<AttendanceSheet>> {
  if (!object(input) || !exact(input, ["workspaceId", "sessionId"]) || !uuid(input.workspaceId) || !uuid(input.sessionId))
    return invalid;
  return call(actor, "app_attendance_sheet", { p_workspace_id: id(input.workspaceId), p_session_id: id(input.sessionId) }, v => {
    const sheet = decodeSheet(v);
    return sheet && sheet.session.id === id(input.sessionId as string) ? sheet : null;
  });
}
function writeInput(input: unknown): {
  requestId: string;
  payload: AttendancePayload;
} | null {
  if (!object(input) || !exact(input, ["requestId", "payload"]) || !uuid(input.requestId))
    return null;
  const payload = canonicalAttendancePayload(input.payload);
  return payload ? { requestId: id(input.requestId), payload } : null;
}
function matchingReceipt(v: unknown, input: {
  requestId: string;
  payload: AttendancePayload;
}): AttendanceReceipt | null {
  const r = decodeAttendanceReceipt(v);
  const p = input.payload;
  return r && r.requestId === input.requestId && r.sessionId === p.session_id && r.sessionVersion === p.expected_session_version && r.sheetVersion === p.expected_sheet_version + 1 && r.rosterToken === p.roster_token && r.recordCount === p.records.length ? r : null;
}
export async function saveAttendance(actor: unknown, input: unknown): Promise<Result<AttendanceReceipt>> {
  const value = writeInput(input);
  if (!value)
    return invalid;
  const p = value.payload;
  return call(actor, "app_save_attendance", { p_workspace_id: p.workspace_id, p_session_id: p.session_id, p_expected_session_version: p.expected_session_version, p_expected_sheet_version: p.expected_sheet_version, p_roster_token: p.roster_token, p_records: p.records, p_request_id: value.requestId }, v => matchingReceipt(v, value));
}
export async function attendanceRequestStatus(actor: unknown, input: unknown): Promise<Result<RequestStatus<AttendanceReceipt>>> {
  const value = writeInput(input);
  if (!value)
    return invalid;
  const p = value.payload;
  return call(actor, "app_attendance_request_status", { p_workspace_id: p.workspace_id, p_session_id: p.session_id, p_request_id: value.requestId, p_payload: p }, v => decodeRequestStatus(v, r => matchingReceipt(r, value)));
}
export async function listSessionSignals(actor: unknown, input: unknown): Promise<Result<SignalPage>> {
  if (!object(input) || !exact(input, ["workspaceId", "sessionId", "after"]) || !uuid(input.workspaceId) || !uuid(input.sessionId))
    return invalid;
  const after = input.after;
  if (after !== null && (!object(after) || !exact(after, ["childId", "actorId"]) || !uuid(after.childId) || !uuid(after.actorId)))
    return invalid;
  return call(actor, "app_session_parent_signals", {
    p_workspace_id: id(input.workspaceId), p_session_id: id(input.sessionId), p_after_child: after === null ? null : id((after as {
      childId: string;
    }).childId), p_after_actor: after === null ? null : id((after as {
      actorId: string;
    }).actorId)
  }, v => {
    const p = decodeSignals(v);
    return p && (after === null || p.signals.every(s => signalOrder(s, after as {
      childId: string;
      actorId: string;
    }) > 0)) ? p : null;
  });
}
