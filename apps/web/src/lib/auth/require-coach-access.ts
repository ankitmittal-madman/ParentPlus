import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function requireCoachAccess(): Promise<{ userId: string; workspaceIds: string[] }> {
  let userId: string | undefined;
  let workspaceIds: string[] = [];
  try {
    const client = await createClient();
    const { data: identity, error: identityError } = await client.auth.getUser();
    if (!identityError && typeof identity.user?.id === "string" && UUID.test(identity.user.id)) {
      userId = identity.user.id;
      const { data, error } = await client.from("workspace_memberships")
        .select("workspace_id, workspaces!inner(id, status)")
        .eq("user_id", userId)
        .eq("status", "active")
        .eq("workspaces.status", "active")
        .in("role", ["owner", "admin", "coach"]);
      if (!error && Array.isArray(data)) {
        const eligibleWorkspaceIds: string[] = [];
        let malformedMembership = false;
        for (const row of data) {
          const workspace = row.workspaces as unknown;
          if (!workspace || typeof workspace !== "object" || Array.isArray(workspace)) {
            malformedMembership = true;
            break;
          }
          const value = workspace as Record<string, unknown>;
          if (typeof row.workspace_id !== "string" || !UUID.test(row.workspace_id)
            || value.id !== row.workspace_id || value.status !== "active") {
            malformedMembership = true;
            break;
          }
          eligibleWorkspaceIds.push(row.workspace_id);
        }
        workspaceIds = malformedMembership ? [] : eligibleWorkspaceIds;
      }
    }
  } catch {
    // Provider, cookie and malformed-response errors all fail closed below.
  }
  if (!userId) redirect("/login");
  if (workspaceIds.length === 0) redirect("/coach-access");
  return { userId, workspaceIds };
}
