import { beforeEach, expect, it, vi } from "vitest";
import { readPending, writePending, clearPending, type PendingOperation } from "./pending";
const a = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", b = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
const value: PendingOperation = { format: 1, actorId: a, requestId: b, payload: { operation: "save_attendance", workspace_id: a, session_id: b, expected_session_version: 1, expected_sheet_version: 0, roster_token: "a".repeat(64), records: [{ enrollment_id: a, child_id: b, status: "late" }] } };
beforeEach(() => {
  vi.restoreAllMocks();
  sessionStorage.clear();
});
it("stores the immutable operation for reload and isolates actor and operation slots", () => {
  expect(readPending(a, "attendance")).toEqual({ kind: "none" });
  expect(writePending(value)).toBe("stored");
  expect(readPending(a, "attendance")).toEqual({ kind: "pending", value });
  expect(readPending(b, "attendance")).toEqual({ kind: "none" });
  expect(readPending(a, "signal")).toEqual({ kind: "none" });
  expect(writePending(value)).toBe("same");
});
it("blocks replacement requests and changed full payload without losing the original", () => {
  writePending(value);
  expect(writePending({ ...value, requestId: a })).toBe("blocked");
  expect(writePending({ ...value, payload: { ...value.payload, expected_session_version: 2 } })).toBe("blocked");
  expect(readPending(a, "attendance")).toEqual({ kind: "pending", value });
});
it("clears only the complete expected actor operation key and canonical body", () => {
  writePending(value);
  clearPending({ ...value, payload: { ...value.payload, expected_session_version: 2 } });
  expect(readPending(a, "attendance").kind).toBe("pending");
  const signal: PendingOperation = { ...value, payload: { operation: "send_parent_signal", child_id: b, workspace_id: a, session_id: b, expected_session_version: 1, type: "running_late", reason: null } };
  writePending(signal);
  clearPending(value);
  expect(readPending(a, "attendance")).toEqual({ kind: "none" });
  expect(readPending(a, "signal")).toEqual({ kind: "pending", value: signal });
  clearPending(signal);
  expect(readPending(a, "signal")).toEqual({ kind: "none" });
});
it("quarantines corrupt wrong-actor and wrong-operation data without overwriting it", () => {
  for (const raw of ["{", JSON.stringify({ ...value, actorId: b }), JSON.stringify({ ...value, format: 2 }), JSON.stringify({ ...value, payload: { ...value.payload, actor_id: a } }), JSON.stringify({ ...value, payload: { operation: "send_parent_signal" } })]) {
    sessionStorage.setItem(`parentplus:attendance-pending:${a}`, raw);
    expect(readPending(a, "attendance")).toEqual({ kind: "corrupt" });
    expect(writePending(value)).toBe("blocked");
    clearPending(value);
    expect(sessionStorage.getItem(`parentplus:attendance-pending:${a}`)).toBe(raw);
  }
});
it("distinguishes unavailable storage from absent and never claims durable persistence", () => {
  vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
    throw Error("denied");
  });
  expect(readPending(a, "attendance")).toEqual({ kind: "unavailable" });
  expect(writePending(value)).toBe("unavailable");
  expect(() => clearPending(value)).not.toThrow();
});
it("reports failed persistence and preserves the slot when removal is unavailable", () => {
  const failedPersistence = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
    throw Error("quota");
  });
  expect(writePending(value)).toBe("unavailable");
  failedPersistence.mockRestore();
  expect(writePending(value)).toBe("stored");
  const original = sessionStorage.getItem(`parentplus:attendance-pending:${a}`);
  const failedRemoval = vi.spyOn(Storage.prototype, "removeItem").mockImplementation(() => {
    throw Error("removal denied");
  });
  expect(() => clearPending(value)).not.toThrow();
  expect(sessionStorage.getItem(`parentplus:attendance-pending:${a}`)).toBe(original);
  expect(readPending(a, "attendance")).toEqual({ kind: "pending", value });
  expect(writePending({ ...value, requestId: a })).toBe("blocked");
  failedRemoval.mockRestore();
  clearPending(value);
  expect(readPending(a, "attendance")).toEqual({ kind: "none" });
});
it("retains immutable memory fallback through view remounts and clears by complete identity", async () => {
  const { retainVolatilePending, readVolatilePending } = await import("./pending");
  expect(retainVolatilePending(value)).toBe(true);
  expect(retainVolatilePending({ ...value, requestId: a })).toBe(false);
  expect(readVolatilePending(a, "attendance")).toEqual(value);
  clearPending({ ...value, requestId: a });
  expect(readVolatilePending(a, "attendance")).toEqual(value);
  clearPending(value);
  expect(readVolatilePending(a, "attendance")).toBeNull();
});
