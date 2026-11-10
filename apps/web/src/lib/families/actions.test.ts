import { beforeEach, expect, it, vi } from "vitest";
const m = vi.hoisted(() => ({
  create: vi.fn(),
  getUser: vi.fn(),
  rpc: vi.fn(),
}));
vi.mock("@/lib/supabase/server", () => ({ createClient: m.create }));
import {
  familySession,
  issueFamilyInvite,
  previewFamilyInvite,
  acceptFamilyInvite,
  familyRoster,
  childAcademies,
} from "./actions";
const actor = "11111111-1111-4111-8111-111111111111",
  id = "22222222-2222-4222-8222-222222222222",
  token = "ab".repeat(32);
beforeEach(() => {
  vi.resetAllMocks();
  m.create.mockResolvedValue({ auth: { getUser: m.getUser }, rpc: m.rpc });
  m.getUser.mockResolvedValue({ data: { user: { id: actor } }, error: null });
});
it("requires verified server identity", async () => {
  m.getUser.mockResolvedValue({ data: { user: null }, error: null });
  expect((await familySession()).ok).toBe(false);
  expect(m.rpc).not.toHaveBeenCalled();
});
it("rejects account switch before reading or writing", async () => {
  expect((await issueFamilyInvite(id, id, id, token)).ok).toBe(false);
  expect(m.rpc).not.toHaveBeenCalled();
});
it("rejects malformed token, IDs and cursor without RPC", async () => {
  expect((await issueFamilyInvite(actor, id, id, "short")).ok).toBe(false);
  expect((await acceptFamilyInvite(actor, token, "bad")).ok).toBe(false);
  expect((await familyRoster(actor, id, "bad")).ok).toBe(false);
  expect(m.rpc).not.toHaveBeenCalled();
});
it("passes stable request and token unchanged and validates response", async () => {
  m.rpc.mockResolvedValue({
    data: [{ invite_id: id, expires_at: "2026-11-24T12:00:00Z" }],
    error: null,
  });
  expect((await issueFamilyInvite(actor, id, id, token)).ok).toBe(true);
  expect(m.rpc).toHaveBeenCalledWith("app_issue_family_invite", {
    p_workspace_id: id,
    p_request_id: id,
    p_token: token,
  });
});
it("redacts provider errors and thrown exceptions", async () => {
  m.rpc.mockRejectedValue(new Error("private token"));
  expect(await previewFamilyInvite(actor, token)).toEqual({ ok: false });
  m.rpc.mockResolvedValue({ data: null, error: { message: "secret" } });
  expect(await acceptFamilyInvite(actor, token, id)).toEqual({ ok: false });
});
it("rejects malformed or duplicate database rows", async () => {
  for (const data of [
    null,
    [
      {
        relationship_id: id,
        child_name: "Child",
        relationship_status: "bogus",
      },
    ],
    [
      {
        relationship_id: id,
        child_name: "Child",
        relationship_status: "active",
      },
      {
        relationship_id: id,
        child_name: "Other",
        relationship_status: "active",
      },
    ],
  ]) {
    m.rpc.mockResolvedValue({ data, error: null });
    expect((await familyRoster(actor, id, null)).ok).toBe(false);
  }
});
it("projects only academy name, expiry and state from preview", async () => {
  m.rpc.mockResolvedValue({
    data: [
      {
        academy_name: "Academy",
        expires_at: "2026-11-24T12:00:00Z",
        state: "pending",
        private_field: "secret",
      },
    ],
    error: null,
  });
  const r = await previewFamilyInvite(actor, token);
  expect(r.ok).toBe(true);
  expect(JSON.stringify(r)).not.toContain("secret");
});
it("validates accepted relationship and parent read model", async () => {
  m.rpc.mockResolvedValue({ data: id, error: null });
  expect(await acceptFamilyInvite(actor, token, id)).toEqual({
    ok: true,
    data: id,
  });
  m.rpc.mockResolvedValue({
    data: [
      {
        relationship_id: id,
        academy_name: "Academy",
        relationship_status: "active",
      },
    ],
    error: null,
  });
  expect((await childAcademies(actor, id)).ok).toBe(true);
});
