// This untrusted, tab-scoped marker contains identifiers only; the server remains authoritative.
export type RecoveryMarker = { version: 1; actor: string; operation: "begin" | "ack"; priorIntentId: string | null; requestId: string | null };
type ReadResult = { state: "none" } | { state: "unavailable" } | { state: "present"; marker: RecoveryMarker };
const key = "parentplus.child-creation-recovery.v1";
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function valid(value: unknown): value is RecoveryMarker {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const v = value as Record<string, unknown>;
  if (Object.keys(v).sort().join(",") !== "actor,operation,priorIntentId,requestId,version" || v.version !== 1 || typeof v.actor !== "string" || !uuid.test(v.actor)) return false;
  const id = (x: unknown) => typeof x === "string" && uuid.test(x);
  return v.operation === "begin" ? id(v.requestId) && (v.priorIntentId === null || id(v.priorIntentId)) : v.operation === "ack" && id(v.priorIntentId) && v.requestId === null;
}
function same(a: RecoveryMarker, b: RecoveryMarker) {
  return a.actor.toLowerCase() === b.actor.toLowerCase() && a.operation === b.operation && (a.priorIntentId?.toLowerCase() ?? null) === (b.priorIntentId?.toLowerCase() ?? null) && (a.requestId?.toLowerCase() ?? null) === (b.requestId?.toLowerCase() ?? null);
}
export function readRecoveryMarker(): ReadResult {
  try {
    const raw = sessionStorage.getItem(key);
    if (raw === null) return { state: "none" };
    const marker: unknown = JSON.parse(raw);
    return valid(marker) ? { state: "present", marker } : { state: "unavailable" };
  } catch { return { state: "unavailable" }; }
}
export function writeRecoveryMarker(marker: RecoveryMarker): boolean {
  if (!valid(marker)) return false;
  const existing = readRecoveryMarker();
  if (existing.state === "unavailable") return false;
  if (existing.state === "present") return same(existing.marker, marker);
  try {
    sessionStorage.setItem(key, JSON.stringify(marker));
    const stored = readRecoveryMarker();
    return stored.state === "present" && same(stored.marker, marker);
  } catch { return false; }
}
export function clearRecoveryMarker(marker: RecoveryMarker): boolean {
  const existing = readRecoveryMarker();
  if (existing.state !== "present" || !same(existing.marker, marker)) return false;
  try { sessionStorage.removeItem(key); return readRecoveryMarker().state === "none"; }
  catch { return false; }
}
