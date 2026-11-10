import { afterEach, beforeEach, expect, it, vi } from "vitest";
const mocks = vi.hoisted(() => ({ client: vi.fn(), user: vi.fn(), from: vi.fn(), upsert: vi.fn() }));
vi.mock("@supabase/supabase-js", () => ({ createClient: mocks.client }));
import { readFounderRecords, setFounderMembership } from "./controls";
const userId = "11111111-1111-4111-8111-111111111111", workspaceId = "22222222-2222-4222-8222-222222222222";
beforeEach(() => {
  vi.resetAllMocks(); vi.stubEnv("NODE_ENV", "development"); vi.stubEnv("PARENTPLUS_FOUNDER_MODE", "true"); vi.stubEnv("NEXT_PUBLIC_FOUNDER_MODE", "true");
  vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "http://127.0.0.1:54321"); vi.stubEnv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "local-public"); vi.stubEnv("PARENTPLUS_LOCAL_SERVICE_KEY", "local-private");
  mocks.client.mockReturnValue({ auth: { admin: { getUserById: mocks.user } }, from: mocks.from }); mocks.from.mockReturnValue({ upsert: mocks.upsert });
});
afterEach(() => vi.unstubAllEnvs());
it("keeps founder read and override controls inaccessible in production", async () => {
  vi.stubEnv("NODE_ENV", "production"); expect((await readFounderRecords()).ok).toBe(false); expect((await setFounderMembership({ userId, workspaceId, role: "owner", status: "active" })).ok).toBe(false); expect(mocks.client).not.toHaveBeenCalled();
});
it("rejects a non-synthetic account without writing memberships", async () => {
  mocks.user.mockResolvedValue({ data: { user: { email: "person@example.com" } }, error: null });
  expect((await setFounderMembership({ userId, workspaceId, role: "owner", status: "active" })).ok).toBe(false); expect(mocks.from).not.toHaveBeenCalled();
});
it("lets the founder restore or suspend a synthetic test membership", async () => {
  mocks.user.mockResolvedValue({ data: { user: { email: "coach@example.test" } }, error: null }); mocks.upsert.mockResolvedValue({ error: null });
  for (const status of ["active", "suspended"]) expect((await setFounderMembership({ userId, workspaceId, role: "coach", status })).ok).toBe(true);
  expect(mocks.upsert).toHaveBeenCalledWith({ user_id: userId, workspace_id: workspaceId, role: "coach", status: "suspended" }, { onConflict: "workspace_id,user_id" });
});
it("keeps accounts and workspaces beyond the first page available to founder overrides", async () => {
  const listUsers = vi.fn(({ page }) => Promise.resolve({ error: null, data: { users: page === 1 ? Array.from({ length: 100 }, (_, i) => ({ id: `old-${i}`, email: `old-${i}@example.test` })) : [{ id: userId, email: "latest@example.test" }] } }));
  const range = vi.fn((start) => Promise.resolve({ error: null, data: start === 0 ? Array.from({ length: 100 }, (_, i) => ({ id: `workspace-${i}`, name: "Existing", status: "active" })) : [{ id: workspaceId, name: "Latest academy", status: "active" }] }));
  const query = { select: vi.fn(), order: vi.fn(), limit: vi.fn(), range };
  query.order.mockReturnValue(query); query.limit.mockResolvedValue({ error: null, data: [], count: 0 });
  query.select.mockImplementation((_fields, options) => options?.head ? Promise.resolve({ error: null, count: 0 }) : query);
  mocks.client.mockReturnValue({ auth: { admin: { listUsers } }, from: () => query });
  const result = await readFounderRecords();
  expect(result.ok).toBe(true);
  if (result.ok) { expect(result.users).toContainEqual({ id: userId, email: "latest@example.test" }); expect(result.workspaces).toContainEqual({ id: workspaceId, name: "Latest academy", status: "active" }); }
});
