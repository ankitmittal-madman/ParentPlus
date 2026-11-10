import { expect, it } from "vitest";
import { decodeParentSessions, decodeParentItems, decodeParentWeek, decodeParentBatches, safeParentAction, mondayOf } from "./contracts";
const a = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", b = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", t = "2026-11-10T12:00:00Z";
const item = { id: a, child_id: a, class_id: b, type: "future_type", schema_version: 2, priority: 0, created_at: t, expires_at: null, payload: { title: "Hello", extra: true } };
const session = { id: b, batch_id: b, batch_name: "Art", course_name: "Painting", starts_at: t, ends_at: "2026-11-10T13:00:00Z", status: "scheduled", version: 1, enrollment_id: a, enrollment_status: "active", attendance: { status: "late", confirmed_at: t }, own_latest_signal: { id: a, child_id: a, actor_id: b, type: "running_late", reason: null, created_at: t }, can_signal: true };
it("decodes dedicated batch IDs and retained enrolment states without relationship aliases", () => {
  expect(decodeParentBatches({ batches: [{ batch_id: b, batch_name: "Art", course_name: "Painting", enrollment_id: a, enrollment_status: "paused", private_note: "hidden" }], next_after: null })).toEqual({ batches: [{ batchId: b, batchName: "Art", courseName: "Painting", enrollmentId: a, enrollmentStatus: "paused" }], nextAfter: null });
  expect(decodeParentBatches({ batches: [{ id: b, class_ids: [a] }], next_after: null })).toBeNull();
});
it("validates parent session bounds chronology local date eligibility and own report projection", () => {
  const page = { date: "2026-11-10", time_zone: "Asia/Kolkata", server_now: t, sessions: [session], next: null };
  expect(decodeParentSessions(page)?.sessions[0]).toMatchObject({ batchId: b, attendance: { status: "late", confirmedAt: t }, canSignal: true });
  for (const bad of [{ sessions: [session, session] }, { sessions: [{ ...session, ends_at: t }] }, { date: "2026-11-11" }, { sessions: [{ ...session, enrollment_status: "paused" }] }, { sessions: [{ ...session, status: "cancelled" }] }, { sessions: [{ ...session, attendance: { status: "invented", confirmed_at: t } }] }, { sessions: Array(51).fill(session) }, { next: { starts_at: t } }]) expect(decodeParentSessions({ ...page, ...bad })).toBeNull();
});
it("retains unknown typed envelopes while rejecting malformed bounds duplicates and cursors", () => {
  expect(decodeParentItems({ items: [item], next: null })?.items[0]).toMatchObject({ type: "future_type", schemaVersion: 2, childId: a });
  for (const bad of [{ items: [{ ...item, priority: 101 }] }, { items: [{ ...item, payload: [] }] }, { items: [item, item] }, { items: [{ ...item, schema_version: 0 }] }, { next: { created_at: t, id: a } }]) expect(decodeParentItems({ items: [item], next: null, ...bad })).toBeNull();
});
it("orders feed timestamps at full UTC microsecond precision and rejects ascending pages", () => {
  const newer = { ...item, created_at: "2026-11-10T12:00:00.000002+00:00" }, older = { ...item, id: b, created_at: "2026-11-10T12:00:00.000001Z" };
  expect(decodeParentItems({ items: [newer, older], next: null })?.items).toHaveLength(2); expect(decodeParentItems({ items: [older, newer], next: null })).toBeNull();
});
it("keeps exact weekly counts independent of capped detail and validates Monday window", () => {
  const page = { week_start: "2026-11-09", time_zone: "Asia/Kolkata", attended_count: 61, recorded_count: 70, rows: Array.from({ length: 50 }, (_, i) => ({ session_id: `00000000-0000-4000-8000-${String(i).padStart(12, "0")}`, batch_id: b, batch_name: "Art", date: "2026-11-10", status: "present", confirmed_at: t })), has_more: true };
  expect(decodeParentWeek(page)?.attendedCount).toBe(61);
  for (const bad of [{ week_start: "2026-11-10" }, { attended_count: 71 }, { has_more: false }, { rows: [{ ...page.rows[0], date: "2026-11-16" }] }]) expect(decodeParentWeek({ ...page, ...bad })).toBeNull(); expect(mondayOf("2026-11-15")).toBe("2026-11-09");
});
it("rebuilds only exact own-child parent actions with bounded plain labels", () => {
  expect(safeParentAction({ label: "Open", href: "/parent" }, a)).toEqual({ label: "Open", href: "/parent" }); expect(safeParentAction({ label: "<b>Profile</b>", href: `/parent/children?child=${a}` }, a)).toEqual({ label: "<b>Profile</b>", href: `/parent/children?child=${a}` }); expect(safeParentAction({ label: "x".repeat(81), href: "/parent" }, a)).toBeNull();
});
it("denies external encoded traversal control fragment duplicate and other-child action tricks", () => {
  for (const href of ["https://evil.test/parent", "//evil.test/parent", "javascript:alert(1)", "data:text/html,x", "file:///parent", "/%70arent", "/parent%2fchildren", "/parent/../parent", "/parent\\children", "/parent\n", "/parent#x", "/parent?", "/parent/", `/parent?child=${b}`, `/parent?child=${a}&child=${a}`, `/parent?child=${a}&x=1`, `/parent?child=%61${a.slice(1)}`, "/parent?x=1", " /parent", "/parent/children/../../parent"]) expect(safeParentAction({ label: "Open", href }, a)).toBeNull();
  for (const value of [null, [], [{ label: "x", href: "/parent" }], { label: "", href: "/parent" }, { label: "x", href: 5 }]) expect(safeParentAction(value, a)).toBeNull();
});
it("requires exact fifty-row continuation anchors for dedicated batches sessions and feed", () => {
  const identifier = (n: number) => `00000000-0000-4000-8000-${String(n).padStart(12, "0")}`;
  const batches = Array.from({ length: 50 }, (_, i) => ({ batch_id: identifier(i), batch_name: "Art", course_name: "Painting", enrollment_id: identifier(i), enrollment_status: "active" }));
  expect(decodeParentBatches({ batches, next_after: identifier(49) })?.nextAfter).toBe(identifier(49)); expect(decodeParentBatches({ batches, next_after: identifier(48) })).toBeNull(); expect(decodeParentBatches({ batches: [...batches, { ...batches[0], batch_id: identifier(50) }], next_after: null })).toBeNull();
  const sessions = Array.from({ length: 50 }, (_, i) => ({ ...session, id: identifier(i) })); const page = { date: "2026-11-10", time_zone: "UTC", server_now: t, sessions, next: { starts_at: t, id: identifier(49) } }; expect(decodeParentSessions(page)?.sessions).toHaveLength(50); expect(decodeParentSessions({ ...page, next: { starts_at: t, id: identifier(48) } })).toBeNull();
  const items = Array.from({ length: 50 }, (_, i) => ({ ...item, id: identifier(50 - i) })); expect(decodeParentItems({ items, next: { created_at: t, id: identifier(1) } })?.items).toHaveLength(50); expect(decodeParentItems({ items, next: { created_at: t, id: identifier(2) } })).toBeNull();
});
