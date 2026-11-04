import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { runChildCreation } from "./child-creation-journey";

const mocks = vi.hoisted(() => ({ createClient: vi.fn(), getUser: vi.fn(), rpc: vi.fn() }));
vi.mock("@/lib/supabase/server", () => ({ createClient: mocks.createClient }));
const actor = "11111111-1111-4111-8111-111111111111";
const other = "22222222-2222-4222-8222-222222222222";
const intent = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const child = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
const request = "cccccccc-cccc-4ccc-8ccc-cccccccccccc";
const row = { intent_id: intent, child_id: child, display_name: "Asha", acknowledged: false, prior_intent_id: null, request_id: request };

describe("runChildCreation", () => {
  beforeEach(() => {
    vi.resetAllMocks(); vi.stubEnv("PARENTPLUS_ENABLE_CHILD_CREATION", "true"); vi.stubEnv("PARENTPLUS_ENABLE_PARENT_CHILD_LIST", "true");
    mocks.createClient.mockResolvedValue({ auth: { getUser: mocks.getUser }, rpc: mocks.rpc });
    mocks.getUser.mockResolvedValue({ data: { user: { id: actor } }, error: null });
    mocks.rpc.mockResolvedValue({ data: [], error: null });
  });
  afterEach(() => vi.unstubAllEnvs());
  it("fails closed without provider access when disabled", async () => {
    vi.stubEnv("PARENTPLUS_ENABLE_CHILD_CREATION", "false");
    expect((await runChildCreation({ operation: "status" })).ok).toBe(false);
    expect(mocks.createClient).not.toHaveBeenCalled();
  });
  it("fails closed when the parent page is disabled", async () => {
    vi.stubEnv("PARENTPLUS_ENABLE_PARENT_CHILD_LIST", "false");
    expect((await runChildCreation({ operation: "status" })).ok).toBe(false);
    expect(mocks.createClient).not.toHaveBeenCalled();
  });
  it("rejects invalid operations and details before provider access", async () => {
    for (const input of [null, {}, { operation: "begin", expectedActorId: actor, displayName: " ", priorIntentId: null }, { operation: "begin", expectedActorId: actor, displayName: "A".repeat(121), priorIntentId: null }, { operation: "ack", expectedActorId: actor, intentId: "bad" }]) {
      expect((await runChildCreation(input)).ok).toBe(false);
    }
    expect(mocks.createClient).not.toHaveBeenCalled();
  });
  it("rejects missing or changed user identity before the RPC", async () => {
    mocks.getUser.mockResolvedValueOnce({ data: { user: null }, error: null });
    expect((await runChildCreation({ operation: "status" })).ok).toBe(false);
    expect((await runChildCreation({ operation: "begin", expectedActorId: other, displayName: "Asha", priorIntentId: null, requestId: request })).ok).toBe(false);
    expect(mocks.rpc).not.toHaveBeenCalled();
  });
  it("returns a scoped empty or current status", async () => {
    expect(await runChildCreation({ operation: "status" })).toEqual({ ok: true, operation: "status", actorId: actor, current: null });
    mocks.rpc.mockResolvedValueOnce({ data: [row], error: null });
    expect(await runChildCreation({ operation: "status", expectedActorId: actor })).toEqual({ ok: true, operation: "status", actorId: actor, current: { intentId: intent, childId: child, name: "Asha", acknowledged: false, priorIntentId: null, requestId: request } });
    expect(mocks.rpc).toHaveBeenLastCalledWith("app_current_child_creation");
  });
  it("starts an explicit request without passing a caller actor to the database", async () => {
    mocks.rpc.mockResolvedValue({ data: [{ ...row, disposition: "created" }], error: null });
    expect(await runChildCreation({ operation: "begin", expectedActorId: actor, displayName: " Asha ", priorIntentId: null, requestId: request })).toEqual({ ok: true, operation: "begin", current: { intentId: intent, childId: child, name: "Asha", acknowledged: false, priorIntentId: null, requestId: request }, disposition: "created" });
    expect(mocks.rpc).toHaveBeenCalledWith("app_begin_child_creation", { p_display_name: "Asha", p_prior_intent_id: null, p_request_id: request });
  });
  it("acknowledges only the explicit intent after identity verification", async () => {
    mocks.rpc.mockResolvedValue({ data: true, error: null });
    expect(await runChildCreation({ operation: "ack", expectedActorId: actor, intentId: intent })).toEqual({ ok: true, operation: "ack" });
    expect(mocks.rpc).toHaveBeenCalledWith("app_ack_child_creation", { p_intent_id: intent });
  });
  it("does not claim success for malformed or contradictory results", async () => {
    for (const data of [[{ ...row, child_id: "bad", disposition: "created" }], [{ ...row, display_name: "Other", disposition: "created" }], [{ ...row, acknowledged: true, disposition: "created" }], [{ ...row, request_id: "ffffffff-ffff-4fff-8fff-ffffffffffff", disposition: "existing" }], [{ ...row, prior_intent_id: intent, disposition: "existing" }], []]) {
      mocks.rpc.mockResolvedValueOnce({ data, error: null });
      expect((await runChildCreation({ operation: "begin", expectedActorId: actor, displayName: "Asha", priorIntentId: null, requestId: request })).ok).toBe(false);
    }
  });
  it("redacts provider failures and treats them as uncertain", async () => {
    mocks.rpc.mockResolvedValueOnce({ data: null, error: { message: "private provider detail" } });
    const result = await runChildCreation({ operation: "status" });
    expect(result.ok).toBe(false); expect(JSON.stringify(result)).not.toContain("private provider detail");
  });
});
