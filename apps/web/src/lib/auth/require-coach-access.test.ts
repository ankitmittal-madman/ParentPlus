import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { requireCoachAccess } from "./require-coach-access";

const mocks = vi.hoisted(() => ({ createClient: vi.fn(), getUser: vi.fn(), from: vi.fn(), select: vi.fn(), eq: vi.fn(), in: vi.fn(), redirect: vi.fn() }));
vi.mock("@/lib/supabase/server", () => ({ createClient: mocks.createClient }));
vi.mock("next/navigation", () => ({ redirect: mocks.redirect }));

const userId = "b0000000-0000-4000-8000-000000000001";
const workspaceId = "a0000000-0000-4000-8000-000000000001";

describe("requireCoachAccess", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    const query = { select: mocks.select, eq: mocks.eq, in: mocks.in };
    mocks.createClient.mockResolvedValue({ auth: { getUser: mocks.getUser }, from: mocks.from });
    mocks.getUser.mockResolvedValue({ data: { user: { id: userId } }, error: null });
    mocks.from.mockReturnValue(query); mocks.select.mockReturnValue(query); mocks.eq.mockReturnValue(query);
    mocks.in.mockResolvedValue({ data: [{ workspace_id: workspaceId, workspaces: { id: workspaceId, status: "active" } }], error: null });
    mocks.redirect.mockImplementation((path: string) => { throw new Error(`redirect:${path}`); });
  });
  afterEach(() => vi.unstubAllEnvs());

  it("sends anonymous users to sign in without querying memberships", async () => {
    mocks.getUser.mockResolvedValue({ data: { user: null }, error: null });
    await expect(requireCoachAccess()).rejects.toThrow("redirect:/login");
    expect(mocks.from).not.toHaveBeenCalled();
  });

  it("allows only an active workspace membership", async () => {
    await expect(requireCoachAccess()).resolves.toEqual({ userId, workspaceIds: [workspaceId] });
    expect(mocks.from).toHaveBeenCalledWith("workspace_memberships");
    expect(mocks.eq).toHaveBeenCalledWith("user_id", userId);
    expect(mocks.eq).toHaveBeenCalledWith("status", "active");
    expect(mocks.eq).toHaveBeenCalledWith("workspaces.status", "active");
    expect(mocks.in).toHaveBeenCalledWith("role", ["owner", "admin", "coach"]);
  });

  it("sends users without active memberships to the access page", async () => {
    mocks.in.mockResolvedValue({ data: [], error: null });
    await expect(requireCoachAccess()).rejects.toThrow("redirect:/coach-access");
  });

  it("fails closed on malformed membership rows even when another row is valid", async () => {
    mocks.in.mockResolvedValue({ data: [
      { workspace_id: workspaceId, workspaces: { id: workspaceId, status: "active" } },
      { workspace_id: "not-a-uuid", workspaces: { id: "not-a-uuid", status: "active" } },
    ], error: null });
    await expect(requireCoachAccess()).rejects.toThrow("redirect:/coach-access");
  });

  it("fails closed when identity or membership lookup fails", async () => {
    mocks.getUser.mockResolvedValue({ data: { user: { id: userId } }, error: { message: "private" } });
    await expect(requireCoachAccess()).rejects.toThrow("redirect:/login");
    mocks.getUser.mockResolvedValue({ data: { user: { id: userId } }, error: null });
    mocks.in.mockResolvedValue({ data: null, error: { message: "private" } });
    await expect(requireCoachAccess()).rejects.toThrow("redirect:/coach-access");
  });
});
