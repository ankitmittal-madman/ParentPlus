import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import CreatedChildrenPanel from "./created-children-panel";
import ChildCreationPanel from "./child-creation-panel";

// Only the provider and session observer are simulated. Both server actions and
// both React panels are the real application modules; no network is used.
const mocks = vi.hoisted(() => ({ createClient: vi.fn(), getUser: vi.fn(), rpc: vi.fn(), observe: vi.fn() }));
vi.mock("@/lib/supabase/server", () => ({ createClient: mocks.createClient }));
vi.mock("@/lib/auth/session-observer", () => ({ observeSessionChanges: mocks.observe }));

const actor = "11111111-1111-4111-8111-111111111111";
const other = "22222222-2222-4222-8222-222222222222";
const request = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee";
const nextRequest = "dddddddd-dddd-4ddd-8ddd-dddddddddddd";
type Row = { intent_id: string; child_id: string; display_name: string; acknowledged: boolean; prior_intent_id: string | null; request_id: string };

function syntheticProvider() {
  const ids = [
    { intent: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", child: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb" },
    { intent: "cccccccc-cccc-4ccc-8ccc-cccccccccccc", child: "ffffffff-ffff-4fff-8fff-ffffffffffff" },
  ];
  let current: Row | null = null;
  const old: Row[] = [];
  const children: Row[] = [];
  let lostBegin = false;
  let failBeforeBegin = false;
  let historyAccess = true;
  const fenced = new Set<string>();
  const rpc = vi.fn(async (operation: string, params?: Record<string, unknown>) => {
    if (operation === "app_current_child_creation") return { data: current ? [{ ...current }] : [], error: null };
    if (operation === "app_list_created_children") return { data: children.map(({ child_id, display_name }) => ({ child_id, display_name })), error: null };
    if (operation === "app_begin_child_creation") {
      if (failBeforeBegin) { failBeforeBegin = false; return { data: null, error: { message: "synthetic request not delivered" } }; }
      if (fenced.has(String(params?.p_request_id))) return { data: null, error: { message: "fenced" } };
      const pair = ids[children.length];
      if (!pair || (current && (!current.acknowledged || params?.p_prior_intent_id !== current.intent_id)) || (!current && params?.p_prior_intent_id !== null)) return { data: null, error: { message: "unavailable" } };
      if (current) old.push({ ...current });
      current = { intent_id: pair.intent, child_id: pair.child, display_name: String(params?.p_display_name), acknowledged: false, prior_intent_id: params?.p_prior_intent_id as string | null, request_id: String(params?.p_request_id) };
      children.push(current);
      if (lostBegin) { lostBegin = false; return { data: null, error: { message: "synthetic lost response" } }; }
      return { data: [{ ...current, disposition: "created" }], error: null };
    }
    if (operation === "app_ack_child_creation") {
      if (!current || params?.p_intent_id !== current.intent_id) return { data: null, error: { message: "unavailable" } };
      current.acknowledged = true; return { data: true, error: null };
    }
    if (operation === "app_fence_child_creation") {
      const matches = current && current.request_id === params?.p_request_id && current.prior_intent_id === params?.p_prior_intent_id;
      if (matches) return { data: "created", error: null };
      if (!current && params?.p_prior_intent_id === null) { fenced.add(String(params?.p_request_id)); return { data: "fenced", error: null }; }
      return { data: "unknown", error: null };
    }
    if (operation === "app_historical_child_creation") {
      if (!historyAccess) return { data: null, error: { message: "private provider detail" } };
      return { data: old.some((row) => row.request_id === params?.p_request_id && row.prior_intent_id === params?.p_prior_intent_id) ? "found" : "unknown", error: null };
    }
    throw new Error("Unexpected synthetic RPC");
  });
  return { rpc, loseNextBegin: () => { lostBegin = true; }, failNextBeforeBegin: () => { failBeforeBegin = true; }, revokeHistory: () => { historyAccess = false; }, current: () => current };
}

