import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import CreatedChildrenPanel from "./created-children-panel";
import ChildCreationPanel from "./child-creation-panel";

const mocks = vi.hoisted(() => ({ list: vi.fn(), run: vi.fn(), observe: vi.fn() }));
vi.mock("@/lib/parent/list-created-children", () => ({ listCreatedChildren: mocks.list }));
vi.mock("@/lib/parent/child-creation-journey", () => ({ runChildCreation: mocks.run }));
vi.mock("@/lib/auth/session-observer", () => ({ observeSessionChanges: mocks.observe }));
const actor = "11111111-1111-4111-8111-111111111111";
const request = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee";
const current = { intentId: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", childId: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", name: "Asha", acknowledged: false, priorIntentId: null, requestId: request };

describe("ParentChildPanels", () => {
  beforeEach(() => {
    vi.resetAllMocks(); vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    vi.spyOn(globalThis.crypto, "randomUUID").mockReturnValue(request);
    mocks.observe.mockReturnValue(() => {}); mocks.list.mockResolvedValue({ ok: true, children: [] });
    mocks.run.mockResolvedValueOnce({ ok: true, operation: "status", actorId: actor, current: null })
      .mockResolvedValueOnce({ ok: true, operation: "begin", current, disposition: "created" })
      .mockResolvedValueOnce({ ok: true, operation: "status", actorId: actor, current });
  });
  afterEach(() => { vi.unstubAllEnvs(); vi.restoreAllMocks(); });
  it("marks a previously loaded list stale when a profile request starts", async () => {
    render(<><CreatedChildrenPanel /><ChildCreationPanel /></>);
    fireEvent.click(await screen.findByRole("button", { name: "Load profiles" }));
    await screen.findByText(/no profiles available/i);
    fireEvent.click(await screen.findByRole("button", { name: "Check creation status" }));
    fireEvent.change(await screen.findByLabelText("Child name"), { target: { value: "Asha" } });
    fireEvent.click(screen.getByRole("button", { name: "Create profile" }));
    expect(screen.queryByText(/no profiles available/i)).not.toBeInTheDocument();
    expect(await screen.findByText(/profile list may have changed/i)).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Confirm result" })).toBeInTheDocument();
  });
  it("ignores an earlier list response while creation is pending", async () => {
    let finish!: (value: unknown) => void, finishList!: (value: unknown) => void;
    mocks.list.mockReturnValueOnce(new Promise((resolve) => { finishList = resolve; }));
    mocks.run.mockReset(); mocks.run.mockResolvedValueOnce({ ok: true, operation: "status", actorId: actor, current: null })
      .mockReturnValueOnce(new Promise((resolve) => { finish = resolve; }))
      .mockResolvedValueOnce({ ok: true, operation: "status", actorId: actor, current });
    render(<><CreatedChildrenPanel /><ChildCreationPanel /></>);
    fireEvent.click(await screen.findByRole("button", { name: "Load profiles" }));
    fireEvent.click(await screen.findByRole("button", { name: "Check creation status" }));
    fireEvent.change(await screen.findByLabelText("Child name"), { target: { value: "Asha" } });
    fireEvent.click(screen.getByRole("button", { name: "Create profile" }));
    expect(screen.getByRole("button", { name: "Load profiles" })).toBeDisabled();
    await act(async () => finishList({ ok: true, children: [{ id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", name: "Stale name" }] }));
    expect(screen.queryByText("Stale name")).not.toBeInTheDocument();
    await act(async () => finish({ ok: true, operation: "begin", current, disposition: "created" }));
    expect(await screen.findByRole("button", { name: "Confirm result" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Load profiles" })).toBeEnabled();
    expect(screen.getByText(/profile list may have changed/i)).toBeInTheDocument();
  });
  it("keeps list loading blocked while a creation result is uncertain", async () => {
    mocks.run.mockReset(); mocks.run.mockResolvedValueOnce({ ok: true, operation: "status", actorId: actor, current: null })
      .mockResolvedValueOnce({ ok: false, error: "unavailable" });
    render(<><CreatedChildrenPanel /><ChildCreationPanel /></>);
    fireEvent.click(await screen.findByRole("button", { name: "Check creation status" }));
    fireEvent.change(await screen.findByLabelText("Child name"), { target: { value: "Asha" } });
    fireEvent.click(screen.getByRole("button", { name: "Create profile" }));
    await screen.findByText(/unable to confirm the profile/i);
    expect(screen.getByRole("button", { name: "Load profiles" })).toBeDisabled();
  });

  it("re-enables list loading after the same uncertain request is confirmed", async () => {
    mocks.run.mockReset(); mocks.run.mockResolvedValueOnce({ ok: true, operation: "status", actorId: actor, current: null })
      .mockResolvedValueOnce({ ok: false, error: "unavailable" })
      .mockResolvedValueOnce({ ok: true, operation: "status", actorId: actor, current: null })
      .mockResolvedValueOnce({ ok: true, operation: "begin", current, disposition: "created" })
      .mockResolvedValueOnce({ ok: true, operation: "status", actorId: actor, current });
    render(<><CreatedChildrenPanel /><ChildCreationPanel /></>);
    fireEvent.click(await screen.findByRole("button", { name: "Check creation status" }));
    fireEvent.change(await screen.findByLabelText("Child name"), { target: { value: "Asha" } });
    fireEvent.click(screen.getByRole("button", { name: "Create profile" }));
    await screen.findByText(/unable to confirm the profile/i);
    expect(screen.getByRole("button", { name: "Load profiles" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Check creation status" }));
    fireEvent.click(await screen.findByRole("button", { name: "Retry same request" }));
    expect(await screen.findByRole("button", { name: "Confirm result" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Load profiles" })).toBeEnabled();
  });

  it("explains why the list remains blocked after an uncertain request and session change", async () => {
    const listeners: ((event: string) => void)[] = [];
    mocks.observe.mockImplementation((callback) => { listeners.push(callback); return () => {}; });
    mocks.run.mockReset(); mocks.run.mockResolvedValueOnce({ ok: true, operation: "status", actorId: actor, current: null })
      .mockResolvedValueOnce({ ok: false, error: "unavailable" });
    render(<><CreatedChildrenPanel /><ChildCreationPanel /></>);
    fireEvent.click(await screen.findByRole("button", { name: "Check creation status" }));
    fireEvent.change(await screen.findByLabelText("Child name"), { target: { value: "Asha" } });
    fireEvent.click(screen.getByRole("button", { name: "Create profile" }));
    await screen.findByText(/unable to confirm the profile/i);
    act(() => listeners.forEach((listener) => listener("SIGNED_OUT")));
    expect(screen.getByRole("button", { name: "Load profiles" })).toBeDisabled();
    expect(screen.getByText(/profile request remains unresolved/i)).toBeInTheDocument();
  });

});
