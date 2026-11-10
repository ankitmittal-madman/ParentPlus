"use server";
import { createFounderAdmin } from "./server-admin";
import { founderConfig } from "./runtime";
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
export async function readFounderRecords() {
  const config = founderConfig();
  if (!config) return { ok: false as const, error: "Local founder controls are unavailable." };
  try {
    const admin = await createFounderAdmin(config);
    const users: { id: string; email?: string }[] = [];
    const seen = new Set<string>();
    for (let page = 1; ; page++) {
      const result = await admin.auth.admin.listUsers({ page, perPage: 100 });
      if (result.error) throw new Error("Unavailable");
      for (const user of result.data.users) {
        if (seen.has(user.id)) throw new Error("Account list changed; refresh");
        seen.add(user.id); users.push(user);
      }
      if (result.data.users.length < 100) break;
    }
    const workspaces: { id: string; name: string; status: string }[] = [];
    for (let offset = 0; ; offset += 100) {
      const result = await admin.from("workspaces").select("id,name,status").order("id").range(offset, offset + 99);
      if (result.error) throw new Error("Unavailable");
      workspaces.push(...result.data);
      if (result.data.length < 100) break;
    }
    const counts: Record<string, number> = {};
    for (const table of ["children", "workspaces", "courses", "batches", "schedule_sessions", "workspace_memberships"]) {
      const result = await admin.from(table).select("*", { count: "exact", head: true });
      if (result.error || result.count === null) throw new Error("Unavailable");
      counts[table] = result.count;
    }
    return { ok: true as const, counts, users: users.filter(u => u.email?.endsWith(".test")).map(u => ({ id: u.id, email: u.email! })), workspaces };
  } catch { return { ok: false as const, error: "Unable to load local test records." }; }
}
export async function setFounderMembership(input: unknown) {
  const config = founderConfig();
  if (!config || !input || typeof input !== "object" || Array.isArray(input)) return { ok: false, error: "Local founder controls are unavailable." };
  const { userId, workspaceId, role, status } = input as Record<string, unknown>;
  if (typeof userId !== "string" || !UUID.test(userId) || typeof workspaceId !== "string" || !UUID.test(workspaceId) || (typeof role !== "string" || !["owner", "admin", "coach"].includes(role)) || (typeof status !== "string" || !["active", "suspended", "removed"].includes(status))) return { ok: false, error: "Choose a test account, workspace, role and status." };
  try {
    const admin = await createFounderAdmin(config);
    const user = await admin.auth.admin.getUserById(userId);
    if (user.error || !user.data.user.email?.endsWith(".test")) throw new Error("Not a synthetic account");
    const result = await admin.from("workspace_memberships").upsert({ user_id: userId, workspace_id: workspaceId, role, status }, { onConflict: "workspace_id,user_id" });
    if (result.error) throw new Error("Unavailable");
    return { ok: true, error: null };
  } catch { return { ok: false, error: "Unable to update this test membership." }; }
}
