import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { recoverCurrentClassSetup } from "./recover-current-class-setup";

const mocks = vi.hoisted(() => ({ createClient: vi.fn(), getUser: vi.fn(), rpc: vi.fn() }));
vi.mock("@/lib/supabase/server", () => ({ createClient: mocks.createClient }));
const actor = "b0000000-0000-4000-8000-000000000001";
const workspace = "a0000000-0000-4000-8000-000000000001";
const intent = "e0000000-0000-4000-8000-000000000001";
const prior = "e0000000-0000-4000-8000-000000000002";
const request = "e0000000-0000-4000-8000-000000000003";
const course = "c0000000-0000-4000-8000-000000000001";
const batch = "d0000000-0000-4000-8000-000000000001";
const scheduleFields = { time_zone: null, start_date: null, start_time: null, end_date: null, duration_minutes: null, occurrence_count: null };
const pending = { state: "pending", intent_id: intent, prior_intent_id: prior, request_id: request, course_name: "Art", batch_name: "Morning", course_id: null, batch_id: null, acknowledged: false, ...scheduleFields };
const unknown = { state: "unknown", intent_id: null, prior_intent_id: null, request_id: null, course_name: null, batch_name: null, course_id: null, batch_id: null, acknowledged: null, ...scheduleFields };
const input = { workspaceId: workspace, expectedActorId: actor };

describe("recoverCurrentClassSetup", () => {
  beforeEach(() => {
    vi.resetAllMocks(); vi.stubEnv("PARENTPLUS_ENABLE_CLASS_SETUP", "true");
    mocks.createClient.mockResolvedValue({ auth: { getUser: mocks.getUser }, rpc: mocks.rpc });
    mocks.getUser.mockResolvedValue({ data: { user: { id: actor } }, error: null });
    mocks.rpc.mockResolvedValue({ data: [pending], error: null });
  });
  afterEach(() => vi.unstubAllEnvs());
  it("fails closed before contacting the provider when disabled", async () => {
    vi.stubEnv("PARENTPLUS_ENABLE_CLASS_SETUP", "false");
    expect(await recoverCurrentClassSetup(input)).toEqual({ ok: false, error: "Class setup is not available." });
    expect(mocks.createClient).not.toHaveBeenCalled();
  });
  it("rejects malformed workspace and expected actor IDs", async () => {
    for (const x of [null, { ...input, workspaceId: "bad" }, { ...input, expectedActorId: "bad" }]) {
      expect(await recoverCurrentClassSetup(x)).toEqual({ ok: false, error: "Check the recovery details." });
    }
    expect(mocks.createClient).not.toHaveBeenCalled();
  });
  it("denies missing or failed provider identity before the RPC", async () => {
    for (const response of [{ data: { user: null }, error: null }, { data: { user: null }, error: { message: "private" } }]) {
      mocks.getUser.mockResolvedValue(response);
      expect(await recoverCurrentClassSetup(input)).toEqual({ ok: false, error: "Please sign in to continue." });
    }
    expect(mocks.rpc).not.toHaveBeenCalled();
  });
  it("denies an account switch before calling the RPC", async () => {
    mocks.getUser.mockResolvedValue({ data: { user: { id: prior } }, error: null });
    expect(await recoverCurrentClassSetup(input)).toEqual({ ok: false, error: "Your account has changed. Sign in to the original account before continuing." });
    expect(mocks.rpc).not.toHaveBeenCalled();
  });
  it("returns a sanitized pending request and sends only the workspace", async () => {
    expect(await recoverCurrentClassSetup({ ...input, actorId: "untrusted" })).toEqual({ ok: true, state: "pending", intentId: intent, priorIntentId: prior, requestId: request, courseName: "Art", batchName: "Morning", schedule: null });
    expect(mocks.rpc).toHaveBeenCalledWith("app_current_class_setup_v2", { p_workspace_id: workspace });
  });
  it("keeps unknown distinct from failure or absence", async () => {
    mocks.rpc.mockResolvedValue({ data: [unknown], error: null });
    expect(await recoverCurrentClassSetup(input)).toEqual({ ok: true, state: "unknown" });
  });
  it("returns a valid completed result with acknowledgement state", async () => {
    mocks.rpc.mockResolvedValue({ data: [{ ...pending, state: "completed", course_id: course, batch_id: batch, acknowledged: true }], error: null });
    expect(await recoverCurrentClassSetup(input)).toEqual({ ok: true, state: "completed", intentId: intent, priorIntentId: prior, requestId: request, courseName: "Art", batchName: "Morning", courseId: course, batchId: batch, acknowledged: true, schedule: null });
  });
  it("recovers a completed weekly schedule after a lost response or reload", async () => {
    mocks.rpc.mockResolvedValue({ data: [{ ...pending, state: "completed", course_id: course, batch_id: batch, acknowledged: false, time_zone: "Asia/Kolkata", start_date: "2026-11-09", start_time: "17:30:00", end_date: "2026-11-23", duration_minutes: 60, occurrence_count: 3 }], error: null });
    expect(await recoverCurrentClassSetup(input)).toMatchObject({ ok: true, state: "completed", schedule: { timeZone: "Asia/Kolkata", startDate: "2026-11-09", startTime: "17:30", endDate: "2026-11-23", durationMinutes: 60, occurrenceCount: 3 } });
  });
  it("rejects inconsistent or malformed provider results without claiming success", async () => {
    for (const data of [null, [], [pending,pending], [{ ...unknown, intent_id: intent }], [{ ...pending, request_id: null }], [{ ...pending, acknowledged: true }], [{ ...pending, course_id: course }], [{ ...pending, state: "completed", course_id: course, batch_id: "bad" }], [{ ...pending, state: "mystery" }]]) {
      mocks.rpc.mockResolvedValue({ data, error: null });
      expect(await recoverCurrentClassSetup(input)).toEqual({ ok: false, error: "Unable to recover class setup." });
    }
  });
  it("redacts provider and thrown errors", async () => {
    mocks.rpc.mockResolvedValue({ data: null, error: { message: "private database detail" } });
    expect(await recoverCurrentClassSetup(input)).toEqual({ ok: false, error: "Unable to recover class setup." });
    mocks.createClient.mockRejectedValue(new Error("private configuration"));
    expect(await recoverCurrentClassSetup(input)).toEqual({ ok: false, error: "Unable to recover class setup." });
  });
});
