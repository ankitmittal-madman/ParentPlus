"use server";

import { createClient } from "@/lib/supabase/server";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
type Result =
  | { ok: true; actorId: string; workspaces: { id: string; name: string; timeZone: string | null }[] }
  | { ok: false; error: string };

export async function listClassWorkspaces(): Promise<Result> {
  if (process.env.PARENTPLUS_ENABLE_CLASS_SETUP !== "true") {
    return { ok: false, error: "Class setup is not available." };
  }
  try {
    const client = await createClient();
    const { data: identity, error: identityError } = await client.auth.getUser();
    const actorId = identity.user?.id;
    if (identityError || typeof actorId !== "string" || !UUID.test(actorId)) {
      return { ok: false, error: "Please sign in to continue." };
    }
    const { data, error } = await client.from("workspace_memberships")
      .select("workspace_id, workspaces!workspace_memberships_workspace_id_fkey!inner(id, name, status, scheduling_time_zone)")
      .eq("user_id", actorId)
      .eq("status", "active")
      .eq("workspaces.status", "active")
      .in("role", ["owner", "admin"]);
    if (error || !Array.isArray(data)) return { ok: false, error: "Unable to load academies." };
    const workspaces: { id: string; name: string; timeZone: string | null }[] = [];
    for (const row of data) {
      const item = row.workspaces as unknown;
      if (!item || typeof item !== "object" || Array.isArray(item)) return { ok: false, error: "Unable to load academies." };
      const value = item as Record<string, unknown>;
      if (typeof row.workspace_id !== "string" || !UUID.test(row.workspace_id)
        || value.id !== row.workspace_id || typeof value.name !== "string" || !value.name.trim()
        || value.status !== "active"
        || (value.scheduling_time_zone !== null && typeof value.scheduling_time_zone !== "string")) return { ok: false, error: "Unable to load academies." };
      workspaces.push({ id: row.workspace_id, name: value.name, timeZone: value.scheduling_time_zone as string | null });
    }
    return { ok: true, actorId, workspaces };
  } catch {
    return { ok: false, error: "Unable to load academies." };
  }
}
