"use server";
import { createClient } from "@/lib/supabase/server";
import {
  isId,
  isToken,
  isName,
  isDate,
  rows,
  rosterRows,
  type Result,
  type Invite,
  type Preview,
  type RosterRow,
  type Child,
} from "@/modules/families/contracts";

async function clientFor(expectedActor: unknown) {
  if (!isId(expectedActor)) return null;
  const client = await createClient();
  const { data, error } = await client.auth.getUser();
  return !error &&
    isId(data.user?.id) &&
    data.user.id.toLowerCase() === expectedActor.toLowerCase()
    ? client
    : null;
}
export async function familySession(): Promise<Result<string>> {
  try {
    const client = await createClient();
    const { data, error } = await client.auth.getUser();
    return !error && isId(data.user?.id)
      ? { ok: true, data: data.user.id }
      : { ok: false };
  } catch {
    return { ok: false };
  }
}
export async function familyAcademies(
  actor: unknown,
): Promise<Result<Child[]>> {
  try {
    const client = await clientFor(actor);
    if (!client) return { ok: false };
    const { data, error } = await client
      .from("workspace_memberships")
      .select(
        "workspace_id, workspaces!workspace_memberships_workspace_id_fkey!inner(id,name,status)",
      )
      .eq("user_id", actor)
      .eq("status", "active")
      .eq("workspaces.status", "active")
      .in("role", ["owner", "admin"])
      .limit(100);
    const seen = new Set<string>();
    const result = rows(data, 100, (r) => {
      const w = r.workspaces as Record<string, unknown> | null;
      if (
        !w ||
        !isId(r.workspace_id) ||
        w.id !== r.workspace_id ||
        !isName(w.name) ||
        w.status !== "active" ||
        seen.has(r.workspace_id)
      )
        return null;
      seen.add(r.workspace_id);
      return { id: r.workspace_id, name: w.name };
    });
    return !error && result ? { ok: true, data: result } : { ok: false };
  } catch {
    return { ok: false };
  }
}
export async function familyChildren(actor: unknown): Promise<Result<Child[]>> {
  try {
    const client = await clientFor(actor);
    if (!client) return { ok: false };
    const { data, error } = await client.rpc("app_list_created_children");
    const seen = new Set<string>();
    const result = rows(data, 100, (r) => {
      if (!isId(r.child_id) || !isName(r.display_name) || seen.has(r.child_id))
        return null;
      seen.add(r.child_id);
      return { id: r.child_id, name: r.display_name };
    });
    return !error && result ? { ok: true, data: result } : { ok: false };
  } catch {
    return { ok: false };
  }
}
export async function issueFamilyInvite(
  actor: unknown,
  workspace: unknown,
  request: unknown,
  token: unknown,
): Promise<Result<Invite>> {
  if (!isId(workspace) || !isId(request) || !isToken(token))
    return { ok: false };
  try {
    const client = await clientFor(actor);
    if (!client) return { ok: false };
    const { data, error } = await client.rpc("app_issue_family_invite", {
      p_workspace_id: workspace,
      p_request_id: request,
      p_token: token,
    });
    const result = rows(data, 1, (r) =>
      isId(r.invite_id) && r.invite_id === request && isDate(r.expires_at)
        ? { inviteId: r.invite_id, expiresAt: r.expires_at }
        : null,
    );
    return !error && result?.length === 1
      ? { ok: true, data: result[0] }
      : { ok: false };
  } catch {
    return { ok: false };
  }
}
export async function previewFamilyInvite(
  actor: unknown,
  token: unknown,
): Promise<Result<Preview>> {
  if (!isToken(token)) return { ok: false };
  try {
    const client = await clientFor(actor);
    if (!client) return { ok: false };
    const { data, error } = await client.rpc("app_preview_family_invite", {
      p_token: token,
    });
    const result = rows<Preview>(data, 1, (r) =>
      isName(r.academy_name) &&
      isDate(r.expires_at) &&
      (r.state === "pending" || r.state === "accepted")
        ? {
            academyName: r.academy_name,
            expiresAt: r.expires_at,
            state: r.state,
          }
        : null,
    );
    return !error && result?.length === 1
      ? { ok: true, data: result[0] }
      : { ok: false };
  } catch {
    return { ok: false };
  }
}
export async function acceptFamilyInvite(
  actor: unknown,
  token: unknown,
  child: unknown,
): Promise<Result<string>> {
  if (!isToken(token) || !isId(child)) return { ok: false };
  try {
    const client = await clientFor(actor);
    if (!client) return { ok: false };
    const { data, error } = await client.rpc("app_accept_family_invite", {
      p_token: token,
      p_child_id: child,
    });
    return !error && isId(data) ? { ok: true, data } : { ok: false };
  } catch {
    return { ok: false };
  }
}
export async function familyRoster(
  actor: unknown,
  workspace: unknown,
  after: unknown,
): Promise<Result<RosterRow[]>> {
  if (!isId(workspace) || (after !== null && !isId(after)))
    return { ok: false };
  try {
    const client = await clientFor(actor);
    if (!client) return { ok: false };
    const { data, error } = await client.rpc("app_family_roster", {
      p_workspace_id: workspace,
      p_after: after,
    });
    const result = rosterRows(data, "child_name", 50);
    return !error && result ? { ok: true, data: result } : { ok: false };
  } catch {
    return { ok: false };
  }
}
export async function childAcademies(
  actor: unknown,
  child: unknown,
): Promise<Result<RosterRow[]>> {
  if (!isId(child)) return { ok: false };
  try {
    const client = await clientFor(actor);
    if (!client) return { ok: false };
    const { data, error } = await client.rpc("app_child_academies", {
      p_child_id: child,
    });
    const result = rosterRows(data, "academy_name", 100);
    return !error && result ? { ok: true, data: result } : { ok: false };
  } catch {
    return { ok: false };
  }
}
