"use server";
import { createClient } from "@/lib/supabase/server";
import { isAuthApiError, isAuthSessionMissingError } from "@supabase/supabase-js";
import { canonicalSignalPayload, decodeRequestStatus, type RequestStatus, type Result, type SignalPayload } from "@/modules/attendance/contracts";
import { date, exact, id, object, sessionOrder, timestamp, uuid } from "@/modules/attendance/validation";
import { decodeAcademies, type AcademyPage } from "@/modules/today/contracts";
import { decodeParentBatches, decodeParentChildren, decodeParentItems, decodeParentSessions, decodeParentWeek, decodeSignalReceipt, itemOrder, mondayOf, type ParentBatchPage, type ParentChild, type ParentItemPage, type ParentSessionPage, type ParentWeek, type SignalReceipt } from "@/modules/parent-feed/contracts";
const invalid = { ok: false, kind: "invalid" } as const;
async function call<T>(actor: unknown, rpc: string, args: Record<string, unknown>, decode: (value: unknown) => T | null): Promise<Result<T>> {
  if (!uuid(actor)) return invalid;
  try {
    const client = await createClient(); const { data: auth, error: authError } = await client.auth.getUser();
    if (authError) {
      const denied = isAuthSessionMissingError(authError) || (isAuthApiError(authError) && [400, 401, 403].includes(authError.status) && ["bad_jwt", "no_authorization", "user_not_found", "user_banned", "session_not_found", "session_expired"].includes(authError.code ?? ""));
      return { ok: false, kind: denied ? "forbidden" : "unknown" };
    }
    if (!uuid(auth.user?.id) || id(auth.user.id) !== id(actor)) return { ok: false, kind: "forbidden" };
    const { data, error } = await client.rpc(rpc, args);
    if (error) return { ok: false, kind: error.code === "22023" ? "invalid" : error.code === "42501" ? "forbidden" : ["40001", "23505"].includes(error.code) ? "conflict" : "unknown" };
    const result = decode(data); return result === null ? { ok: false, kind: "unknown" } : { ok: true, data: result };
  } catch { return { ok: false, kind: "unknown" }; }
}
export async function listParentChildren(actor: unknown): Promise<Result<ParentChild[]>> {
  if (!uuid(actor)) return invalid;
  if (process.env.PARENTPLUS_ENABLE_PARENT_CHILD_LIST !== "true") return { ok: false, kind: "forbidden" };
  return call(actor, "app_list_created_children", {}, decodeParentChildren);
}
export async function listParentAcademies(actor: unknown, input: unknown): Promise<Result<AcademyPage>> {
  if (!object(input) || !exact(input, ["childId", "after"]) || !uuid(input.childId) || !(input.after === null || uuid(input.after))) return invalid;
  const after = input.after === null ? null : id(input.after);
  return call(actor, "app_parent_academies", { p_child_id: id(input.childId), p_after: after }, v => { const p = decodeAcademies(v); return p && (!after || p.academies.every(a => a.workspaceId > after)) ? p : null; });
}
export async function listParentBatches(actor: unknown, input: unknown): Promise<Result<ParentBatchPage>> {
  if (!object(input) || !exact(input, ["childId", "workspaceId", "after"]) || !uuid(input.childId) || !uuid(input.workspaceId) || !(input.after === null || uuid(input.after))) return invalid;
  const after = input.after === null ? null : id(input.after);
  return call(actor, "app_parent_batches", { p_child_id: id(input.childId), p_workspace_id: id(input.workspaceId), p_after: after }, v => { const p = decodeParentBatches(v); return p && (!after || p.batches.every(b => b.batchId > after)) ? p : null; });
}
function scope(input: unknown, keys: string[]): input is Record<string, unknown> & { childId: string; workspaceId: string; batchId: string | null } {
  return object(input) && exact(input, keys) && uuid(input.childId) && uuid(input.workspaceId) && (input.batchId === null || uuid(input.batchId));
}
export async function listParentSessions(actor: unknown, input: unknown): Promise<Result<ParentSessionPage>> {
  if (!scope(input, ["childId", "workspaceId", "date", "batchId", "after"]) || !date(input.date)) return invalid;
  const after = input.after;
  if (after !== null && (!object(after) || !exact(after, ["startsAt", "id"]) || !timestamp(after.startsAt) || !uuid(after.id))) return invalid;
  return call(actor, "app_parent_sessions", { p_child_id: id(input.childId), p_workspace_id: id(input.workspaceId), p_date: input.date, p_batch_id: input.batchId === null ? null : id(input.batchId), p_after_start: after === null ? null : (after as { startsAt: string }).startsAt, p_after_id: after === null ? null : id((after as { id: string }).id) }, v => {
    const p = decodeParentSessions(v);
    return p && p.date === input.date && p.sessions.every(s => (!input.batchId || s.batchId === id(input.batchId)) && (!s.ownLatestSignal || (s.ownLatestSignal.childId === id(input.childId) && s.ownLatestSignal.actorId === id(actor as string))) && (after === null || sessionOrder(s, after as { startsAt: string; id: string }) > 0)) ? p : null;
  });
}
export async function listParentItems(actor: unknown, input: unknown): Promise<Result<ParentItemPage>> {
  if (!scope(input, ["childId", "workspaceId", "batchId", "before"])) return invalid;
  const before = input.before;
  if (before !== null && (!object(before) || !exact(before, ["createdAt", "id"]) || !timestamp(before.createdAt) || !uuid(before.id))) return invalid;
  return call(actor, "app_parent_items", { p_child_id: id(input.childId), p_workspace_id: id(input.workspaceId), p_batch_id: input.batchId === null ? null : id(input.batchId), p_before_created: before === null ? null : (before as { createdAt: string }).createdAt, p_before_id: before === null ? null : id((before as { id: string }).id) }, v => {
    const p = decodeParentItems(v);
    return p && p.items.every(i => i.childId === id(input.childId) && (!input.batchId || i.classId === id(input.batchId)) && (before === null || itemOrder(i, before as { createdAt: string; id: string }) < 0)) ? p : null;
  });
}
export async function loadParentWeek(actor: unknown, input: unknown): Promise<Result<ParentWeek>> {
  if (!scope(input, ["childId", "workspaceId", "batchId", "weekStart"]) || !date(input.weekStart) || mondayOf(input.weekStart) !== input.weekStart) return invalid;
  return call(actor, "app_parent_attendance_week", { p_child_id: id(input.childId), p_workspace_id: id(input.workspaceId), p_week_start: input.weekStart, p_batch_id: input.batchId === null ? null : id(input.batchId) }, v => { const p = decodeParentWeek(v); return p && p.weekStart === input.weekStart && p.rows.every(r => !input.batchId || r.batchId === id(input.batchId)) ? p : null; });
}
function writeInput(v: unknown): { requestId: string; payload: SignalPayload } | null {
  if (!object(v) || !exact(v, ["requestId", "payload"]) || !uuid(v.requestId)) return null;
  const payload = canonicalSignalPayload(v.payload); return payload ? { requestId: id(v.requestId), payload } : null;
}
function matchingReceipt(v: unknown, write: { requestId: string; payload: SignalPayload }) {
  const r = decodeSignalReceipt(v), p = write.payload;
  return r && r.requestId === write.requestId && r.childId === p.child_id && r.sessionId === p.session_id && r.type === p.type && r.reason === p.reason ? r : null;
}
export async function sendParentSignal(actor: unknown, input: unknown): Promise<Result<SignalReceipt>> {
  const write = writeInput(input); if (!write) return invalid; const p = write.payload;
  return call(actor, "app_send_parent_signal", { p_child_id: p.child_id, p_workspace_id: p.workspace_id, p_session_id: p.session_id, p_expected_session_version: p.expected_session_version, p_type: p.type, p_reason: p.reason, p_request_id: write.requestId }, v => matchingReceipt(v, write));
}
export async function parentSignalRequestStatus(actor: unknown, input: unknown): Promise<Result<RequestStatus<SignalReceipt>>> {
  const write = writeInput(input); if (!write) return invalid; const p = write.payload;
  return call(actor, "app_parent_signal_request_status", { p_child_id: p.child_id, p_workspace_id: p.workspace_id, p_session_id: p.session_id, p_request_id: write.requestId, p_payload: p }, v => decodeRequestStatus(v, r => matchingReceipt(r, write)));
}
