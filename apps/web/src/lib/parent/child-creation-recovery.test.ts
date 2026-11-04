import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearRecoveryMarker, readRecoveryMarker, writeRecoveryMarker } from "./child-creation-recovery";

const actor = "11111111-1111-4111-8111-111111111111";
const request = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee";
const intent = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const marker = { version: 1 as const, actor, operation: "begin" as const, priorIntentId: null, requestId: request };

describe("childCreationRecovery", () => {
  beforeEach(() => sessionStorage.clear());
  afterEach(() => { vi.restoreAllMocks(); sessionStorage.clear(); });
  it("reports no recovery marker in a fresh tab", () => {
    expect(readRecoveryMarker()).toEqual({ state: "none" });
  });
  it("stores and reads only the validated request reference", () => {
    expect(writeRecoveryMarker(marker)).toBe(true);
    expect(readRecoveryMarker()).toEqual({ state: "present", marker });
    expect(JSON.stringify(sessionStorage)).not.toContain("Asha");
  });
  it("does not overwrite an unresolved different request", () => {
    expect(writeRecoveryMarker(marker)).toBe(true);
    expect(writeRecoveryMarker({ ...marker, requestId: intent })).toBe(false);
    expect(readRecoveryMarker()).toEqual({ state: "present", marker });
  });
  it("permits reusing the exact existing marker", () => {
    expect(writeRecoveryMarker(marker)).toBe(true);
    expect(writeRecoveryMarker(marker)).toBe(true);
  });
  it("rejects malformed, unexpected or unsupported stored data", () => {
    for (const data of ["not json", JSON.stringify({ ...marker, version: 2 }), JSON.stringify({ ...marker, displayName: "Asha" }), JSON.stringify({ ...marker, requestId: null })]) {
      sessionStorage.clear(); sessionStorage.setItem("parentplus.child-creation-recovery.v1", data);
      expect(readRecoveryMarker()).toEqual({ state: "unavailable" }); expect(writeRecoveryMarker(marker)).toBe(false);
    }
  });
  it("clears only the exact confirmed marker", () => {
    expect(writeRecoveryMarker(marker)).toBe(true);
    expect(clearRecoveryMarker({ ...marker, requestId: intent })).toBe(false);
    expect(readRecoveryMarker().state).toBe("present");
    expect(clearRecoveryMarker(marker)).toBe(true); expect(readRecoveryMarker()).toEqual({ state: "none" });
  });
  it("accepts acknowledgement markers with a valid intent", () => {
    const ack = { version: 1 as const, actor, operation: "ack" as const, priorIntentId: intent, requestId: null };
    expect(writeRecoveryMarker(ack)).toBe(true); expect(readRecoveryMarker()).toEqual({ state: "present", marker: ack });
  });
  it("fails closed when storage cannot be read or written", () => {
    const get = vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => { throw new Error("blocked"); });
    expect(readRecoveryMarker()).toEqual({ state: "unavailable" }); expect(writeRecoveryMarker(marker)).toBe(false);
    get.mockRestore();
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("blocked"); });
    expect(writeRecoveryMarker(marker)).toBe(false);
  });
  it("does not report successful removal when storage cannot remove", () => {
    expect(writeRecoveryMarker(marker)).toBe(true);
    vi.spyOn(Storage.prototype, "removeItem").mockImplementation(() => { throw new Error("blocked"); });
    expect(clearRecoveryMarker(marker)).toBe(false);
  });
});
