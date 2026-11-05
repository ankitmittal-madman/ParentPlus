"use server";

import { createClient } from "@/lib/supabase/server";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const isId = (value: unknown): value is string => typeof value === "string" && UUID.test(value);
type Result =
  | { ok: false; error: string }
  | { ok: true; operation: "reserve"; intentId: string; disposition: "created" | "existing"; state: "pending" | "completed" | "acknowledged" }
  | { ok: true; operation: "advance"; intentId: string }
  | { ok: true; operation: "complete"; courseId: string; batchId: string }
  | { ok: true; operation: "acknowledge" };

export async function runClassSetupOperation(input: unknown): Promise<Result> {
  if (process.env.PARENTPLUS_ENABLE_CLASS_SETUP !== "true") return { ok: false, error: "Class setup is not available." };
  const invalid = { ok: false, error: "Check the class setup details." } as const;
  if (!input || typeof input !== "object" || Array.isArray(input)) return invalid;
  const value = input as Record<string, unknown>;
  const { operation, workspaceId, expectedActorId } = value;
  if (!isId(workspaceId) || !isId(expectedActorId) || typeof operation !== "string" || !["reserve", "complete", "acknowledge", "advance"].includes(operation)) return invalid;
  let courseName = "", batchName = "";
  if (operation === "reserve" || operation === "advance") {
    if (typeof value.courseName !== "string" || typeof value.batchName !== "string") return invalid;
    courseName = value.courseName.trim(); batchName = value.batchName.trim();
    if (!courseName || !batchName || courseName.length > 120 || batchName.length > 120) return invalid;
  }
  if ((operation === "complete" || operation === "acknowledge") && !isId(value.intentId)) return invalid;
  if (operation === "advance" && (!isId(value.priorIntentId) || !isId(value.requestId))) return invalid;
  const uncertain = { ok: false, error: "Unable to confirm class setup. Check its status before retrying." } as const;
  try {
    const client = await createClient();
    const { data: identity, error: identityError } = await client.auth.getUser();
    const actorId = identity.user?.id;
    if (identityError || !isId(actorId)) return { ok: false, error: "Please sign in to continue." };
    if (actorId.toLowerCase() !== expectedActorId.toLowerCase()) return { ok: false, error: "Your account has changed. Sign in to the original account before continuing." };
    if (operation === "reserve") {
      const { data, error } = await client.rpc("app_begin_class_setup", { p_workspace_id: workspaceId, p_course_name: courseName, p_batch_name: batchName });
      if (error || !Array.isArray(data) || data.length !== 1 || !data[0] || typeof data[0] !== "object" || Array.isArray(data[0])) return uncertain;
      const row = data[0] as Record<string, unknown>;
      if (!isId(row.intent_id) || (row.disposition !== "created" && row.disposition !== "existing")
          || (row.state !== "pending" && row.state !== "completed" && row.state !== "acknowledged")
          || (row.disposition === "created" && row.state !== "pending")) return uncertain;
      return { ok: true, operation, intentId: row.intent_id, disposition: row.disposition, state: row.state };
    }
    if (operation === "advance") {
      const { data, error } = await client.rpc("app_advance_class_setup", { p_workspace_id: workspaceId, p_prior_intent_id: value.priorIntentId, p_request_id: value.requestId, p_course_name: courseName, p_batch_name: batchName });
      return !error && isId(data) ? { ok: true, operation, intentId: data } : uncertain;
    }
    if (operation === "acknowledge") {
      const { data, error } = await client.rpc("app_acknowledge_class_setup", { p_workspace_id: workspaceId, p_intent_id: value.intentId });
      return !error && data === true ? { ok: true, operation } : uncertain;
    }
    if (operation === "complete") {
      const { data, error } = await client.rpc("app_complete_class_setup", { p_workspace_id: workspaceId, p_intent_id: value.intentId });
      if (error || !Array.isArray(data) || data.length !== 1 || !data[0] || typeof data[0] !== "object" || Array.isArray(data[0])) return uncertain;
      const row = data[0] as Record<string, unknown>;
      return isId(row.course_id) && isId(row.batch_id) ? { ok: true, operation, courseId: row.course_id, batchId: row.batch_id } : uncertain;
    }
    return invalid;
  } catch { return uncertain; }
}
