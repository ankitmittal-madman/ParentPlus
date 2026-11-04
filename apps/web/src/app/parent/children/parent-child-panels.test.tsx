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
    sessionStorage.clear();
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

  it("recovers an uncertain request after remount without storing the child name", async () => {
    mocks.run.mockReset();
    mocks.run.mockResolvedValueOnce({ ok: true, operation: "status", actorId: actor, current: null })
      .mockResolvedValueOnce({ ok: false, error: "unavailable" });
    const view = render(<><CreatedChildrenPanel /><ChildCreationPanel /></>);
    fireEvent.click(await screen.findByRole("button", { name: "Check creation status" }));
    fireEvent.change(await screen.findByLabelText("Child name"), { target: { value: "Asha" } });
    fireEvent.click(screen.getByRole("button", { name: "Create profile" }));
    await screen.findByText(/unable to confirm the profile/i);
    expect(sessionStorage.getItem("parentplus.child-creation-recovery.v1")).not.toContain("Asha");
    view.unmount();
    mocks.run.mockResolvedValueOnce({ ok: true, operation: "status", actorId: actor, current });
    render(<><CreatedChildrenPanel /><ChildCreationPanel /></>);
    expect(await screen.findByRole("button", { name: "Load profiles" })).toBeDisabled();
    fireEvent.click(await screen.findByRole("button", { name: "Check creation status" }));
    expect(await screen.findByRole("button", { name: "Confirm result" })).toBeInTheDocument();
    expect(mocks.run).toHaveBeenLastCalledWith({ operation: "status", expectedActorId: actor });
    expect(sessionStorage.length).toBe(0);
    expect(screen.getByRole("button", { name: "Load profiles" })).toBeEnabled();
  });

  it("does not submit a profile if recovery storage cannot be written", async () => {
    render(<><CreatedChildrenPanel /><ChildCreationPanel /></>);
    fireEvent.click(await screen.findByRole("button", { name: "Check creation status" }));
    fireEvent.change(await screen.findByLabelText("Child name"), { target: { value: "Asha" } });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("blocked"); });
    fireEvent.click(screen.getByRole("button", { name: "Create profile" }));
    expect(await screen.findByText(/recovery information is unavailable/i)).toBeInTheDocument();
    expect(mocks.run).toHaveBeenCalledTimes(1);
  });

  it("keeps the list and new requests blocked when restored status is empty", async () => {
    sessionStorage.setItem("parentplus.child-creation-recovery.v1", JSON.stringify({ version: 1, actor, operation: "begin", priorIntentId: null, requestId: request }));
    mocks.run.mockReset(); mocks.run.mockResolvedValueOnce({ ok: true, operation: "status", actorId: actor, current: null });
    render(<><CreatedChildrenPanel /><ChildCreationPanel /></>);
    expect(await screen.findByRole("button", { name: "Load profiles" })).toBeDisabled();
    fireEvent.click(await screen.findByRole("button", { name: "Check creation status" }));
    expect(await screen.findByText(/do not start another/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retry same request" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Child name")).not.toBeInTheDocument();
  });

  it("keeps recovery locked if confirmation cannot remove the marker", async () => {
    sessionStorage.setItem("parentplus.child-creation-recovery.v1", JSON.stringify({ version: 1, actor, operation: "begin", priorIntentId: null, requestId: request }));
    mocks.run.mockReset(); mocks.run.mockResolvedValueOnce({ ok: true, operation: "status", actorId: actor, current });
    vi.spyOn(Storage.prototype, "removeItem").mockImplementation(() => { throw new Error("blocked"); });
    render(<><CreatedChildrenPanel /><ChildCreationPanel /></>);
    fireEvent.click(await screen.findByRole("button", { name: "Check creation status" }));
    expect(await screen.findByText(/unable to complete recovery/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Load profiles" })).toBeDisabled();
    expect(screen.queryByText("Profile: Asha")).not.toBeInTheDocument();
  });

  it("fails closed on invalid stored recovery data", async () => {
    sessionStorage.setItem("parentplus.child-creation-recovery.v1", "invalid");
    render(<><CreatedChildrenPanel /><ChildCreationPanel /></>);
    expect(await screen.findByText(/saved request information is unavailable/i)).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Load profiles" })).toBeDisabled();
    expect(mocks.run).not.toHaveBeenCalled();
  });

  it("blocks the read-only list when creation is disabled after an unresolved request", async () => {
    sessionStorage.setItem("parentplus.child-creation-recovery.v1", JSON.stringify({ version: 1, actor, operation: "begin", priorIntentId: null, requestId: request }));
    render(<CreatedChildrenPanel />);
    expect(await screen.findByRole("button", { name: "Load profiles" })).toBeDisabled();
    expect(mocks.list).not.toHaveBeenCalled();
  });

  it("allows a fresh attempt after a storage write failure is resolved and status is checked", async () => {
    mocks.run.mockReset();
    mocks.run.mockResolvedValueOnce({ ok: true, operation: "status", actorId: actor, current: null })
      .mockResolvedValueOnce({ ok: true, operation: "status", actorId: actor, current: null });
    render(<><CreatedChildrenPanel /><ChildCreationPanel /></>);
    fireEvent.click(await screen.findByRole("button", { name: "Check creation status" }));
    fireEvent.change(await screen.findByLabelText("Child name"), { target: { value: "Asha" } });
    const storage = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("blocked"); });
    fireEvent.click(screen.getByRole("button", { name: "Create profile" }));
    expect(await screen.findByText(/recovery information is unavailable/i)).toBeInTheDocument();
    expect(mocks.run).toHaveBeenCalledTimes(1);
    storage.mockRestore();
    fireEvent.click(screen.getByRole("button", { name: "Check creation status" }));
    expect(await screen.findByLabelText("Child name")).toBeInTheDocument();
    expect(mocks.run).toHaveBeenCalledTimes(2);
  });

  it("retries the same unacknowledged intent after reload and unlocks only after confirmation", async () => {
    const key = "parentplus.child-creation-recovery.v1";
    sessionStorage.setItem(key, JSON.stringify({ version: 1, actor, operation: "ack", priorIntentId: current.intentId, requestId: null }));
    mocks.run.mockReset();
    mocks.run.mockResolvedValueOnce({ ok: true, operation: "status", actorId: actor, current })
      .mockResolvedValueOnce({ ok: true, operation: "ack" })
      .mockResolvedValueOnce({ ok: true, operation: "status", actorId: actor, current: { ...current, acknowledged: true } });
    render(<><CreatedChildrenPanel /><ChildCreationPanel /></>);
    fireEvent.click(await screen.findByRole("button", { name: "Check creation status" }));
    const retry = await screen.findByRole("button", { name: "Retry confirmation" });
    expect(screen.getByRole("button", { name: "Load profiles" })).toBeDisabled();
    fireEvent.click(retry);
    expect(await screen.findByText("Result confirmed")).toBeInTheDocument();
    expect(mocks.run).toHaveBeenNthCalledWith(2, { operation: "ack", expectedActorId: actor, intentId: current.intentId });
    expect(sessionStorage.getItem(key)).toBeNull();
    expect(screen.getByRole("button", { name: "Load profiles" })).toBeEnabled();
  });

  it("does not offer confirmation retry for a different actor or intent", async () => {
    const key = "parentplus.child-creation-recovery.v1";
    sessionStorage.setItem(key, JSON.stringify({ version: 1, actor, operation: "ack", priorIntentId: current.intentId, requestId: null }));
    mocks.run.mockReset().mockResolvedValueOnce({ ok: true, operation: "status", actorId: "22222222-2222-4222-8222-222222222222", current })
      .mockResolvedValueOnce({ ok: true, operation: "status", actorId: actor, current: { ...current, intentId: "cccccccc-cccc-4ccc-8ccc-cccccccccccc" } });
    render(<><CreatedChildrenPanel /><ChildCreationPanel /></>);
    fireEvent.click(await screen.findByRole("button", { name: "Check creation status" }));
    await screen.findByText(/sign in to the original account/i);
    expect(screen.queryByRole("button", { name: "Retry confirmation" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Check creation status" }));
    await screen.findByText(/do not start another/i);
    expect(screen.queryByRole("button", { name: "Retry confirmation" })).not.toBeInTheDocument();
    expect(mocks.run).toHaveBeenCalledTimes(2);
    expect(sessionStorage.getItem(key)).not.toBeNull();
  });

  it("keeps the marker and list locked when a confirmation retry fails", async () => {
    const key = "parentplus.child-creation-recovery.v1";
    sessionStorage.setItem(key, JSON.stringify({ version: 1, actor, operation: "ack", priorIntentId: current.intentId, requestId: null }));
    mocks.run.mockReset().mockResolvedValueOnce({ ok: true, operation: "status", actorId: actor, current })
      .mockResolvedValueOnce({ ok: false, error: "unavailable" });
    render(<><CreatedChildrenPanel /><ChildCreationPanel /></>);
    fireEvent.click(await screen.findByRole("button", { name: "Check creation status" }));
    fireEvent.click(await screen.findByRole("button", { name: "Retry confirmation" }));
    await screen.findByText(/unable to confirm the profile/i);
    expect(sessionStorage.getItem(key)).not.toBeNull();
    expect(screen.getByRole("button", { name: "Load profiles" })).toBeDisabled();
    expect(screen.queryByText("Result confirmed")).not.toBeInTheDocument();
  });

  it("ignores an acknowledgement response after a session change", async () => {
    const key = "parentplus.child-creation-recovery.v1";
    sessionStorage.setItem(key, JSON.stringify({ version: 1, actor, operation: "ack", priorIntentId: current.intentId, requestId: null }));
    const listeners: ((event: string) => void)[] = [];
    mocks.observe.mockImplementation((callback) => { listeners.push(callback); return () => {}; });
    let finish!: (value: unknown) => void;
    mocks.run.mockReset().mockResolvedValueOnce({ ok: true, operation: "status", actorId: actor, current })
      .mockReturnValueOnce(new Promise((resolve) => { finish = resolve; }));
    render(<><CreatedChildrenPanel /><ChildCreationPanel /></>);
    fireEvent.click(await screen.findByRole("button", { name: "Check creation status" }));
    fireEvent.click(await screen.findByRole("button", { name: "Retry confirmation" }));
    act(() => listeners.forEach((listener) => listener("SIGNED_OUT")));
    await act(async () => finish({ ok: true, operation: "ack" }));
    expect(mocks.run).toHaveBeenCalledTimes(2);
    expect(sessionStorage.getItem(key)).not.toBeNull();
    expect(screen.getByRole("button", { name: "Load profiles" })).toBeDisabled();
    expect(screen.queryByText("Result confirmed")).not.toBeInTheDocument();
  });

  it("explains unavailable browser storage without sending requests or exposing profiles", async () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => { throw new Error("blocked"); });
    render(<><CreatedChildrenPanel /><ChildCreationPanel /></>);
    expect(await screen.findByText(/saved request information is unavailable/i)).toHaveTextContent(/browser storage/i);
    expect(await screen.findByRole("button", { name: "Load profiles" })).toBeDisabled();
    expect(screen.getByText(/list cannot be loaded until browser storage can be checked/i)).toBeInTheDocument();
    fireEvent.focus(window);
    expect(screen.getByText(/list cannot be loaded until browser storage can be checked/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Check creation status" })).not.toBeInTheDocument();
    expect(mocks.run).not.toHaveBeenCalled();
    expect(mocks.list).not.toHaveBeenCalled();
  });

});
