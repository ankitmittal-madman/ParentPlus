import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ChildCreationPanel from "./child-creation-panel";

const mocks = vi.hoisted(() => ({ run: vi.fn(), observe: vi.fn() }));
vi.mock("@/lib/parent/child-creation-journey", () => ({ runChildCreation: mocks.run }));
vi.mock("@/lib/auth/session-observer", () => ({ observeSessionChanges: mocks.observe }));
const actor = "11111111-1111-4111-8111-111111111111";
const intent = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const child = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
const request = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee";
const current = { intentId: intent, childId: child, name: "Asha", acknowledged: false, priorIntentId: null, requestId: request };

describe("ChildCreationPanel", () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.resetAllMocks(); vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    mocks.observe.mockReturnValue(() => {});
    vi.spyOn(globalThis.crypto, "randomUUID").mockReturnValue(request);
    mocks.run.mockResolvedValue({ ok: true, operation: "status", actorId: actor, current: null });
  });
  afterEach(() => { vi.unstubAllEnvs(); vi.restoreAllMocks(); });
  it("requires a deliberate status check before profile entry", async () => {
    render(<ChildCreationPanel />); expect(mocks.run).not.toHaveBeenCalled();
    expect(screen.queryByLabelText("Child name")).not.toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: "Check creation status" }));
    expect(await screen.findByLabelText("Child name")).toBeInTheDocument();
    expect(screen.getByText(/does not verify guardianship/i)).toBeInTheDocument();
  });
  it("creates a profile and requires explicit acknowledgement", async () => {
    mocks.run.mockResolvedValueOnce({ ok: true, operation: "status", actorId: actor, current: null })
      .mockResolvedValueOnce({ ok: true, operation: "begin", current, disposition: "created" })
      .mockResolvedValueOnce({ ok: true, operation: "status", actorId: actor, current });
    render(<ChildCreationPanel />); fireEvent.click(await screen.findByRole("button", { name: "Check creation status" }));
    fireEvent.change(await screen.findByLabelText("Child name"), { target: { value: " Asha " } });
    fireEvent.click(screen.getByRole("button", { name: "Create profile" }));
    expect(await screen.findByRole("button", { name: "Confirm result" })).toBeInTheDocument();
    expect(mocks.run).toHaveBeenNthCalledWith(2, { operation: "begin", expectedActorId: actor, displayName: "Asha", priorIntentId: null, requestId: request });
    expect(mocks.run).toHaveBeenCalledTimes(3);
  });
  it("acknowledges a result only on a separate action and rechecks it", async () => {
    mocks.run.mockResolvedValueOnce({ ok: true, operation: "status", actorId: actor, current })
      .mockResolvedValueOnce({ ok: true, operation: "ack" })
      .mockResolvedValueOnce({ ok: true, operation: "status", actorId: actor, current: { ...current, acknowledged: true } });
    render(<ChildCreationPanel />); fireEvent.click(await screen.findByRole("button", { name: "Check creation status" }));
    fireEvent.click(await screen.findByRole("button", { name: "Confirm result" }));
    expect(await screen.findByRole("button", { name: "Add another profile" })).toBeInTheDocument();
    expect(mocks.run).toHaveBeenNthCalledWith(2, { operation: "ack", expectedActorId: actor, intentId: intent });
  });
  it("uses the confirmed prior intent when adding another profile", async () => {
    const next = { ...current, intentId: "cccccccc-cccc-4ccc-8ccc-cccccccccccc", childId: "dddddddd-dddd-4ddd-8ddd-dddddddddddd", name: "Ravi", priorIntentId: intent };
    mocks.run.mockResolvedValueOnce({ ok: true, operation: "status", actorId: actor, current: { ...current, acknowledged: true, requestId: "cccccccc-cccc-4ccc-8ccc-cccccccccccc" } })
      .mockResolvedValueOnce({ ok: true, operation: "begin", current: next, disposition: "created" })
      .mockResolvedValueOnce({ ok: true, operation: "status", actorId: actor, current: next });
    render(<ChildCreationPanel />); fireEvent.click(await screen.findByRole("button", { name: "Check creation status" }));
    fireEvent.click(await screen.findByRole("button", { name: "Add another profile" }));
    fireEvent.change(screen.getByLabelText("Child name"), { target: { value: "Ravi" } });
    fireEvent.click(screen.getByRole("button", { name: "Create profile" }));
    await screen.findByRole("button", { name: "Confirm result" });
    expect(mocks.run).toHaveBeenNthCalledWith(2, { operation: "begin", expectedActorId: actor, displayName: "Ravi", priorIntentId: intent, requestId: request });
  });
  it("requires another status check after an uncertain write", async () => {
    mocks.run.mockResolvedValueOnce({ ok: true, operation: "status", actorId: actor, current: null }).mockResolvedValueOnce({ ok: false, error: "private provider detail" });
    render(<ChildCreationPanel />); fireEvent.click(await screen.findByRole("button", { name: "Check creation status" }));
    fireEvent.change(await screen.findByLabelText("Child name"), { target: { value: "Asha" } });
    fireEvent.click(screen.getByRole("button", { name: "Create profile" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/unable to confirm/i);
    expect(screen.queryByRole("button", { name: "Create profile" })).not.toBeInTheDocument();
    expect(screen.queryByText(/private provider detail/)).not.toBeInTheDocument();
  });
  it("rejects an unrelated status after a write", async () => {
    mocks.run.mockResolvedValueOnce({ ok: true, operation: "status", actorId: actor, current: null })
      .mockResolvedValueOnce({ ok: true, operation: "begin", current, disposition: "created" })
      .mockResolvedValueOnce({ ok: true, operation: "status", actorId: actor, current: { ...current, intentId: "cccccccc-cccc-4ccc-8ccc-cccccccccccc", name: "Other" } });
    render(<ChildCreationPanel />); fireEvent.click(await screen.findByRole("button", { name: "Check creation status" }));
    fireEvent.change(await screen.findByLabelText("Child name"), { target: { value: "Asha" } });
    fireEvent.click(screen.getByRole("button", { name: "Create profile" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/unable to confirm/i);
    expect(screen.queryByText("Other")).not.toBeInTheDocument();
  });
  it("retries the same request after an unconfirmed attempt in the same session", async () => {
    mocks.run.mockResolvedValueOnce({ ok: true, operation: "status", actorId: actor, current: null })
      .mockResolvedValueOnce({ ok: false, error: "unavailable" })
      .mockResolvedValueOnce({ ok: true, operation: "status", actorId: actor, current: null })
      .mockResolvedValueOnce({ ok: true, operation: "begin", current, disposition: "created" })
      .mockResolvedValueOnce({ ok: true, operation: "status", actorId: actor, current });
    render(<ChildCreationPanel />); fireEvent.click(await screen.findByRole("button", { name: "Check creation status" }));
    fireEvent.change(await screen.findByLabelText("Child name"), { target: { value: "Asha" } });
    fireEvent.click(screen.getByRole("button", { name: "Create profile" }));
    await screen.findByRole("alert"); fireEvent.click(screen.getByRole("button", { name: "Check creation status" }));
    fireEvent.click(await screen.findByRole("button", { name: "Retry same request" }));
    expect(await screen.findByRole("button", { name: "Confirm result" })).toBeInTheDocument();
    expect(mocks.run).toHaveBeenNthCalledWith(4, { operation: "begin", expectedActorId: actor, displayName: "Asha", priorIntentId: null, requestId: request });
  });

  it("does not treat another tab's request as recovery of an uncertain write", async () => {
    mocks.run.mockResolvedValueOnce({ ok: true, operation: "status", actorId: actor, current: null })
      .mockResolvedValueOnce({ ok: false, error: "unavailable" })
      .mockResolvedValueOnce({ ok: true, operation: "status", actorId: actor, current: { ...current, name: "Other", requestId: "ffffffff-ffff-4fff-8fff-ffffffffffff", priorIntentId: null } });
    render(<ChildCreationPanel />); fireEvent.click(await screen.findByRole("button", { name: "Check creation status" }));
    fireEvent.change(await screen.findByLabelText("Child name"), { target: { value: "Asha" } });
    fireEvent.click(screen.getByRole("button", { name: "Create profile" }));
    await screen.findByRole("alert");
    fireEvent.click(screen.getByRole("button", { name: "Check creation status" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/unable to confirm/i);
    expect(screen.queryByText("Other")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Confirm result" })).not.toBeInTheDocument();
  });

  it("binds an interrupted write to the original account in the current page", async () => {
    let notify!: (event: string) => void, finish!: (value: unknown) => void;
    mocks.observe.mockImplementation((callback) => { notify = callback; return () => {}; });
    mocks.run.mockResolvedValueOnce({ ok: true, operation: "status", actorId: actor, current: null })
      .mockReturnValueOnce(new Promise((resolve) => { finish = resolve; }))
      .mockResolvedValueOnce({ ok: false, error: "unavailable" });
    render(<ChildCreationPanel />); fireEvent.click(await screen.findByRole("button", { name: "Check creation status" }));
    fireEvent.change(await screen.findByLabelText("Child name"), { target: { value: "Asha" } });
    fireEvent.click(screen.getByRole("button", { name: "Create profile" }));
    act(() => notify("SIGNED_OUT")); await act(async () => finish({ ok: true, operation: "begin", current, disposition: "created" }));
    expect(screen.queryByText("Asha")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Check creation status" }));
    await waitFor(() => expect(mocks.run).toHaveBeenLastCalledWith({ operation: "status", expectedActorId: actor }));
    expect(screen.queryByLabelText("Child name")).not.toBeInTheDocument();
  });
  it("does not keep a child name for retry after a session change", async () => {
    let notify!: (event: string) => void, finish!: (value: unknown) => void;
    mocks.observe.mockImplementation((callback) => { notify = callback; return () => {}; });
    mocks.run.mockResolvedValueOnce({ ok: true, operation: "status", actorId: actor, current: null })
      .mockReturnValueOnce(new Promise((resolve) => { finish = resolve; }))
      .mockResolvedValueOnce({ ok: true, operation: "status", actorId: actor, current: null });
    render(<ChildCreationPanel />); fireEvent.click(await screen.findByRole("button", { name: "Check creation status" }));
    fireEvent.change(await screen.findByLabelText("Child name"), { target: { value: "Asha" } });
    fireEvent.click(screen.getByRole("button", { name: "Create profile" }));
    act(() => notify("SIGNED_OUT")); await act(async () => finish({ ok: false, error: "unavailable" }));
    fireEvent.click(screen.getByRole("button", { name: "Check creation status" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/unable to confirm/i);
    expect(screen.queryByRole("button", { name: "Retry same request" })).not.toBeInTheDocument();
    expect(screen.queryByText("Asha")).not.toBeInTheDocument();
  });

  it("fails closed if session monitoring is unavailable", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "false"); render(<ChildCreationPanel />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/session monitoring is unavailable/i);
    expect(mocks.run).not.toHaveBeenCalled();
  });
});
