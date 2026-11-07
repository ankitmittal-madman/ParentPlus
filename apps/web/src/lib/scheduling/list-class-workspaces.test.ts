import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { listClassWorkspaces } from "./list-class-workspaces";

const mocks = vi.hoisted(() => ({ createClient: vi.fn(), getUser: vi.fn(), from: vi.fn(), select: vi.fn(), eq: vi.fn(), in: vi.fn() }));
vi.mock("@/lib/supabase/server", () => ({ createClient: mocks.createClient }));
const actor = "b0000000-0000-4000-8000-000000000001";
const workspace = "a0000000-0000-4000-8000-000000000001";

describe("listClassWorkspaces", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.stubEnv("PARENTPLUS_ENABLE_CLASS_SETUP", "true");
    const query = { select: mocks.select, eq: mocks.eq, in: mocks.in };
    mocks.createClient.mockResolvedValue({ auth: { getUser: mocks.getUser }, from: mocks.from });
    mocks.getUser.mockResolvedValue({ data: { user: { id: actor } }, error: null });
    mocks.from.mockReturnValue(query); mocks.select.mockReturnValue(query); mocks.eq.mockReturnValue(query);
    mocks.in.mockResolvedValue({ data: [{ workspace_id: workspace, workspaces: { id: workspace, name: "Badminton Academy", status: "active", scheduling_time_zone: null } }], error: null });
  });
  afterEach(() => vi.unstubAllEnvs());

  it("does not contact the provider when class setup is disabled", async () => {
    vi.stubEnv("PARENTPLUS_ENABLE_CLASS_SETUP", "false");
    expect(await listClassWorkspaces()).toEqual({ ok: false, error: "Class setup is not available." });
    expect(mocks.createClient).not.toHaveBeenCalled();
  });
  it("requires a verified signed-in user", async () => {
    mocks.getUser.mockResolvedValue({ data: { user: null }, error: null });
    expect(await listClassWorkspaces()).toEqual({ ok: false, error: "Please sign in to continue." });
    expect(mocks.from).not.toHaveBeenCalled();
  });
  it("filters own active manager memberships and active workspaces", async () => {
    expect(await listClassWorkspaces()).toEqual({ ok: true, actorId: actor, workspaces: [{ id: workspace, name: "Badminton Academy", timeZone: null }] });
    expect(mocks.from).toHaveBeenCalledWith("workspace_memberships");
    expect(mocks.eq).toHaveBeenCalledWith("user_id", actor);
    expect(mocks.eq).toHaveBeenCalledWith("status", "active");
    expect(mocks.eq).toHaveBeenCalledWith("workspaces.status", "active");
    expect(mocks.in).toHaveBeenCalledWith("role", ["owner", "admin"]);
  });
  it("returns an empty list when no eligible workspace exists", async () => {
    mocks.in.mockResolvedValue({ data: [], error: null });
    expect(await listClassWorkspaces()).toEqual({ ok: true, actorId: actor, workspaces: [] });
  });
  it("fails closed on malformed workspace data", async () => {
    mocks.in.mockResolvedValue({ data: [{ workspace_id: workspace, workspaces: { id: "different", name: "Secret", status: "active", scheduling_time_zone: null } }], error: null });
    expect(await listClassWorkspaces()).toEqual({ ok: false, error: "Unable to load academies." });
  });
  it("redacts provider errors", async () => {
    mocks.in.mockResolvedValue({ data: null, error: { message: "private" } });
    expect(await listClassWorkspaces()).toEqual({ ok: false, error: "Unable to load academies." });
  });
});
