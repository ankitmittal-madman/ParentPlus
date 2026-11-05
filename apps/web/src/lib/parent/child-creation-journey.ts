"use server";

import { createClient } from "@/lib/supabase/server";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const isId = (value: unknown): value is string => typeof value === "string" && UUID.test(value);
type Current = { intentId: string; childId: string; name: string; acknowledged: boolean; priorIntentId: string | null; requestId: string };
type Result =
  | { ok: false; error: string }
  | { ok: true; operation: "status"; actorId: string; current: Current | null }
  | { ok: true; operation: "begin"; current: Current; disposition: "created" | "existing" }
  | { ok: true; operation: "ack" }
  | { ok: true; operation: "fence"; actorId: string; disposition: "fenced" | "created" | "unknown" }
  | { ok: true; operation: "history"; actorId: string; disposition: "found" | "unknown" };

function parseCurrent(row: unknown): Current | null {
  if (!row || typeof row !== "object" || Array.isArray(row)) return null;
  const value = row as Record<string, unknown>;
  if (!isId(value.intent_id) || !isId(value.child_id) || typeof value.display_name !== "string"
      || !value.display_name.trim() || Array.from(value.display_name).length > 120
      || typeof value.acknowledged !== "boolean" || !isId(value.request_id)
      || (value.prior_intent_id !== null && !isId(value.prior_intent_id))) return null;
  return { intentId: value.intent_id, childId: value.child_id, name: value.display_name, acknowledged: value.acknowledged, priorIntentId: value.prior_intent_id, requestId: value.request_id };
}

export async function runChildCreation(input: unknown): Promise<Result> {
  const unavailable = { ok: false, error: "Unable to confirm the profile. Check its status before trying again." } as const;
  const invalid = { ok: false, error: "Check the profile details." } as const;
  if (process.env.PARENTPLUS_ENABLE_CHILD_CREATION !== "true" || process.env.PARENTPLUS_ENABLE_PARENT_CHILD_LIST !== "true") return unavailable;
  if (!input || typeof input !== "object" || Array.isArray(input)) return invalid;
  const value = input as Record<string, unknown>;
  const { operation, expectedActorId } = value;
  if (operation !== "status" && operation !== "begin" && operation !== "ack" && operation !== "fence" && operation !== "history") return invalid;
  if ((operation !== "status" || expectedActorId !== undefined) && !isId(expectedActorId)) return invalid;
  let name = "";
  if (operation === "begin") {
    if (typeof value.displayName !== "string" || !isId(value.requestId) || (value.priorIntentId !== null && !isId(value.priorIntentId))) return invalid;
    name = value.displayName.trim();
    if (!name || Array.from(name).length > 120) return invalid;
  }
  if (operation === "ack" && !isId(value.intentId)) return invalid;
  if ((operation === "fence" || operation === "history") && (!isId(value.requestId) || (value.priorIntentId !== null && !isId(value.priorIntentId)))) return invalid;
  try {
    const client = await createClient();
    const { data: identity, error: identityError } = await client.auth.getUser();
    const actor = identity.user?.id;
    if (identityError || !isId(actor) || (isId(expectedActorId) && actor.toLowerCase() !== expectedActorId.toLowerCase())) return unavailable;
    if (operation === "history") {
      const { data, error } = await client.rpc("app_historical_child_creation", { p_prior_intent_id: value.priorIntentId, p_request_id: value.requestId });
      if (error || (data !== "found" && data !== "unknown")) return unavailable;
      return { ok: true, operation, actorId: actor, disposition: data };
    }
    if (operation === "fence") {
      const { data, error } = await client.rpc("app_fence_child_creation", { p_prior_intent_id: value.priorIntentId, p_request_id: value.requestId });
      if (error || (data !== "fenced" && data !== "created" && data !== "unknown")) return unavailable;
      return { ok: true, operation, actorId: actor, disposition: data };
    }
    if (operation === "status") {
      const { data, error } = await client.rpc("app_current_child_creation");
      if (error || !Array.isArray(data) || data.length > 1) return unavailable;
      if (data.length === 0) return { ok: true, operation, actorId: actor, current: null };
      const current = parseCurrent(data[0]);
      return current ? { ok: true, operation, actorId: actor, current } : unavailable;
    }
    if (operation === "begin") {
      const { data, error } = await client.rpc("app_begin_child_creation", { p_display_name: name, p_prior_intent_id: value.priorIntentId, p_request_id: value.requestId });
      if (error || !Array.isArray(data) || data.length !== 1) return unavailable;
      const current = parseCurrent(data[0]);
      const disposition = data[0]?.disposition;
      if (!current || current.name !== name || current.requestId.toLowerCase() !== (value.requestId as string).toLowerCase()
          || (current.priorIntentId?.toLowerCase() ?? null) !== (isId(value.priorIntentId) ? value.priorIntentId.toLowerCase() : null)
          || (disposition !== "created" && disposition !== "existing")
          || (disposition === "created" && current.acknowledged)) return unavailable;
      return { ok: true, operation, current, disposition };
    }
    const { data, error } = await client.rpc("app_ack_child_creation", { p_intent_id: value.intentId });
    return !error && data === true ? { ok: true, operation: "ack" } : unavailable;
  } catch { return unavailable; }
}
