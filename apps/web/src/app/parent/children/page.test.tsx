import { Suspense, type ReactElement } from "react";
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ParentChildrenPage, { ParentChildrenGate } from "./page";
import ParentClassesPanel from "@/modules/enrollments/parent-classes-panel";
import CreatedChildrenPanel from "./created-children-panel";
import ChildCreationPanel from "./child-creation-panel";
import ParentConnectionsPanel from "@/modules/families/parent-connections-panel";

const mocks = vi.hoisted(() => ({ connection: vi.fn() }));
vi.mock("next/server", () => ({ connection: mocks.connection }));

describe("ParentChildrenPage", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.clearAllMocks();
  });
  it("links profiles back to parent home while preserving request-gated management", () => {
    const page = ParentChildrenPage();
    render(<>{page.props.children.filter((child: ReactElement) => child.type !== Suspense)}</>);
    expect(screen.getByRole("link", { name: "Parent home" })).toHaveAttribute("href", "/parent");
    expect(screen.getByRole("heading", { name: "Parent profiles" })).toBeVisible();
  });
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
    expect(result.props.children[0].type).toBe(CreatedChildrenPanel);
    expect(result.props.children[1].type).toBe(ParentConnectionsPanel);
    expect(result.props.children[2].type).toBe(ParentClassesPanel);
  });
  it("exposes creation only when both server controls are explicitly enabled", async () => {
    vi.stubEnv("PARENTPLUS_ENABLE_PARENT_CHILD_LIST", "true");
    vi.stubEnv("PARENTPLUS_ENABLE_CHILD_CREATION", "true");
    const result = await ParentChildrenGate();
    expect(result.props.children[0].type).toBe(CreatedChildrenPanel);
    expect(result.props.children[1].type).toBe(ChildCreationPanel);
    expect(result.props.children[3].type).toBe(ParentClassesPanel);
  });
  it("does not expose creation when the parent page is disabled", async () => {
    vi.stubEnv("PARENTPLUS_ENABLE_PARENT_CHILD_LIST", "false");
    vi.stubEnv("PARENTPLUS_ENABLE_CHILD_CREATION", "true");
    const result = await ParentChildrenGate();
    expect(result.type).not.toBe(ChildCreationPanel);
    expect(typeof result.props.children).toBe("string");
  });
});
