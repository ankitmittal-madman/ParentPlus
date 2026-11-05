import { afterEach, describe, expect, it, vi } from "vitest";
import { ParentChildrenGate } from "./page";
import CreatedChildrenPanel from "./created-children-panel";
import ChildCreationPanel from "./child-creation-panel";

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
    vi.stubEnv("PARENTPLUS_ENABLE_CHILD_CREATION", "false");
    const result = await ParentChildrenGate();
    expect(mocks.connection).toHaveBeenCalledOnce();
    expect(result.type).toBe(CreatedChildrenPanel);
  });
  it("exposes creation only when both server controls are explicitly enabled", async () => {
    vi.stubEnv("PARENTPLUS_ENABLE_PARENT_CHILD_LIST", "true");
    vi.stubEnv("PARENTPLUS_ENABLE_CHILD_CREATION", "true");
    const result = await ParentChildrenGate();
    expect(result.props.children[0].type).toBe(CreatedChildrenPanel);
    expect(result.props.children[1].type).toBe(ChildCreationPanel);
  });
  it("does not expose creation when the parent page is disabled", async () => {
    vi.stubEnv("PARENTPLUS_ENABLE_PARENT_CHILD_LIST", "false");
    vi.stubEnv("PARENTPLUS_ENABLE_CHILD_CREATION", "true");
    const result = await ParentChildrenGate();
    expect(result.type).not.toBe(ChildCreationPanel);
    expect(typeof result.props.children).toBe("string");
  });

});
