import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { listCreatedChildren } from "./list-created-children";

const mocks = vi.hoisted(() => ({ createClient: vi.fn(), getUser: vi.fn(), rpc: vi.fn() }));
vi.mock("@/lib/supabase/server", () => ({ createClient: mocks.createClient }));
const actor = "11111111-1111-4111-8111-111111111111";
const child = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";

describe("listCreatedChildren", () => {
  beforeEach(() => {
    vi.resetAllMocks(); vi.stubEnv("PARENTPLUS_ENABLE_PARENT_CHILD_LIST", "true");
    mocks.createClient.mockResolvedValue({ auth: { getUser: mocks.getUser }, rpc: mocks.rpc });
    mocks.getUser.mockResolvedValue({ data: { user: { id: actor } }, error: null });
    mocks.rpc.mockResolvedValue({ data: [{ child_id: child, display_name: "Asha", private_field: "not returned" }], error: null });
  });
  afterEach(() => vi.unstubAllEnvs());
  it("fails closed before provider access when disabled", async () => {
    vi.stubEnv("PARENTPLUS_ENABLE_PARENT_CHILD_LIST", "false");
    expect((await listCreatedChildren()).ok).toBe(false); expect(mocks.createClient).not.toHaveBeenCalled();
  });
  it("requires a verified user before reading", async () => {
    mocks.getUser.mockResolvedValue({ data: { user: null }, error: null });
    expect((await listCreatedChildren()).ok).toBe(false); expect(mocks.rpc).not.toHaveBeenCalled();
  });
  it("returns only validated child identifiers and names", async () => {
    expect(await listCreatedChildren()).toEqual({ ok: true, children: [{ id: child, name: "Asha" }] });
    expect(mocks.rpc).toHaveBeenCalledWith("app_list_created_children");
  });
  it("accepts names up to 120 Unicode characters", async () => {
    const name = "😀".repeat(120);
    mocks.rpc.mockResolvedValue({ data: [{ child_id: child, display_name: name }], error: null });
    expect(await listCreatedChildren()).toEqual({ ok: true, children: [{ id: child, name }] });
  });
  it("accepts an empty list", async () => {
    mocks.rpc.mockResolvedValue({ data: [], error: null });
    expect(await listCreatedChildren()).toEqual({ ok: true, children: [] });
  });
  it("rejects malformed or duplicate provider rows", async () => {
    for (const data of [[{ child_id: "bad", display_name: "Private" }], [{ child_id: child, display_name: " " }], [{ child_id: child, display_name: "A" }, { child_id: child, display_name: "B" }]]) {
      mocks.rpc.mockResolvedValueOnce({ data, error: null }); expect((await listCreatedChildren()).ok).toBe(false);
    }
  });
  it("redacts provider errors and rejects excessive results", async () => {
    mocks.rpc.mockResolvedValueOnce({ data: null, error: { message: "private provider detail" } });
    expect(JSON.stringify(await listCreatedChildren())).not.toContain("private provider detail");
    mocks.rpc.mockResolvedValueOnce({ data: Array(101).fill({ child_id: child, display_name: "A" }), error: null });
    expect((await listCreatedChildren()).ok).toBe(false);
  });
});
