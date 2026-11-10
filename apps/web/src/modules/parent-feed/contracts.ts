import { attendanceStatus, decodeSignal, signalPair, type AttendanceStatus, type Signal, type SignalReason, type SignalType } from "../attendance/contracts";
import { bounded, date, id, increasing, integer, object, sessionOrder, text, timestamp, timestampOrder, uuid, zone } from "../attendance/validation";
import { decodeSessionCursor, localDate, type SessionCursor } from "../today/contracts";
export type ParentChild = { id: string; name: string };
export type EnrollmentStatus = "pending" | "active" | "paused" | "completed" | "withdrawn" | "cancelled";
export type ParentBatch = { batchId: string; batchName: string; courseName: string; enrollmentId: string; enrollmentStatus: EnrollmentStatus };
export type ParentBatchPage = { batches: ParentBatch[]; nextAfter: string | null };
export type ParentSession = { id: string; batchId: string; batchName: string; courseName: string; startsAt: string; endsAt: string; status: "scheduled" | "cancelled"; version: number; enrollmentId: string; enrollmentStatus: EnrollmentStatus; attendance: { status: AttendanceStatus; confirmedAt: string } | null; ownLatestSignal: Signal | null; canSignal: boolean };
export type ParentSessionPage = { date: string; timeZone: string; serverNow: string; sessions: ParentSession[]; next: SessionCursor | null };
export type ParentItemEnvelope = { id: string; type: string; schemaVersion: number; childId: string; classId: string; priority: number; createdAt: string; expiresAt: string | null; payload: Record<string, unknown> };
export type ItemCursor = { createdAt: string; id: string };
export type ParentItemPage = { items: ParentItemEnvelope[]; next: ItemCursor | null };
export type WeekRow = { sessionId: string; batchId: string; batchName: string; date: string; status: AttendanceStatus; confirmedAt: string };
export type ParentWeek = { weekStart: string; timeZone: string; attendedCount: number; recordedCount: number; rows: WeekRow[]; hasMore: boolean };
export type SignalReceipt = { requestId: string; signalId: string; sessionId: string; childId: string; type: SignalType; reason: SignalReason | null; createdAt: string };
const enrollment = (v: unknown): v is EnrollmentStatus => typeof v === "string" && ["pending", "active", "paused", "completed", "withdrawn", "cancelled"].includes(v);
export function decodeParentChildren(v: unknown): ParentChild[] | null {
  return bounded(v, 100, r => object(r) && uuid(r.child_id) && text(r.display_name) ? { id: id(r.child_id), name: r.display_name } : null, r => r.id);
}
export function decodeParentBatches(v: unknown): ParentBatchPage | null {
  if (!object(v) || !(v.next_after === null || uuid(v.next_after))) return null;
  const batches = bounded(v.batches, 50, r => object(r) && uuid(r.batch_id) && text(r.batch_name) && text(r.course_name) && uuid(r.enrollment_id) && enrollment(r.enrollment_status) ? { batchId: id(r.batch_id), batchName: r.batch_name, courseName: r.course_name, enrollmentId: id(r.enrollment_id), enrollmentStatus: r.enrollment_status } : null, r => r.batchId);
  if (!batches || !increasing(batches, (a, b) => a.batchId.localeCompare(b.batchId)) || new Set(batches.map(b => b.enrollmentId)).size !== batches.length || (v.next_after !== null && (batches.length !== 50 || batches.at(-1)?.batchId !== id(v.next_after)))) return null;
  return { batches, nextAfter: v.next_after === null ? null : id(v.next_after) };
}
export function decodeParentSession(v: unknown): ParentSession | null {
  if (!object(v) || !uuid(v.id) || !uuid(v.batch_id) || !text(v.batch_name) || !text(v.course_name) || !timestamp(v.starts_at) || !timestamp(v.ends_at) || timestampOrder(v.ends_at, v.starts_at) <= 0 || !["scheduled", "cancelled"].includes(v.status as string) || !integer(v.version, 1) || !uuid(v.enrollment_id) || !enrollment(v.enrollment_status) || typeof v.can_signal !== "boolean") return null;
  const attendance = v.attendance === null ? null : object(v.attendance) && attendanceStatus(v.attendance.status) && timestamp(v.attendance.confirmed_at) ? { status: v.attendance.status, confirmedAt: v.attendance.confirmed_at } : undefined;
  const signal = v.own_latest_signal === null ? null : decodeSignal(v.own_latest_signal);
  if (attendance === undefined || (v.own_latest_signal !== null && !signal) || (v.can_signal && (v.status !== "scheduled" || v.enrollment_status !== "active"))) return null;
  return { id: id(v.id), batchId: id(v.batch_id), batchName: v.batch_name, courseName: v.course_name, startsAt: v.starts_at, endsAt: v.ends_at, status: v.status as ParentSession["status"], version: v.version, enrollmentId: id(v.enrollment_id), enrollmentStatus: v.enrollment_status, attendance, ownLatestSignal: signal, canSignal: v.can_signal };
}
export function decodeParentSessions(v: unknown): ParentSessionPage | null {
  if (!object(v) || !date(v.date) || !zone(v.time_zone) || !timestamp(v.server_now)) return null;
  const sessions = bounded(v.sessions, 50, decodeParentSession, s => s.id);
  const next = v.next === null ? null : decodeSessionCursor(v.next);
  if (!sessions || !increasing(sessions, sessionOrder) || sessions.some(s => localDate(v.time_zone as string, new Date(s.startsAt)) !== v.date || (s.canSignal && v.date !== localDate(v.time_zone as string, new Date(v.server_now as string))))) return null;
  if (v.next !== null && (!next || sessions.length !== 50 || sessionOrder(next, sessions.at(-1)!) !== 0)) return null;
  return { date: v.date, timeZone: v.time_zone, serverNow: v.server_now, sessions, next };
}
export const itemOrder = (a: ItemCursor, b: ItemCursor) => timestampOrder(a.createdAt, b.createdAt) || a.id.localeCompare(b.id);
export function decodeParentItems(v: unknown): ParentItemPage | null {
  if (!object(v)) return null;
  const items = bounded(v.items, 50, r => {
    if (!object(r) || !uuid(r.id) || !text(r.type, 80) || !integer(r.schema_version, 1) || !uuid(r.child_id) || !uuid(r.class_id) || !integer(r.priority, 0, 100) || !timestamp(r.created_at) || !(r.expires_at === null || timestamp(r.expires_at)) || !object(r.payload)) return null;
    try { if (new TextEncoder().encode(JSON.stringify(r.payload)).length > 16384) return null; } catch { return null; }
    return { id: id(r.id), type: r.type, schemaVersion: r.schema_version, childId: id(r.child_id), classId: id(r.class_id), priority: r.priority, createdAt: r.created_at, expiresAt: r.expires_at as string | null, payload: r.payload };
  }, r => r.id);
  const next = v.next === null ? null : object(v.next) && timestamp(v.next.created_at) && uuid(v.next.id) ? { createdAt: v.next.created_at, id: id(v.next.id) } : undefined;
  if (!items || next === undefined || !increasing(items, (a, b) => -itemOrder(a, b)) || (next && (items.length !== 50 || itemOrder(next, items.at(-1)!) !== 0))) return null;
  return { items, next };
}
export function mondayOf(day: string): string {
  const d = new Date(`${day}T12:00:00Z`); d.setUTCDate(d.getUTCDate() - (d.getUTCDay() + 6) % 7); return d.toISOString().slice(0, 10);
}
export function decodeParentWeek(v: unknown): ParentWeek | null {
  if (!object(v) || !date(v.week_start) || mondayOf(v.week_start) !== v.week_start || !zone(v.time_zone) || !integer(v.attended_count, 0, Number.MAX_SAFE_INTEGER) || !integer(v.recorded_count, 0, Number.MAX_SAFE_INTEGER) || v.attended_count > v.recorded_count || typeof v.has_more !== "boolean") return null;
  const end = new Date(`${v.week_start}T12:00:00Z`); end.setUTCDate(end.getUTCDate() + 7);
  const rows = bounded(v.rows, 50, r => object(r) && uuid(r.session_id) && uuid(r.batch_id) && text(r.batch_name) && date(r.date) && r.date >= (v.week_start as string) && r.date < end.toISOString().slice(0, 10) && attendanceStatus(r.status) && timestamp(r.confirmed_at) ? { sessionId: id(r.session_id), batchId: id(r.batch_id), batchName: r.batch_name, date: r.date, status: r.status, confirmedAt: r.confirmed_at } : null, r => r.sessionId);
  if (!rows || rows.length !== Math.min(v.recorded_count, 50) || v.has_more !== (v.recorded_count > 50)) return null;
  const attended = rows.filter(r => ["present", "late", "make_up"].includes(r.status)).length;
  if (attended > v.attended_count || (!v.has_more && attended !== v.attended_count)) return null;
  return { weekStart: v.week_start, timeZone: v.time_zone, attendedCount: v.attended_count, recordedCount: v.recorded_count, rows, hasMore: v.has_more };
}
export function decodeSignalReceipt(v: unknown): SignalReceipt | null {
  return object(v) && uuid(v.request_id) && uuid(v.signal_id) && uuid(v.session_id) && uuid(v.child_id) && signalPair(v.type, v.reason) && timestamp(v.created_at) ? { requestId: id(v.request_id), signalId: id(v.signal_id), sessionId: id(v.session_id), childId: id(v.child_id), type: v.type, reason: v.reason as SignalReason | null, createdAt: v.created_at } : null;
}
/** Rebuild exact allowlisted routes. A link grants no destination authority. */
export function safeParentAction(value: unknown, childId: string): { label: string; href: string } | null {
  if (!object(value) || !text(value.label, 80) || typeof value.href !== "string" || !uuid(childId)) return null;
  for (const route of ["/parent", "/parent/children"]) {
    if (value.href === route) return { label: value.label, href: route };
    if (value.href === `${route}?child=${id(childId)}`) return { label: value.label, href: `${route}?child=${id(childId)}` };
  }
  return null;
}
