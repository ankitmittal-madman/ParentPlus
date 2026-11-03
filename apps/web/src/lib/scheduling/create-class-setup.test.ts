import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createClassSetup } from "./create-class-setup";

const mocks = vi.hoisted(() => ({ createClient: vi.fn(), getUser: vi.fn(), rpc: vi.fn() }));
vi.mock("@/lib/supabase/server", () => ({ createClient: mocks.createClient }));

const input = { expectedActorId: "b0000000-0000-4000-8000-000000000001", workspaceId: "a0000000-0000-4000-8000-000000000001", requestId: "e5000000-0000-4000-8000-000000000001", courseName: " Dance ", batchName: " Beginners " };
const ids = { course_id: "c0000000-0000-4000-8000-000000000001", batch_id: "d0000000-0000-4000-8000-000000000001" };

describe("createClassSetup", () => {
  beforeEach(() => {
    mocks.createClient.mockReset(); mocks.getUser.mockReset(); mocks.rpc.mockReset();
    mocks.createClient.mockResolvedValue({ auth: { getUser: mocks.getUser }, rpc: mocks.rpc });
    mocks.getUser.mockResolvedValue({ data: { user: { id: input.expectedActorId } }, error: null });
    mocks.rpc.mockResolvedValue({ data: [ids], error: null });
    vi.stubEnv("PARENTPLUS_ENABLE_CLASS_SETUP", "true");
  });
  afterEach(() => vi.unstubAllEnvs());

  it("fails closed without constructing a client when disabled", async () => {
    vi.stubEnv("PARENTPLUS_ENABLE_CLASS_SETUP", "false");
    expect(await createClassSetup(input)).toEqual({ ok: false, error: "Class setup is not available." });
    expect(mocks.createClient).not.toHaveBeenCalled();
  });

  it("rejects malformed IDs and names before constructing a client", async () => {
    for (const invalid of [null, { ...input, workspaceId: "bad" }, { ...input, requestId: "bad" }, { ...input, courseName: "  " }, { ...input, batchName: "x".repeat(121) }]) {
      expect(await createClassSetup(invalid)).toEqual({ ok: false, error: "Check the class setup details." });
    }
    expect(mocks.createClient).not.toHaveBeenCalled();
  });

  it("rejects a missing user without calling the RPC", async () => {
    mocks.getUser.mockResolvedValue({ data: { user: null }, error: null });
    expect(await createClassSetup(input)).toEqual({ ok: false, error: "Please sign in to continue." });
    expect(mocks.rpc).not.toHaveBeenCalled();
  });

  it("rejects a provider identity error without calling the RPC", async () => {
    mocks.getUser.mockResolvedValue({ data: { user: null }, error: { message: "private detail" } });
    expect(await createClassSetup(input)).toEqual({ ok: false, error: "Please sign in to continue." });
    expect(mocks.rpc).not.toHaveBeenCalled();
  });

  it("rejects a retry when the signed-in account has changed", async () => {
    mocks.getUser.mockResolvedValue({ data: { user: { id: "b0000000-0000-4000-8000-000000000002" } }, error: null });
    expect(await createClassSetup(input)).toEqual({ ok: false, error: "Your account has changed. Restart class setup." });
    expect(mocks.rpc).not.toHaveBeenCalled();
  });

  it("rejects a missing or malformed expected actor before contacting the provider", async () => {
    for (const expectedActorId of [undefined, "not-an-id"]) {
      expect(await createClassSetup({ ...input, expectedActorId })).toEqual({ ok: false, error: "Check the class setup details." });
    }
    expect(mocks.createClient).not.toHaveBeenCalled();
  });

  it("sends normalized values and the original retry ID to the atomic RPC", async () => {
    expect(await createClassSetup({ ...input, actorId: "untrusted-actor" })).toEqual({ ok: true, courseId: ids.course_id, batchId: ids.batch_id });
    expect(mocks.rpc).toHaveBeenCalledWith("create_course_and_batch", { p_workspace_id: input.workspaceId, p_request_id: input.requestId, p_course_name: "Dance", p_batch_name: "Beginners" });
  });

  it("redacts RPC errors", async () => {
    mocks.rpc.mockResolvedValue({ data: null, error: { message: "private database detail" } });
    expect(await createClassSetup(input)).toEqual({ ok: false, error: "Unable to complete class setup." });
  });

  it("redacts thrown client errors", async () => {
    mocks.createClient.mockRejectedValue(new Error("private configuration"));
    expect(await createClassSetup(input)).toEqual({ ok: false, error: "Unable to complete class setup." });
  });

  it("does not claim success for malformed RPC results", async () => {
    for (const data of [null, [], [ids, ids], [{ course_id: "invalid", batch_id: ids.batch_id }]]) {
      mocks.rpc.mockResolvedValue({ data, error: null });
      expect(await createClassSetup(input)).toEqual({ ok: false, error: "Unable to complete class setup." });
    }
  });
});
