"use server";

import { createClient } from "@/lib/supabase/server";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const isId = (value: unknown): value is string => typeof value === "string" && UUID.test(value);
type Result =
  | { ok: false; error: string }
  | { ok: true; operation: "generation"; generation: number; available: boolean }
  | { ok: true; operation: "reserve"; intentId: string; disposition: "created" | "existing"; state: "pending" | "completed" | "acknowledged"; generation: number }
  | { ok: true; operation: "advance"; intentId: string }
  | { ok: true; operation: "complete"; courseId: string; batchId: string; timeZone: string; startDate: string; startTime: string; endDate: string; durationMinutes: number; occurrenceCount: number }
  | { ok: true; operation: "acknowledge" };

export async function runClassSetupOperation(input: unknown): Promise<Result> {
  if (process.env.PARENTPLUS_ENABLE_CLASS_SETUP !== "true") return { ok: false, error: "Class setup is not available." };
  const invalid = { ok: false, error: "Check the class setup details." } as const;
  if (!input || typeof input !== "object" || Array.isArray(input)) return invalid;
  const value = input as Record<string, unknown>;
  const { operation, workspaceId, expectedActorId } = value;
  if (!isId(workspaceId) || !isId(expectedActorId) || typeof operation !== "string" || !["generation", "reserve", "complete", "acknowledge", "advance"].includes(operation)) return invalid;
  let courseName = "", batchName = "";
  if (operation === "reserve" || operation === "advance") {
    if (typeof value.courseName !== "string" || typeof value.batchName !== "string") return invalid;
    courseName = value.courseName.trim(); batchName = value.batchName.trim();
    if (!courseName || !batchName || courseName.length > 120 || batchName.length > 120) return invalid;
  }
  if (operation === "reserve" && (typeof value.generation !== "number" || !Number.isSafeInteger(value.generation) || value.generation < 1 || !isId(value.requestId))) return invalid;
  if ((operation === "complete" || operation === "acknowledge") && !isId(value.intentId)) return invalid;
  let schedule: Record<string, unknown> | null = null;
  if (operation === "complete") {
    const candidate = value.schedule;
    if (!candidate || typeof candidate !== "object" || Array.isArray(candidate)) return invalid;
    schedule = candidate as Record<string, unknown>;
    if (typeof schedule.timeZone !== "string" || !/^[A-Za-z][A-Za-z0-9_+./-]*$/.test(schedule.timeZone)
        || typeof schedule.startDate !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(schedule.startDate)
        || typeof schedule.startTime !== "string" || !/^([01]\d|2[0-3]):[0-5]\d$/.test(schedule.startTime)
        || typeof schedule.endDate !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(schedule.endDate)
        || typeof schedule.durationMinutes !== "number" || !Number.isInteger(schedule.durationMinutes)
        || schedule.durationMinutes < 1 || schedule.durationMinutes > 1440) return invalid;
  }
  if (operation === "advance" && (!isId(value.priorIntentId) || !isId(value.requestId))) return invalid;
  const uncertain = { ok: false, error: "Unable to confirm class setup. Check its status before retrying." } as const;
  try {
    const client = await createClient();
    const { data: identity, error: identityError } = await client.auth.getUser();
    const actorId = identity.user?.id;
    if (identityError || !isId(actorId)) return { ok: false, error: "Please sign in to continue." };
    if (actorId.toLowerCase() !== expectedActorId.toLowerCase()) return { ok: false, error: "Your account has changed. Sign in to the original account before continuing." };
    if (operation === "generation") {
      const { data, error } = await client.rpc("app_class_setup_generation", { p_workspace_id: workspaceId });
      if (error || !Array.isArray(data) || data.length !== 1 || !data[0] || typeof data[0] !== "object" || Array.isArray(data[0])) return uncertain;
      const row = data[0] as Record<string, unknown>;
      if (!Number.isSafeInteger(row.generation) || Number(row.generation) < 1 || typeof row.available !== "boolean") return uncertain;
      return { ok: true, operation, generation: Number(row.generation), available: row.available };
    }
    if (operation === "reserve") {
      const { data, error } = await client.rpc("app_begin_class_setup_v2", { p_workspace_id: workspaceId, p_expected_generation: value.generation, p_request_id: value.requestId, p_course_name: courseName, p_batch_name: batchName });
      if (error || !Array.isArray(data) || data.length !== 1 || !data[0] || typeof data[0] !== "object" || Array.isArray(data[0])) return uncertain;
      const row = data[0] as Record<string, unknown>;
      if (!isId(row.intent_id) || (row.disposition !== "created" && row.disposition !== "existing")
          || (row.state !== "pending" && row.state !== "completed" && row.state !== "acknowledged")
          || (row.disposition === "created" && row.state !== "pending")
          || row.generation !== value.generation) return uncertain;
      return { ok: true, operation, intentId: row.intent_id, disposition: row.disposition, state: row.state, generation: Number(row.generation) };
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
      const { data, error } = await client.rpc("app_complete_class_setup_weekly", {
        p_workspace_id: workspaceId, p_intent_id: value.intentId,
        p_time_zone: schedule?.timeZone, p_start_date: schedule?.startDate,
        p_start_time: schedule?.startTime, p_end_date: schedule?.endDate,
        p_duration_minutes: schedule?.durationMinutes,
      });
      if (error || !Array.isArray(data) || data.length !== 1 || !data[0] || typeof data[0] !== "object" || Array.isArray(data[0])) return uncertain;
      const row = data[0] as Record<string, unknown>;
      return isId(row.course_id) && isId(row.batch_id) && row.time_zone === schedule?.timeZone
        && row.start_date === schedule?.startDate && typeof row.start_time === "string" && row.start_time.startsWith(schedule?.startTime as string)
        && row.end_date === schedule?.endDate && row.duration_minutes === schedule?.durationMinutes
        && typeof row.occurrence_count === "number" && Number.isInteger(row.occurrence_count) && row.occurrence_count >= 1 && row.occurrence_count <= 104
        ? { ok: true, operation, courseId: row.course_id, batchId: row.batch_id, timeZone: row.time_zone as string, startDate: row.start_date as string, startTime: (row.start_time as string).slice(0, 5), endDate: row.end_date as string, durationMinutes: row.duration_minutes as number, occurrenceCount: row.occurrence_count as number }
        : uncertain;
    }
    return invalid;
  } catch { return uncertain; }
}
