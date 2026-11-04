import { afterEach, describe, expect, it, vi } from "vitest";
import { ParentChildrenGate } from "./page";
import CreatedChildrenPanel from "./created-children-panel";

const mocks = vi.hoisted(() => ({ connection: vi.fn() }));
vi.mock("next/server", () => ({ connection: mocks.connection }));

describe("ParentChildrenPage", () => {
  afterEach(() => { vi.unstubAllEnvs(); vi.clearAllMocks(); });
  it("uses request-time configuration and hides the panel by default", async () => {
    vi.stubEnv("PARENTPLUS_ENABLE_PARENT_CHILD_LIST", "false");
    const result = await ParentChildrenGate();
    expect(mocks.connection).toHaveBeenCalledOnce();
    expect(result.type).not.toBe(CreatedChildrenPanel);
  });
  it("exposes the read-only panel only when explicitly enabled", async () => {
    vi.stubEnv("PARENTPLUS_ENABLE_PARENT_CHILD_LIST", "true");
    const result = await ParentChildrenGate();
    expect(mocks.connection).toHaveBeenCalledOnce();
    expect(result.type).toBe(CreatedChildrenPanel);
  });
});
