import { beforeEach, expect, it, vi } from "vitest";
const m = vi.hoisted(() => ({
  create: vi.fn(),
  getUser: vi.fn(),
  rpc: vi.fn(),
}));
vi.mock("@/lib/supabase/server", () => ({ createClient: m.create }));
import {
  listEnrollmentBatches,
  listEnrollmentCandidates,
  listBatchEnrollments,
  saveEnrollment,
  changeEnrollment,
  listParentEnrollments,
} from "./actions";
const actor = "11111111-1111-4111-8111-111111111111",
  id = "22222222-2222-4222-8222-222222222222";
const save = { workspaceId: id, batchId: id, childId: id, requestId: id };
const change = {
  enrollmentId: id,
  status: "paused" as const,
  expectedVersion: 2,
  reason: "temporary_break" as const,
  requestId: id,
};
const receipt = { enrollment_id: id, status: "paused", version: 3 };
const cases = [
  {
    call: () => listEnrollmentBatches(actor, id),
    rpc: "app_enrollment_batches",
    args: { p_workspace_id: id },
    row: { batch_id: id, batch_name: "Morning", course_name: "Maths" },
    want: { id, name: "Morning", courseName: "Maths" },
  },
  {
    call: () => listEnrollmentCandidates(actor, id, null),
    rpc: "app_enrollment_candidates",
    args: { p_workspace_id: id, p_after: null },
    row: { child_id: id, child_name: "Asha" },
    want: { id, name: "Asha" },
  },
  {
    call: () => listBatchEnrollments(actor, id, id, null),
    rpc: "app_batch_enrollments",
    args: { p_workspace_id: id, p_batch_id: id, p_after: null },
    row: { ...receipt, child_id: id, child_name: "Asha" },
    want: { id, childId: id, childName: "Asha", status: "paused", version: 3 },
  },
  {
    call: () => saveEnrollment(actor, save),
    rpc: "app_save_enrollment",
    args: {
      p_workspace_id: id,
      p_batch_id: id,
      p_child_id: id,
      p_request_id: id,
    },
    row: receipt,
    want: { id, status: "paused", version: 3 },
    single: true,
  },
  {
    call: () => changeEnrollment(actor, change),
    rpc: "app_change_enrollment",
    args: {
      p_enrollment_id: id,
      p_status: "paused",
      p_expected_version: 2,
      p_reason: "temporary_break",
      p_request_id: id,
    },
    row: receipt,
    want: { id, status: "paused", version: 3 },
    single: true,
  },
  {
    call: () => listParentEnrollments(actor, id),
    rpc: "app_parent_enrollments",
    args: { p_child_id: id },
    row: {
      ...receipt,
      academy_name: "Academy",
      batch_name: "Morning",
      course_name: "Maths",
    },
    want: {
      id,
      academyName: "Academy",
      batchName: "Morning",
      courseName: "Maths",
      status: "paused",
      version: 3,
    },
  },
];
beforeEach(() => {
  vi.resetAllMocks();
  m.create.mockResolvedValue({ auth: { getUser: m.getUser }, rpc: m.rpc });
  m.getUser.mockResolvedValue({ data: { user: { id: actor } }, error: null });
});
type RpcCase = (typeof cases)[number];
async function projects(c: RpcCase) {
  m.rpc.mockResolvedValue({
    data: [{ ...c.row, private_note: "secret" }],
    error: null,
  });
  expect(await c.call()).toEqual({
    ok: true,
    data: c.single ? c.want : [c.want],
  });
  expect(m.rpc).toHaveBeenCalledWith(c.rpc, c.args);
}
async function identity(c: RpcCase) {
  m.getUser.mockResolvedValue({ data: { user: { id } }, error: null });
  expect(await c.call()).toEqual({ ok: false });
  expect(m.rpc).not.toHaveBeenCalled();
  m.getUser.mockResolvedValue({ data: { user: null }, error: null });
  expect(await c.call()).toEqual({ ok: false });
  expect(m.rpc).not.toHaveBeenCalled();
}
async function malformed(c: RpcCase) {
  for (const data of [
    null,
    [{}],
    [c.row, c.row],
    [{ ...c.row, version: 0, child_name: "", batch_name: "" }],
  ]) {
    m.rpc.mockResolvedValue({ data, error: null });
    expect(await c.call()).toEqual({ ok: false });
  }
  m.rpc.mockResolvedValue({ data: [c.row], error: { message: "secret" } });
  expect(await c.call()).toEqual({ ok: false });
  m.rpc.mockRejectedValue(Error("secret"));
  expect(await c.call()).toEqual({ ok: false });
}
// Literal test identities keep the quality registry and runtime execution in agreement.
it("projects only validated app_enrollment_batches output and preserves RPC payload", () =>
  projects(cases[0]));
it("requires verified expected actor for app_enrollment_batches", () =>
  identity(cases[0]));
it("rejects malformed duplicate and provider-error app_enrollment_batches output", () =>
  malformed(cases[0]));
it("projects only validated app_enrollment_candidates output and preserves RPC payload", () =>
  projects(cases[1]));
it("requires verified expected actor for app_enrollment_candidates", () =>
  identity(cases[1]));
it("rejects malformed duplicate and provider-error app_enrollment_candidates output", () =>
  malformed(cases[1]));
it("projects only validated app_batch_enrollments output and preserves RPC payload", () =>
  projects(cases[2]));
it("requires verified expected actor for app_batch_enrollments", () =>
  identity(cases[2]));
it("rejects malformed duplicate and provider-error app_batch_enrollments output", () =>
  malformed(cases[2]));
it("projects only validated app_save_enrollment output and preserves RPC payload", () =>
  projects(cases[3]));
it("requires verified expected actor for app_save_enrollment", () =>
  identity(cases[3]));
