"use server";

import { createClient } from "@/lib/supabase/server";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const isId = (value: unknown): value is string => typeof value === "string" && UUID.test(value);
type Details = { intentId: string; priorIntentId: string | null; requestId: string | null; courseName: string; batchName: string };
type Result =
  | { ok: false; error: string }
  | { ok: true; state: "unknown" }
  | ({ ok: true; state: "pending" } & Details)
  | ({ ok: true; state: "completed"; courseId: string; batchId: string; acknowledged: boolean } & Details);

export async function recoverCurrentClassSetup(input: unknown): Promise<Result> {
  if (process.env.PARENTPLUS_ENABLE_CLASS_SETUP !== "true") return { ok: false, error: "Class setup is not available." };
  if (!input || typeof input !== "object" || Array.isArray(input)) return { ok: false, error: "Check the recovery details." };
  const value = input as Record<string, unknown>;
  if (!isId(value.workspaceId) || !isId(value.expectedActorId)) return { ok: false, error: "Check the recovery details." };
  const failure = { ok: false, error: "Unable to recover class setup." } as const;
  try {
    const client = await createClient();
    const { data: identity, error: identityError } = await client.auth.getUser();
    const actorId = identity.user?.id;
    if (identityError || !isId(actorId)) return { ok: false, error: "Please sign in to continue." };
    if (actorId.toLowerCase() !== value.expectedActorId.toLowerCase()) return { ok: false, error: "Your account has changed. Restart class setup." };
    const { data, error } = await client.rpc("app_current_class_setup", { p_workspace_id: value.workspaceId });
    if (error || !Array.isArray(data) || data.length !== 1 || !data[0] || typeof data[0] !== "object" || Array.isArray(data[0])) return failure;
    const row = data[0] as Record<string, unknown>;
    if (row.state === "unknown") {
      const fields = [row.intent_id,row.prior_intent_id,row.request_id,row.course_name,row.batch_name,row.course_id,row.batch_id,row.acknowledged];
      return fields.every((field) => field === null) ? { ok: true, state: "unknown" } : failure;
    }
    const pairValid = (row.prior_intent_id === null && row.request_id === null) || (isId(row.prior_intent_id) && isId(row.request_id));
    if (!isId(row.intent_id) || !pairValid || typeof row.course_name !== "string" || !row.course_name.trim() || row.course_name.length > 120
        || typeof row.batch_name !== "string" || !row.batch_name.trim() || row.batch_name.length > 120) return failure;
    const details: Details = { intentId: row.intent_id, priorIntentId: row.prior_intent_id as string | null, requestId: row.request_id as string | null, courseName: row.course_name, batchName: row.batch_name };
    if (row.state === "pending" && row.course_id === null && row.batch_id === null && row.acknowledged === false) return { ok: true, state: "pending", ...details };
    if (row.state === "completed" && isId(row.course_id) && isId(row.batch_id) && typeof row.acknowledged === "boolean") return { ok: true, state: "completed", ...details, courseId: row.course_id, batchId: row.batch_id, acknowledged: row.acknowledged };
    return failure;
  } catch { return failure; }
}