describe("Parent journey integration with a synthetic provider", () => {
  beforeEach(() => {
    sessionStorage.clear(); vi.resetAllMocks();
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    vi.stubEnv("PARENTPLUS_ENABLE_CHILD_CREATION", "true");
    vi.stubEnv("PARENTPLUS_ENABLE_PARENT_CHILD_LIST", "true");
    vi.spyOn(globalThis.crypto, "randomUUID").mockReturnValue(request);
    mocks.observe.mockReturnValue(() => {});
    mocks.getUser.mockResolvedValue({ data: { user: { id: actor } }, error: null });
  });
  afterEach(() => { vi.restoreAllMocks(); vi.unstubAllEnvs(); sessionStorage.clear(); });

  it("creates, acknowledges and lists a profile through the real server actions", async () => {
    const provider = syntheticProvider();
    mocks.createClient.mockResolvedValue({ auth: { getUser: mocks.getUser }, rpc: provider.rpc });
    render(<><CreatedChildrenPanel /><ChildCreationPanel /></>);
    fireEvent.click(await screen.findByRole("button", { name: "Check creation status" }));
    fireEvent.change(await screen.findByLabelText("Child name"), { target: { value: "Asha" } });
    fireEvent.click(screen.getByRole("button", { name: "Create profile" }));
    expect(await screen.findByText("Profile: Asha")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Confirm result" }));
    expect(await screen.findByText("Result confirmed")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Load profiles" }));
    expect(await screen.findByRole("listitem")).toHaveTextContent("Asha");
    expect(provider.rpc).toHaveBeenCalledWith("app_ack_child_creation", { p_intent_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa" });
    expect(sessionStorage.length).toBe(0);
  });

  it("recovers a committed request after its response is lost and the panel remounts", async () => {
    const provider = syntheticProvider(); provider.loseNextBegin();
    mocks.createClient.mockResolvedValue({ auth: { getUser: mocks.getUser }, rpc: provider.rpc });
    const view = render(<><CreatedChildrenPanel /><ChildCreationPanel /></>);
    fireEvent.click(await screen.findByRole("button", { name: "Check creation status" }));
    fireEvent.change(await screen.findByLabelText("Child name"), { target: { value: "Asha" } });
    fireEvent.click(screen.getByRole("button", { name: "Create profile" }));
    await screen.findByText(/unable to confirm the profile/i);
    expect(provider.current()?.display_name).toBe("Asha");
    view.unmount();
    render(<><CreatedChildrenPanel /><ChildCreationPanel /></>);
    expect(await screen.findByRole("button", { name: "Load profiles" })).toBeDisabled();
    fireEvent.click(await screen.findByRole("button", { name: "Check creation status" }));
    expect(await screen.findByText("Profile: Asha")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirm result" })).toBeInTheDocument();
    expect(sessionStorage.length).toBe(0);
  });

  it("recognises a superseded request through the real history action without displaying a later profile", async () => {
    const provider = syntheticProvider(); provider.loseNextBegin();
    mocks.createClient.mockResolvedValue({ auth: { getUser: mocks.getUser }, rpc: provider.rpc });
    const view = render(<><CreatedChildrenPanel /><ChildCreationPanel /></>);
    fireEvent.click(await screen.findByRole("button", { name: "Check creation status" }));
    fireEvent.change(await screen.findByLabelText("Child name"), { target: { value: "Asha" } });
    fireEvent.click(screen.getByRole("button", { name: "Create profile" }));
    await screen.findByText(/unable to confirm the profile/i);
    const firstIntent = provider.current()!.intent_id;
    await provider.rpc("app_ack_child_creation", { p_intent_id: firstIntent });
    await provider.rpc("app_begin_child_creation", { p_display_name: "Later profile", p_prior_intent_id: firstIntent, p_request_id: nextRequest });
    view.unmount();
    render(<><CreatedChildrenPanel /><ChildCreationPanel /></>);
    fireEvent.click(await screen.findByRole("button", { name: "Check creation status" }));
    fireEvent.click(await screen.findByRole("button", { name: "Stop waiting for this request" }));
    expect(await screen.findByText(/earlier request created a profile/i)).toBeInTheDocument();
    expect(provider.rpc).toHaveBeenCalledWith("app_historical_child_creation", { p_prior_intent_id: null, p_request_id: request });
    expect(screen.queryByText(/Later profile/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Add another profile" })).not.toBeInTheDocument();
    expect(sessionStorage.length).toBe(0);
  });

  it("keeps recovery locked after an account change without calling a provider RPC", async () => {
    const provider = syntheticProvider(); provider.loseNextBegin();
    let notify!: () => void;
    mocks.observe.mockImplementation((callback) => { notify = callback; return () => {}; });
    mocks.createClient.mockResolvedValue({ auth: { getUser: mocks.getUser }, rpc: provider.rpc });
    render(<><CreatedChildrenPanel /><ChildCreationPanel /></>);
    fireEvent.click(await screen.findByRole("button", { name: "Check creation status" }));
    fireEvent.change(await screen.findByLabelText("Child name"), { target: { value: "Asha" } });
    fireEvent.click(screen.getByRole("button", { name: "Create profile" }));
    await screen.findByText(/unable to confirm the profile/i);
    mocks.getUser.mockResolvedValue({ data: { user: { id: other } }, error: null });
    act(() => notify());
    const calls = provider.rpc.mock.calls.length;
    fireEvent.click(screen.getByRole("button", { name: "Check creation status" }));
    expect(await screen.findByText(/unable to confirm the profile\. Sign in to the original account/i)).toBeInTheDocument();
    expect(provider.rpc).toHaveBeenCalledTimes(calls);
    expect(sessionStorage.length).toBe(1);
    expect(screen.getByRole("button", { name: "Load profiles" })).toBeDisabled();
  });
  it("keeps the earlier request locked if historical access is revoked", async () => {
    const provider = syntheticProvider(); provider.loseNextBegin();
    mocks.createClient.mockResolvedValue({ auth: { getUser: mocks.getUser }, rpc: provider.rpc });
    const view = render(<><CreatedChildrenPanel /><ChildCreationPanel /></>);
    fireEvent.click(await screen.findByRole("button", { name: "Check creation status" }));
    fireEvent.change(await screen.findByLabelText("Child name"), { target: { value: "Asha" } });
    fireEvent.click(screen.getByRole("button", { name: "Create profile" }));
    await screen.findByText(/unable to confirm the profile/i);
    const firstIntent = provider.current()!.intent_id;
    await provider.rpc("app_ack_child_creation", { p_intent_id: firstIntent });
    await provider.rpc("app_begin_child_creation", { p_display_name: "Later profile", p_prior_intent_id: firstIntent, p_request_id: nextRequest });
    provider.revokeHistory();
    view.unmount();
    render(<><CreatedChildrenPanel /><ChildCreationPanel /></>);
    fireEvent.click(await screen.findByRole("button", { name: "Check creation status" }));
    fireEvent.click(await screen.findByRole("button", { name: "Stop waiting for this request" }));
    expect(await screen.findByText(/unable to resolve/i)).toBeInTheDocument();
    expect(screen.queryByText(/private provider detail|Later profile/)).not.toBeInTheDocument();
    expect(sessionStorage.length).toBe(1);
    expect(screen.getByRole("button", { name: "Load profiles" })).toBeDisabled();
  });

  it("fences an undelivered request before accepting a new request through the real actions", async () => {
    const provider = syntheticProvider(); provider.failNextBeforeBegin();
    mocks.createClient.mockResolvedValue({ auth: { getUser: mocks.getUser }, rpc: provider.rpc });
    const view = render(<><CreatedChildrenPanel /><ChildCreationPanel /></>);
    fireEvent.click(await screen.findByRole("button", { name: "Check creation status" }));
    fireEvent.change(await screen.findByLabelText("Child name"), { target: { value: "Asha" } });
    fireEvent.click(screen.getByRole("button", { name: "Create profile" }));
    await screen.findByText(/unable to confirm the profile/i);
    expect(provider.current()).toBeNull();
    view.unmount();
    render(<><CreatedChildrenPanel /><ChildCreationPanel /></>);
    fireEvent.click(await screen.findByRole("button", { name: "Check creation status" }));
    fireEvent.click(await screen.findByRole("button", { name: "Stop waiting for this request" }));
    expect(await screen.findByLabelText("Child name")).toBeInTheDocument();
    expect(provider.rpc).toHaveBeenCalledWith("app_fence_child_creation", { p_prior_intent_id: null, p_request_id: request });
    const oldAttempt = await provider.rpc("app_begin_child_creation", { p_display_name: "Asha", p_prior_intent_id: null, p_request_id: request });
    expect(oldAttempt.error).not.toBeNull();
    vi.mocked(globalThis.crypto.randomUUID).mockReturnValue(nextRequest);
    fireEvent.change(screen.getByLabelText("Child name"), { target: { value: "Asha" } });
    fireEvent.click(screen.getByRole("button", { name: "Create profile" }));
    expect(await screen.findByText("Profile: Asha")).toBeInTheDocument();
    expect(provider.current()?.request_id).toBe(nextRequest);
  });

});