it("rejects malformed duplicate and provider-error app_save_enrollment output", () =>
  malformed(cases[3]));
it("projects only validated app_change_enrollment output and preserves RPC payload", () =>
  projects(cases[4]));
it("requires verified expected actor for app_change_enrollment", () =>
  identity(cases[4]));
it("rejects malformed duplicate and provider-error app_change_enrollment output", () =>
  malformed(cases[4]));
it("projects only validated app_parent_enrollments output and preserves RPC payload", () =>
  projects(cases[5]));
it("requires verified expected actor for app_parent_enrollments", () =>
  identity(cases[5]));
it("rejects malformed duplicate and provider-error app_parent_enrollments output", () =>
  malformed(cases[5]));

it("rejects bad IDs cursors versions statuses and reasons before creating a client", async () => {
  const calls = [
    () => listEnrollmentBatches(actor, "bad"),
    () => listEnrollmentCandidates(actor, id, undefined),
    () => listBatchEnrollments(actor, id, id, "bad"),
    () => listParentEnrollments(actor, "bad"),
    () => saveEnrollment(actor, { ...save, childId: "bad" }),
    () => saveEnrollment(actor, null as never),
    () => changeEnrollment(actor, { ...change, expectedVersion: 0 }),
    () => changeEnrollment(actor, { ...change, expectedVersion: 1.2 }),
    () => changeEnrollment(actor, { ...change, reason: null }),
    () => changeEnrollment(actor, { ...change, status: "pending" }),
    () => changeEnrollment(actor, { ...change, status: "active" }),
    () =>
      changeEnrollment(actor, { ...change, reason: "personal note" as never }),
  ];
  for (const call of calls) expect(await call()).toEqual({ ok: false });
  expect(m.create).not.toHaveBeenCalled();
});
it("bounds paginated roster and candidates at fifty and parent classes at one hundred", async () => {
  for (const c of [cases[1], cases[2], cases[5]]) {
    m.rpc.mockResolvedValue({ data: Array(101).fill(c.row), error: null });
    expect(await c.call()).toEqual({ ok: false });
  }
});
it("passes non-null cursors and accepts null reasons for resume and complete", async () => {
  m.rpc.mockResolvedValue({ data: [], error: null });
  expect(await listEnrollmentCandidates(actor, id, actor)).toEqual({
    ok: true,
    data: [],
  });
  expect(m.rpc).toHaveBeenLastCalledWith("app_enrollment_candidates", {
    p_workspace_id: id,
    p_after: actor,
  });
  expect(await listBatchEnrollments(actor, id, id, actor)).toEqual({
    ok: true,
    data: [],
  });
  expect(m.rpc).toHaveBeenLastCalledWith("app_batch_enrollments", {
    p_workspace_id: id,
    p_batch_id: id,
    p_after: actor,
  });
  m.rpc.mockResolvedValue({ data: [receipt], error: null });
  for (const status of ["active", "completed"] as const)
    expect(
      (await changeEnrollment(actor, { ...change, status, reason: null })).ok,
    ).toBe(true);
});
it("rejects object reasons without coercing untrusted input", async () => {
  expect(
    await changeEnrollment(actor, {
      ...change,
      reason: { toString: () => "temporary_break" } as never,
    }),
  ).toEqual({ ok: false });
  expect(m.create).not.toHaveBeenCalled();
});
it("rejects auth errors even with a matching user and invalid actor IDs", async () => {
  m.getUser.mockResolvedValue({
    data: { user: { id: actor } },
    error: { message: "private" },
  });
  expect(await listEnrollmentBatches(actor, id)).toEqual({ ok: false });
  expect(await listEnrollmentBatches("bad", id)).toEqual({ ok: false });
  expect(m.rpc).not.toHaveBeenCalled();
});
it("rejects empty write receipts and invalid returned state or version", async () => {
  for (const data of [
    [],
    [{ ...receipt, status: "unknown" }],
    [{ ...receipt, version: 1.5 }],
    [{ ...receipt, version: 2147483648 }],
  ]) {
    m.rpc.mockResolvedValue({ data, error: null });
    expect(await changeEnrollment(actor, change)).toEqual({ ok: false });
  }
});
it("returns only fixed redacted mutation conflicts for structured 40001 and 23505 rejections", async () => {
  for (const code of ["40001", "23505"]) {
    m.rpc.mockResolvedValue({
      data: null,
      error: {
        code,
        message: "private child and workspace",
        details: "private payload",
      },
    });
    expect(await saveEnrollment(actor, save)).toEqual({
      ok: false,
      conflict: true,
    });
    expect(await changeEnrollment(actor, change)).toEqual({
      ok: false,
      conflict: true,
    });
  }
});
it("keeps read failures unchanged even when the provider reports a conflict code", async () => {
  m.rpc.mockResolvedValue({
    data: null,
    error: { code: "40001", message: "private" },
  });
  expect(await listEnrollmentBatches(actor, id)).toEqual({ ok: false });
  expect(await listBatchEnrollments(actor, id, id, null)).toEqual({
    ok: false,
  });
});
it("does not classify transport malformed output or non-allowlisted errors as definite conflicts", async () => {
  for (const error of [
    { code: "42501", message: "40001 23505 private" },
    { code: 40001 },
    { message: "23505" },
  ]) {
    m.rpc.mockResolvedValue({ data: null, error });
    expect(await changeEnrollment(actor, change)).toEqual({ ok: false });
  }
  m.rpc.mockRejectedValue({ code: "40001", message: "transport uncertainty" });
  expect(await changeEnrollment(actor, change)).toEqual({ ok: false });
  m.rpc.mockResolvedValue({ data: [], error: null });
  expect(await changeEnrollment(actor, change)).toEqual({ ok: false });
});
