import { afterEach, beforeEach, expect, it, vi } from "vitest";
const mocks = vi.hoisted(() => ({ create: vi.fn(), rpc: vi.fn(), from: vi.fn(), getUser: vi.fn() }));
vi.mock("@/lib/supabase/server", () => ({ createClient: mocks.create }));
import { createFirstWorkspace, checkWorkspaceSetup } from "./first-use";
afterEach(() => vi.unstubAllEnvs());
const actor = "11111111-1111-4111-8111-111111111111";
const key = "22222222-2222-4222-8222-222222222222";
const workspace = "33333333-3333-4333-8333-333333333333";
beforeEach(() => {
  vi.resetAllMocks(); vi.stubEnv("PARENTPLUS_ENABLE_WORKSPACE_CREATION", "true");
  mocks.create.mockResolvedValue({ auth: { getUser: mocks.getUser }, rpc: mocks.rpc, from: mocks.from });
  mocks.getUser.mockResolvedValue({ data: { user: { id: actor } }, error: null });
});
it("does not contact the provider while workspace onboarding is disabled", async () => {
  vi.stubEnv("PARENTPLUS_ENABLE_WORKSPACE_CREATION", "false");
  expect((await createFirstWorkspace({ expectedActorId: actor, requestId: key, name: "Local Coach", type: "independent" })).ok).toBe(false);
  expect(mocks.create).not.toHaveBeenCalled();
});
it("rejects a changed actor before any workspace mutation", async () => {
  expect((await createFirstWorkspace({ expectedActorId: workspace, requestId: key, name: "Local Coach", type: "independent" })).ok).toBe(false);
  expect(mocks.rpc).not.toHaveBeenCalled();
});
it("uses the original request key and only existing controlled creation", async () => {
  mocks.rpc.mockResolvedValue({ data: workspace, error: null });
  expect(await createFirstWorkspace({ expectedActorId: actor, requestId: key, name: " Local Coach ", type: "independent" })).toEqual({ ok: true, actorId: actor, workspaceId: workspace });
  expect(mocks.rpc).toHaveBeenCalledWith("create_workspace", { p_name: "Local Coach", p_type: "independent", p_request_id: key });
});
it("treats transport failure as unresolved and redacts provider errors", async () => {
  mocks.rpc.mockRejectedValue(new Error("private-provider-error"));
  const result = await createFirstWorkspace({ expectedActorId: actor, requestId: key, name: "Local Coach", type: "academy" });
  expect(result.ok).toBe(false); expect(JSON.stringify(result)).not.toContain("private-provider-error");
  expect(JSON.stringify(result)).toContain("unresolved");
});
it("rejects malformed input without starting a provider request", async () => {
  for (const input of [null, {}, { expectedActorId: actor, requestId: "bad", name: "Local", type: "academy" }, { expectedActorId: actor, requestId: key, name: "X", type: "academy" }, { expectedActorId: actor, requestId: key, name: "Local", type: "owner" }]) expect((await createFirstWorkspace(input)).ok).toBe(false);
  expect(mocks.create).not.toHaveBeenCalled();
});
it("returns unknown for an empty RLS result without authorizing another request", async () => {
  const query = { select: vi.fn(), eq: vi.fn(), limit: vi.fn() };
  query.select.mockReturnValue(query); query.eq.mockReturnValue(query); query.limit.mockResolvedValue({ data: [], error: null }); mocks.from.mockReturnValue(query);
  expect(await checkWorkspaceSetup({ expectedActorId: actor, requestId: key })).toEqual({ ok: true, actorId: actor, workspaceId: null });
  expect(query.eq).toHaveBeenCalledWith("created_by", actor);
  expect(query.eq).toHaveBeenCalledWith("creation_request_id", key);
  expect(query.eq).toHaveBeenCalledWith("status", "active");
  expect(mocks.rpc).not.toHaveBeenCalled();
});
