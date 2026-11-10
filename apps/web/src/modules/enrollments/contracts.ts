import type { Result } from "@/modules/families/contracts";

/** Only structured, definitive DB write rejections carry this redacted discriminator. */
export type MutationResult<T> = Result<T> | { ok: false; conflict: true };

export type EnrollmentState =
  "pending" | "active" | "paused" | "completed" | "withdrawn" | "cancelled";
export type EnrollmentReason = "temporary_break" | "schedule_change" | "other";
export type Batch = { id: string; name: string; courseName: string };
export type Candidate = { id: string; name: string };
export type SavedEnrollment = {
  id: string;
  status: EnrollmentState;
  version: number;
};
export type Enrollment = SavedEnrollment & {
  childId: string;
  childName: string;
};
export type ParentEnrollment = SavedEnrollment & {
  academyName: string;
  batchName: string;
  courseName: string;
};
export type SaveInput = {
  workspaceId: string;
  batchId: string;
  childId: string;
  requestId: string;
};
export type ChangeInput = {
  enrollmentId: string;
  status: EnrollmentState;
  expectedVersion: number;
  reason: EnrollmentReason | null;
  requestId: string;
};
