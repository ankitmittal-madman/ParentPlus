"use server";
import { createClient } from "@/lib/supabase/server";
import { isId, isName, rows, type Result } from "@/modules/families/contracts";
import type {
  Batch,
  Candidate,
  Enrollment,
  EnrollmentState,
  SavedEnrollment,
  ParentEnrollment,
  SaveInput,
  ChangeInput,
  MutationResult,
} from "@/modules/enrollments/contracts";

function state(value: unknown): value is EnrollmentState {
  return (
    typeof value === "string" &&
    [
      "pending",
      "active",
      "paused",
      "completed",
      "withdrawn",
      "cancelled",
    ].includes(value)
  );
}
function version(value: unknown): value is number {
  return (
    typeof value === "number" &&
    Number.isSafeInteger(value) &&
    value > 0 &&
    value <= 2147483647
  );
}
function saved(r: Record<string, unknown>): SavedEnrollment | null {
  return isId(r.enrollment_id) && state(r.status) && version(r.version)
    ? { id: r.enrollment_id, status: r.status, version: r.version }
    : null;
}
async function read<T extends { id: string }>(
  actor: unknown,
  rpc: string,
  args: Record<string, unknown>,
  max: number,
  project: (r: Record<string, unknown>) => T | null,
  allowConflict = false,
): Promise<MutationResult<T[]>> {
  if (!isId(actor)) return { ok: false };
  try {
    const client = await createClient();
    const { data: session, error: authError } = await client.auth.getUser();
    if (
      authError ||
      !isId(session.user?.id) ||
      session.user.id.toLowerCase() !== actor.toLowerCase()
    )
      return { ok: false };
    const { data, error } = await client.rpc(rpc, args);
    if (error) {
      return allowConflict && ["40001", "23505"].includes(error.code)
        ? { ok: false, conflict: true }
        : { ok: false };
    }
    const seen = new Set<string>();
    const result = rows(data, max, (r) => {
      const item = project(r);
      if (!item || seen.has(item.id.toLowerCase())) return null;
      seen.add(item.id.toLowerCase());
      return item;
    });
    return result ? { ok: true, data: result } : { ok: false };
  } catch {
    return { ok: false };
  }
}
async function write(
  actor: unknown,
  rpc: string,
  args: Record<string, unknown>,
): Promise<MutationResult<SavedEnrollment>> {
  const result = await read(actor, rpc, args, 1, saved, true);
  if (!result.ok) return result;
  return result.data.length === 1
    ? { ok: true, data: result.data[0] }
    : { ok: false };
}
export async function listEnrollmentBatches(
  actor: unknown,
  workspace: unknown,
): Promise<Result<Batch[]>> {
  if (!isId(workspace)) return { ok: false };
  return read(
    actor,
    "app_enrollment_batches",
    { p_workspace_id: workspace },
    Number.MAX_SAFE_INTEGER,
    (r) =>
      isId(r.batch_id) && isName(r.batch_name) && isName(r.course_name)
        ? { id: r.batch_id, name: r.batch_name, courseName: r.course_name }
        : null,
  );
}
export async function listEnrollmentCandidates(
  actor: unknown,
  workspace: unknown,
  after: unknown,
): Promise<Result<Candidate[]>> {
  if (!isId(workspace) || (after !== null && !isId(after)))
    return { ok: false };
  return read(
    actor,
    "app_enrollment_candidates",
    { p_workspace_id: workspace, p_after: after },
    50,
    (r) =>
      isId(r.child_id) && isName(r.child_name)
        ? { id: r.child_id, name: r.child_name }
        : null,
  );
}
export async function listBatchEnrollments(
  actor: unknown,
  workspace: unknown,
  batch: unknown,
  after: unknown,
): Promise<Result<Enrollment[]>> {
  if (!isId(workspace) || !isId(batch) || (after !== null && !isId(after)))
    return { ok: false };
  return read(
    actor,
    "app_batch_enrollments",
    { p_workspace_id: workspace, p_batch_id: batch, p_after: after },
    50,
    (r) => {
      const s = saved(r);
      return s && isId(r.child_id) && isName(r.child_name)
        ? { ...s, childId: r.child_id, childName: r.child_name }
        : null;
    },
  );
}
export async function saveEnrollment(
  actor: unknown,
  input: SaveInput,
): Promise<MutationResult<SavedEnrollment>> {
  if (
    !input ||
    !isId(input.workspaceId) ||
    !isId(input.batchId) ||
    !isId(input.childId) ||
    !isId(input.requestId)
  )
    return { ok: false };
  return write(actor, "app_save_enrollment", {
    p_workspace_id: input.workspaceId,
    p_batch_id: input.batchId,
    p_child_id: input.childId,
    p_request_id: input.requestId,
  });
}
export async function changeEnrollment(
  actor: unknown,
  input: ChangeInput,
): Promise<MutationResult<SavedEnrollment>> {
  if (
    !input ||
    !isId(input.enrollmentId) ||
    !isId(input.requestId) ||
    !version(input.expectedVersion)
  )
    return { ok: false };
  const needsReason = input.status === "paused" || input.status === "withdrawn";
  if (
    needsReason
      ? !["temporary_break", "schedule_change", "other"].includes(
          input.reason as string,
        )
      : !["active", "completed"].includes(input.status) || input.reason !== null
  )
    return { ok: false };
  return write(actor, "app_change_enrollment", {
    p_enrollment_id: input.enrollmentId,
    p_status: input.status,
    p_expected_version: input.expectedVersion,
    p_reason: input.reason,
    p_request_id: input.requestId,
  });
}
export async function listParentEnrollments(
  actor: unknown,
  child: unknown,
): Promise<Result<ParentEnrollment[]>> {
  if (!isId(child)) return { ok: false };
  return read(
    actor,
    "app_parent_enrollments",
    { p_child_id: child },
    100,
    (r) => {
      const s = saved(r);
      return s &&
        isName(r.academy_name) &&
        isName(r.batch_name) &&
        isName(r.course_name)
        ? {
            ...s,
            academyName: r.academy_name,
            batchName: r.batch_name,
            courseName: r.course_name,
          }
        : null;
    },
  );
}
