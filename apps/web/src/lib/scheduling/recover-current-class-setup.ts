"use server";

import { createClient } from "@/lib/supabase/server";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const isId = (value: unknown): value is string => typeof value === "string" && UUID.test(value);
type WeeklySchedule = { timeZone: string; startDate: string; startTime: string; endDate: string; durationMinutes: number; occurrenceCount: number };
type Details = { intentId: string; priorIntentId: string | null; requestId: string | null; courseName: string; batchName: string };
type Result =
  | { ok: false; error: string }
  | { ok: true; state: "unknown" }
  | ({ ok: true; state: "pending"; schedule: null } & Details)
  | ({ ok: true; state: "completed"; courseId: string; batchId: string; acknowledged: boolean; schedule: WeeklySchedule | null } & Details);

function recoverSchedule(row: Record<string, unknown>): WeeklySchedule | null | false {
  const values = [row.time_zone, row.start_date, row.start_time, row.end_date, row.duration_minutes, row.occurrence_count];
  if (values.every((value) => value === null)) return null;
  if (typeof row.time_zone !== "string" || !row.time_zone.trim()
      || typeof row.start_date !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(row.start_date)
      || typeof row.start_time !== "string" || !/^(?:[01]\d|2[0-3]):[0-5]\d:00(?:\.0+)?$/.test(row.start_time)
      || typeof row.end_date !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(row.end_date)
      || typeof row.duration_minutes !== "number" || !Number.isInteger(row.duration_minutes) || row.duration_minutes < 1 || row.duration_minutes > 1440
      || typeof row.occurrence_count !== "number" || !Number.isInteger(row.occurrence_count) || row.occurrence_count < 1 || row.occurrence_count > 104) return false;
  return { timeZone: row.time_zone, startDate: row.start_date, startTime: row.start_time.slice(0, 5), endDate: row.end_date, durationMinutes: row.duration_minutes, occurrenceCount: row.occurrence_count };
}

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
    if (actorId.toLowerCase() !== value.expectedActorId.toLowerCase()) return { ok: false, error: "Your account has changed. Sign in to the original account before continuing." };
    const { data, error } = await client.rpc("app_current_class_setup_v2", { p_workspace_id: value.workspaceId });
    if (error || !Array.isArray(data) || data.length !== 1 || !data[0] || typeof data[0] !== "object" || Array.isArray(data[0])) return failure;
    const row = data[0] as Record<string, unknown>;
    if (row.state === "unknown") {
      const fields = [row.intent_id,row.prior_intent_id,row.request_id,row.course_name,row.batch_name,row.course_id,row.batch_id,row.acknowledged,row.time_zone,row.start_date,row.start_time,row.end_date,row.duration_minutes,row.occurrence_count];
      return fields.every((field) => field === null) ? { ok: true, state: "unknown" } : failure;
    }
    const pairValid = (row.prior_intent_id === null && row.request_id === null) || (isId(row.prior_intent_id) && isId(row.request_id));
    if (!isId(row.intent_id) || !pairValid || typeof row.course_name !== "string" || !row.course_name.trim() || row.course_name.length > 120
        || typeof row.batch_name !== "string" || !row.batch_name.trim() || row.batch_name.length > 120) return failure;
    const details: Details = { intentId: row.intent_id, priorIntentId: row.prior_intent_id as string | null, requestId: row.request_id as string | null, courseName: row.course_name, batchName: row.batch_name };
    if (row.state === "pending" && row.course_id === null && row.batch_id === null && row.acknowledged === false && recoverSchedule(row) === null) return { ok: true, state: "pending", ...details, schedule: null };
    if (row.state === "completed" && isId(row.course_id) && isId(row.batch_id) && typeof row.acknowledged === "boolean") {
      const schedule = recoverSchedule(row);
      if (schedule !== false) return { ok: true, state: "completed", ...details, courseId: row.course_id, batchId: row.batch_id, acknowledged: row.acknowledged, schedule };
    }
    return failure;
  } catch { return failure; }
}
