"use server";

import { createClient } from "@/lib/supabase/server";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

type Result =
  | { ok: true; courseId: string; batchId: string }
  | { ok: false; error: string };

export async function createClassSetup(input: unknown): Promise<Result> {
  if (process.env.PARENTPLUS_ENABLE_CLASS_SETUP !== "true") {
    return { ok: false, error: "Class setup is not available." };
  }
  if (!input || typeof input !== "object") {
    return { ok: false, error: "Check the class setup details." };
  }
  const value = input as Record<string, unknown>;
  if (typeof value.expectedActorId !== "string" || !UUID.test(value.expectedActorId)
      || typeof value.workspaceId !== "string" || !UUID.test(value.workspaceId)
      || typeof value.requestId !== "string" || !UUID.test(value.requestId)
      || typeof value.courseName !== "string" || typeof value.batchName !== "string") {
    return { ok: false, error: "Check the class setup details." };
  }
  const course = value.courseName.trim();
  const batch = value.batchName.trim();
  if (!course || !batch || course.length > 120 || batch.length > 120) {
    return { ok: false, error: "Check the class setup details." };
  }
  try {
    const client = await createClient();
    const { data: identity, error: identityError } = await client.auth.getUser();
    if (identityError || !identity.user || typeof identity.user.id !== "string" || !identity.user.id) {
      return { ok: false, error: "Please sign in to continue." };
    }
    if (identity.user.id.toLowerCase() !== value.expectedActorId.toLowerCase()) {
      return { ok: false, error: "Your account has changed. Restart class setup." };
    }
    const { data, error } = await client.rpc("create_course_and_batch", {
      p_workspace_id: value.workspaceId,
      p_request_id: value.requestId,
      p_course_name: course,
      p_batch_name: batch,
    });
    if (error || !Array.isArray(data) || data.length !== 1) {
      return { ok: false, error: "Unable to complete class setup." };
    }
    const result = data[0];
    if (!result || typeof result.course_id !== "string" || !UUID.test(result.course_id)
        || typeof result.batch_id !== "string" || !UUID.test(result.batch_id)) {
      return { ok: false, error: "Unable to complete class setup." };
    }
    return { ok: true, courseId: result.course_id, batchId: result.batch_id };
  } catch {
    return { ok: false, error: "Unable to complete class setup." };
  }
}
