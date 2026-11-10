import { object, uuid, id, integer, text, timestamp, date, zone, bounded, increasing, sessionOrder, timestampOrder } from "../attendance/validation";
export type Academy = {
  workspaceId: string;
  name: string;
  timeZone: string | null;
};
export type AcademyPage = {
  academies: Academy[];
  nextAfter: string | null;
};
export type Session = {
  id: string;
  batchId: string;
  batchName: string;
  courseName: string;
  startsAt: string;
  endsAt: string;
  status: "scheduled" | "cancelled";
  version: number;
  sheetVersion: number;
  rosterSize: number | null;
  rosterTooLarge: boolean;
  markedCount: number;
  attendanceCurrent: boolean;
};
export type SessionCursor = {
  startsAt: string;
  id: string;
};
export type TodayPage = {
  date: string;
  timeZone: string;
  serverNow: string;
  sessions: Session[];
  next: SessionCursor | null;
};
export function decodeAcademies(v: unknown): AcademyPage | null {
  if (!object(v) || !(v.next_after === null || uuid(v.next_after)))
    return null;
  const academies = bounded(v.academies, 50, r => object(r) && uuid(r.workspace_id) && text(r.name) && (r.time_zone === null || typeof r.time_zone === "string") ? { workspaceId: id(r.workspace_id), name: r.name, timeZone: zone(r.time_zone) ? r.time_zone : null } : null, r => r.workspaceId);
  if (!academies || !increasing(academies, (a, b) => a.workspaceId.localeCompare(b.workspaceId)) || (v.next_after !== null && (academies.length !== 50 || academies.at(-1)?.workspaceId !== id(v.next_after))))
    return null;
  return { academies, nextAfter: v.next_after === null ? null : id(v.next_after) };
}
export function decodeSession(v: unknown): Session | null {
  if (!object(v) || !uuid(v.id) || !uuid(v.batch_id) || !text(v.batch_name) || !text(v.course_name) || !timestamp(v.starts_at) || !timestamp(v.ends_at) || timestampOrder(v.ends_at, v.starts_at) <= 0 || !(v.status === "scheduled" || v.status === "cancelled") || !integer(v.version, 1) || !integer(v.sheet_version) || typeof v.roster_too_large !== "boolean" || typeof v.attendance_current !== "boolean" || !integer(v.marked_count, 0, 200) || (v.roster_too_large ? v.roster_size !== null : !integer(v.roster_size, 0, 200)))
    return null;
  if (v.attendance_current && (v.sheet_version === 0 || v.roster_too_large))
    return null;
  if (typeof v.roster_size === "number" && v.marked_count > v.roster_size)
    return null;
  return { id: id(v.id), batchId: id(v.batch_id), batchName: v.batch_name, courseName: v.course_name, startsAt: v.starts_at, endsAt: v.ends_at, status: v.status, version: v.version, sheetVersion: v.sheet_version, rosterSize: v.roster_size as number | null, rosterTooLarge: v.roster_too_large, markedCount: v.marked_count, attendanceCurrent: v.attendance_current };
}
export function decodeSessionCursor(v: unknown): SessionCursor | null {
  return object(v) && timestamp(v.starts_at) && uuid(v.id) ? { startsAt: v.starts_at, id: id(v.id) } : null;
}
export function decodeTodaySessions(v: unknown): TodayPage | null {
  if (!object(v) || !date(v.date) || !zone(v.time_zone) || !timestamp(v.server_now))
    return null;
  const sessions = bounded(v.sessions, 50, decodeSession, s => s.id);
  const next = v.next === null ? null : decodeSessionCursor(v.next);
  if (!sessions || !increasing(sessions, sessionOrder) || sessions.some(s => localDate(v.time_zone as string, new Date(s.startsAt)) !== v.date) || (v.next !== null && (!next || sessions.length !== 50 || next.id !== sessions.at(-1)?.id || next.startsAt !== sessions.at(-1)?.startsAt)))
    return null;
  return { date: v.date, timeZone: v.time_zone, serverNow: v.server_now, sessions, next };
}
export function localDate(timeZone: string, now = new Date()): string {
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone, year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(now);
  return ["year", "month", "day"].map(k => parts.find(p => p.type === k)!.value).join("-");
}
export function dateStrip(selected: string): string[] {
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(`${selected}T12:00:00Z`);
    d.setUTCDate(d.getUTCDate() + i - 3);
    return d.toISOString().slice(0, 10);
  }).filter(date);
}
