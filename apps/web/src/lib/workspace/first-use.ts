"use server";
import { createClient } from "@/lib/supabase/server";
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const isId = (v: unknown): v is string => typeof v === "string" && UUID.test(v);
type Result = { ok: true; actorId: string; workspaceId: string | null } | { ok: false; error: string };
const unresolved: Result = { ok: false, error: "Workspace setup is unresolved. Check this request before retrying; do not start another request." };

export async function checkWorkspaceSetup(input: unknown): Promise<Result> {
  if (process.env.PARENTPLUS_ENABLE_WORKSPACE_CREATION !== "true") return unresolved;
  if (!input || typeof input !== "object" || Array.isArray(input)) return unresolved;
  const { expectedActorId, requestId } = input as Record<string, unknown>;
  if ((expectedActorId !== undefined && !isId(expectedActorId)) || (requestId !== undefined && !isId(requestId))) return unresolved;
  try {
    const client = await createClient();
    const { data, error } = await client.auth.getUser();
    const actorId = data.user?.id;
    if (error || !isId(actorId) || (expectedActorId !== undefined && actorId.toLowerCase() !== (expectedActorId as string).toLowerCase())) return unresolved;
    if (requestId === undefined) return { ok: true, actorId, workspaceId: null };
    const result = await client.from("workspaces").select("id").eq("created_by", actorId).eq("creation_request_id", requestId).eq("status", "active").limit(2);
    if (result.error || !Array.isArray(result.data) || result.data.length > 1 || (result.data.length === 1 && !isId(result.data[0].id))) return unresolved;
    // An empty snapshot is unknown: it never proves an in-flight write failed.
    return { ok: true, actorId, workspaceId: result.data[0]?.id ?? null };
  } catch { return unresolved; }
}
export async function createFirstWorkspace(input: unknown): Promise<Result> {
  if (process.env.PARENTPLUS_ENABLE_WORKSPACE_CREATION !== "true") return unresolved;
  if (!input || typeof input !== "object" || Array.isArray(input)) return unresolved;
  const { expectedActorId, requestId, name, type } = input as Record<string, unknown>;
  if (!isId(expectedActorId) || !isId(requestId) || typeof name !== "string" || Array.from(name.trim()).length < 2 || Array.from(name.trim()).length > 120 || (type !== "independent" && type !== "academy")) return unresolved;
  try {
    const client = await createClient();
    const { data: identity, error } = await client.auth.getUser();
    const actorId = identity.user?.id;
    if (error || !isId(actorId) || actorId.toLowerCase() !== expectedActorId.toLowerCase()) return unresolved;
    const result = await client.rpc("create_workspace", { p_name: name.trim(), p_type: type, p_request_id: requestId });
    return !result.error && isId(result.data) ? { ok: true, actorId, workspaceId: result.data } : unresolved;
  } catch { return unresolved; }
}
