import { canonicalAttendancePayload, canonicalSignalPayload, type AttendancePayload, type SignalPayload } from "./contracts";
import { object, uuid, id, exact } from "./validation";
export type PendingOperation = {
  format: 1;
  actorId: string;
  requestId: string;
  payload: AttendancePayload | SignalPayload;
};
export type PendingRead = {
  kind: "none";
} | {
  kind: "pending";
  value: PendingOperation;
} | {
  kind: "corrupt";
} | {
  kind: "unavailable";
};
export type PendingWrite = "stored" | "same" | "blocked" | "unavailable";
type Operation = "attendance" | "signal";
// Deliberately tab-memory only when browser storage is unavailable.
const volatile = new Map<string, PendingOperation>();
const operation = (v: PendingOperation): Operation => v.payload.operation === "save_attendance" ? "attendance" : "signal";
const key = (actor: string, op: Operation) => `parentplus:${op}-pending:${id(actor)}`;
function decode(v: unknown): PendingOperation | null {
  if (!object(v) || !exact(v, ["format", "actorId", "requestId", "payload"]) || v.format !== 1 || !uuid(v.actorId) || !uuid(v.requestId))
    return null;
  const payload = canonicalAttendancePayload(v.payload) ?? canonicalSignalPayload(v.payload);
  return payload ? { format: 1, actorId: id(v.actorId), requestId: id(v.requestId), payload } : null;
}
const equal = (a: PendingOperation, b: PendingOperation) => JSON.stringify(a) === JSON.stringify(b);
export function readPending(actorId: string, op: Operation): PendingRead {
  if (!uuid(actorId))
    return { kind: "corrupt" };
  try {
    const raw = sessionStorage.getItem(key(actorId, op));
    if (raw === null)
      return { kind: "none" };
    let value: PendingOperation | null;
    try {
      value = decode(JSON.parse(raw));
    }
    catch {
      return { kind: "corrupt" };
    }
    return value && value.actorId === id(actorId) && operation(value) === op ? { kind: "pending", value } : { kind: "corrupt" };
  }
  catch {
    return { kind: "unavailable" };
  }
}
export function writePending(input: PendingOperation): PendingWrite {
  const value = decode(input);
  if (!value)
    return "blocked";
  const existing = readPending(value.actorId, operation(value));
  if (existing.kind === "unavailable")
    return "unavailable";
  if (existing.kind === "corrupt")
    return "blocked";
  if (existing.kind === "pending")
    return equal(existing.value, value) ? "same" : "blocked";
  try {
    sessionStorage.setItem(key(value.actorId, operation(value)), JSON.stringify(value));
    return "stored";
  }
  catch {
    return "unavailable";
  }
}
export function clearPending(input: PendingOperation): void {
  const expected = decode(input);
  if (!expected)
    return;
  const memoryKey = key(expected.actorId, operation(expected));
  const memory = volatile.get(memoryKey);
  if (memory && equal(memory, expected))
    volatile.delete(memoryKey);
  const existing = readPending(expected.actorId, operation(expected));
  if (existing.kind === "pending" && equal(existing.value, expected))
    try {
      sessionStorage.removeItem(key(expected.actorId, operation(expected)));
    }
    catch {
      /* Retaining a resolved key is safer than clearing another operation. */
    }
}
export function retainVolatilePending(input: PendingOperation): boolean {
  const value = decode(input);
  if (!value)
    return false;
  const k = key(value.actorId, operation(value));
  const existing = volatile.get(k);
  if (existing && !equal(existing, value))
    return false;
  volatile.set(k, value);
  return true;
}
export function readVolatilePending(actorId: string, op: Operation): PendingOperation | null {
  const value = volatile.get(key(actorId, op));
  return value ? decode(value) : null;
}
