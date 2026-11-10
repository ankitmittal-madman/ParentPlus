import { object, uuid, id, integer, text, token, timestamp, zone, exact, bounded, increasing, signalOrder } from "./validation";
import { decodeSession, type Session } from "../today/contracts";
export type Result<T> = {
  ok: true;
  data: T;
} | {
  ok: false;
  kind: "invalid" | "forbidden" | "conflict" | "unknown";
};
export type AttendanceStatus = "present" | "late" | "absent" | "excused" | "make_up";
export type SignalType = "running_late" | "missing_today" | "dropped_off" | "picked_up";
export type SignalReason = "unwell" | "travelling" | "other";
export type AttendanceRecord = {
  enrollment_id: string;
  child_id: string;
  status: AttendanceStatus;
};
export type AttendancePayload = {
  operation: "save_attendance";
  workspace_id: string;
  session_id: string;
  expected_session_version: number;
  expected_sheet_version: number;
  roster_token: string;
  records: AttendanceRecord[];
};
export type SignalPayload = {
  operation: "send_parent_signal";
  child_id: string;
  workspace_id: string;
  session_id: string;
  expected_session_version: number;
  type: SignalType;
  reason: SignalReason | null;
};
export type AttendanceReceipt = {
  requestId: string;
  sessionId: string;
  sheetVersion: number;
  sessionVersion: number;
  rosterToken: string;
  savedAt: string;
  recordCount: number;
};
export type RequestStatus<T> = {
  state: "unknown";
  receipt: null;
} | {
  state: "known";
  receipt: T;
};
export type RosterRow = {
  enrollmentId: string;
  enrollmentVersion: number;
  childId: string;
  childName: string;
  status: AttendanceStatus | null;
  confirmedAt: string | null;
};
export type AttendanceSheet = {
  session: Session;
  timeZone: string;
  serverNow: string;
  sheetVersion: number;
  savedAt: string | null;
  savedRosterToken: string | null;
  rosterToken: string | null;
  rosterTooLarge: boolean;
  rows: RosterRow[];
};
export type Signal = {
  id: string;
  childId: string;
  actorId: string;
  type: SignalType;
  reason: SignalReason | null;
  createdAt: string;
};
export type SignalCursor = {
  childId: string;
  actorId: string;
};
export type SignalPage = {
  signals: Signal[];
  next: SignalCursor | null;
  serverNow: string;
};
export const attendanceStatus = (v: unknown): v is AttendanceStatus => typeof v === "string" && ["present", "late", "absent", "excused", "make_up"].includes(v);
export function signalPair(type: unknown, reason: unknown): type is SignalType {
  return type === "missing_today" ? typeof reason === "string" && ["unwell", "travelling", "other"].includes(reason) : typeof type === "string" && ["running_late", "dropped_off", "picked_up"].includes(type) && reason === null;
}
export function canonicalAttendancePayload(v: unknown): AttendancePayload | null {
  if (!object(v) || !exact(v, ["operation", "workspace_id", "session_id", "expected_session_version", "expected_sheet_version", "roster_token", "records"]) || v.operation !== "save_attendance" || !uuid(v.workspace_id) || !uuid(v.session_id) || !integer(v.expected_session_version, 1) || !integer(v.expected_sheet_version) || !token(v.roster_token))
    return null;
  const records = bounded(v.records, 200, r => object(r) && exact(r, ["enrollment_id", "child_id", "status"]) && uuid(r.enrollment_id) && uuid(r.child_id) && attendanceStatus(r.status) ? { enrollment_id: id(r.enrollment_id), child_id: id(r.child_id), status: r.status } : null, r => r.enrollment_id);
  if (!records?.length || new Set(records.map(r => r.child_id)).size !== records.length)
    return null;
  records.sort((a, b) => a.enrollment_id.localeCompare(b.enrollment_id));
  const result: AttendancePayload = { operation: "save_attendance", workspace_id: id(v.workspace_id), session_id: id(v.session_id), expected_session_version: v.expected_session_version, expected_sheet_version: v.expected_sheet_version, roster_token: v.roster_token, records };
  return new TextEncoder().encode(JSON.stringify(result)).length <= 65536 ? result : null;
}
export function canonicalSignalPayload(v: unknown): SignalPayload | null {
  return object(v) && exact(v, ["operation", "child_id", "workspace_id", "session_id", "expected_session_version", "type", "reason"]) && v.operation === "send_parent_signal" && uuid(v.child_id) && uuid(v.workspace_id) && uuid(v.session_id) && integer(v.expected_session_version, 1) && signalPair(v.type, v.reason) ? { operation: "send_parent_signal", child_id: id(v.child_id), workspace_id: id(v.workspace_id), session_id: id(v.session_id), expected_session_version: v.expected_session_version, type: v.type, reason: v.reason as SignalReason | null } : null;
}
export function decodeAttendanceReceipt(v: unknown): AttendanceReceipt | null {
  return object(v) && uuid(v.request_id) && uuid(v.session_id) && integer(v.sheet_version, 1) && integer(v.session_version, 1) && token(v.roster_token) && timestamp(v.saved_at) && integer(v.record_count, 1, 200) ? { requestId: id(v.request_id), sessionId: id(v.session_id), sheetVersion: v.sheet_version, sessionVersion: v.session_version, rosterToken: v.roster_token, savedAt: v.saved_at, recordCount: v.record_count } : null;
}
export function decodeRequestStatus<T>(v: unknown, decode: (v: unknown) => T | null): RequestStatus<T> | null {
  if (!object(v))
    return null;
  if (v.state === "unknown" && v.receipt === null)
    return { state: "unknown", receipt: null };
  const receipt = v.state === "known" ? decode(v.receipt) : null;
  return receipt ? { state: "known", receipt } : null;
}
export function decodeSheet(v: unknown): AttendanceSheet | null {
  if (!object(v) || !zone(v.time_zone) || !timestamp(v.server_now) || !integer(v.sheet_version) || typeof v.roster_too_large !== "boolean" || !(v.roster_token === null || token(v.roster_token)) || !(v.saved_at === null || timestamp(v.saved_at)) || !(v.saved_roster_token === null || token(v.saved_roster_token)))
    return null;
  const session = decodeSession(v.session);
  const rows = bounded(v.rows, 200, r => object(r) && uuid(r.enrollment_id) && integer(r.enrollment_version, 1) && uuid(r.child_id) && text(r.child_name) && (r.status === null ? r.confirmed_at === null : attendanceStatus(r.status) && timestamp(r.confirmed_at)) ? { enrollmentId: id(r.enrollment_id), enrollmentVersion: r.enrollment_version, childId: id(r.child_id), childName: r.child_name, status: r.status as AttendanceStatus | null, confirmedAt: r.confirmed_at as string | null } : null, r => r.enrollmentId);
  if (!session || !rows || new Set(rows.map(r => r.childId)).size !== rows.length || session.sheetVersion !== v.sheet_version || session.rosterTooLarge !== v.roster_too_large)
    return null;
  if (v.sheet_version === 0 ? (v.saved_at !== null || v.saved_roster_token !== null) : (v.saved_at === null || v.saved_roster_token === null))
    return null;
  if (v.roster_too_large ? (rows.length !== 0 || v.roster_token !== null) : (v.roster_token === null || session.rosterSize !== rows.length))
    return null;
  return { session, timeZone: v.time_zone, serverNow: v.server_now, sheetVersion: v.sheet_version, savedAt: v.saved_at, savedRosterToken: v.saved_roster_token, rosterToken: v.roster_token, rosterTooLarge: v.roster_too_large, rows };
}
export function decodeSignal(v: unknown): Signal | null {
  return object(v) && uuid(v.id) && uuid(v.child_id) && uuid(v.actor_id) && signalPair(v.type, v.reason) && timestamp(v.created_at) ? { id: id(v.id), childId: id(v.child_id), actorId: id(v.actor_id), type: v.type, reason: v.reason as SignalReason | null, createdAt: v.created_at } : null;
}
export function decodeSignals(v: unknown): SignalPage | null {
  if (!object(v) || !timestamp(v.server_now))
    return null;
  const signals = bounded(v.signals, 50, decodeSignal, s => `${s.childId}:${s.actorId}`);
  const next = v.next === null ? null : object(v.next) && uuid(v.next.child_id) && uuid(v.next.actor_id) ? { childId: id(v.next.child_id), actorId: id(v.next.actor_id) } : undefined;
  if (!signals || !increasing(signals, signalOrder) || next === undefined || new Set(signals.map(s => s.id)).size !== signals.length)
    return null;
  if (next && (signals.length !== 50 || signals.at(-1)?.childId !== next.childId || signals.at(-1)?.actorId !== next.actorId))
    return null;
  return { signals, next, serverNow: v.server_now };
}
