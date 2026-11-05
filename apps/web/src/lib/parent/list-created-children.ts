"use server";

import { createClient } from "@/lib/supabase/server";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
type Result = { ok: true; children: { id: string; name: string }[] } | { ok: false; error: string };

export async function listCreatedChildren(): Promise<Result> {
  const unavailable = { ok: false, error: "Unable to load profiles. Please try again." } as const;
  if (process.env.PARENTPLUS_ENABLE_PARENT_CHILD_LIST !== "true") return unavailable;
  try {
    const client = await createClient();
    const { data: identity, error: identityError } = await client.auth.getUser();
    const actor = identity.user?.id;
    if (identityError || typeof actor !== "string" || !UUID.test(actor)) return unavailable;
    const { data, error } = await client.rpc("app_list_created_children");
    if (error || !Array.isArray(data) || data.length > 100) return unavailable;
    const children: { id: string; name: string }[] = [];
    const seen = new Set<string>();
    for (const row of data) {
      if (!row || typeof row !== "object" || Array.isArray(row)) return unavailable;
      const value = row as Record<string, unknown>;
      if (typeof value.child_id !== "string" || !UUID.test(value.child_id)
          || typeof value.display_name !== "string" || !value.display_name.trim()
          || Array.from(value.display_name).length > 120 || seen.has(value.child_id.toLowerCase())) return unavailable;
      seen.add(value.child_id.toLowerCase());
      children.push({ id: value.child_id, name: value.display_name });
    }
    return { ok: true, children };
  } catch { return unavailable; }
}
