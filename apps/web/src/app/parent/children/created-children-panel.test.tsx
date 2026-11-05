import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import CreatedChildrenPanel from "./created-children-panel";

const mocks = vi.hoisted(() => ({ list: vi.fn(), observe: vi.fn() }));
vi.mock("@/lib/parent/list-created-children", () => ({ listCreatedChildren: mocks.list }));
vi.mock("@/lib/auth/session-observer", () => ({ observeSessionChanges: mocks.observe }));
const child = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";

describe("CreatedChildrenPanel", () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.resetAllMocks(); vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
    mocks.observe.mockReturnValue(() => {});
    mocks.list.mockResolvedValue({ ok: true, children: [{ id: child, name: "Asha" }] });
  });
  afterEach(() => vi.unstubAllEnvs());
  it("loads profiles only on request and explains the limited scope", async () => {
    render(<CreatedChildrenPanel />);
    expect(mocks.list).not.toHaveBeenCalled();
    expect(screen.getByText(/may not include all linked children/i)).toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: "Load profiles" }));
    expect(await screen.findByText("Asha")).toBeInTheDocument();
  });
  it("shows an honest empty state", async () => {
    mocks.list.mockResolvedValue({ ok: true, children: [] }); render(<CreatedChildrenPanel />);
    fireEvent.click(await screen.findByRole("button", { name: "Load profiles" }));
    expect(await screen.findByText(/no profiles available/i)).toBeInTheDocument();
  });
  it("fails closed if session monitoring is unavailable", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "false"); render(<CreatedChildrenPanel />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/session monitoring is unavailable/i);
    expect(mocks.list).not.toHaveBeenCalled();
  });
  it("clears details on authentication changes", async () => {
    let notify!: (event: string) => void;
    mocks.observe.mockImplementation((callback) => { notify = callback; return () => {}; });
    render(<CreatedChildrenPanel />); fireEvent.click(await screen.findByRole("button", { name: "Load profiles" }));
    await screen.findByText("Asha"); act(() => notify("SIGNED_OUT"));
    expect(screen.queryByText("Asha")).not.toBeInTheDocument();
  });
  it("ignores a delayed response after an account change", async () => {
    let notify!: (event: string) => void, finish!: (value: unknown) => void;
    mocks.observe.mockImplementation((callback) => { notify = callback; return () => {}; });
    mocks.list.mockReturnValue(new Promise((resolve) => { finish = resolve; }));
    render(<CreatedChildrenPanel />); fireEvent.click(await screen.findByRole("button", { name: "Load profiles" }));
    act(() => notify("SIGNED_OUT")); await act(async () => finish({ ok: true, children: [{ id: child, name: "Old private name" }] }));
    expect(screen.queryByText("Old private name")).not.toBeInTheDocument();
  });
  it("clears details on return to the page and redacts errors", async () => {
    render(<CreatedChildrenPanel />); fireEvent.click(await screen.findByRole("button", { name: "Load profiles" }));
    await screen.findByText("Asha"); fireEvent.focus(window); expect(screen.queryByText("Asha")).not.toBeInTheDocument();
    mocks.list.mockResolvedValue({ ok: false, error: "private provider detail" });
    fireEvent.click(screen.getByRole("button", { name: "Load profiles" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/unable to load profiles/i);
    expect(screen.queryByText(/private provider detail/)).not.toBeInTheDocument();
  });
  it("fails closed when session observation throws", async () => {
    mocks.observe.mockImplementation(() => { throw new Error("private provider detail"); });
    render(<CreatedChildrenPanel />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/session monitoring is unavailable/i);
    expect(screen.queryByText(/private provider detail/)).not.toBeInTheDocument();
    expect(mocks.list).not.toHaveBeenCalled();
  });
  it("clears details when the page becomes visible", async () => {
    vi.spyOn(document, "visibilityState", "get").mockReturnValue("visible");
    render(<CreatedChildrenPanel />); fireEvent.click(await screen.findByRole("button", { name: "Load profiles" }));
    await screen.findByText("Asha"); fireEvent(document, new Event("visibilitychange"));
    expect(screen.queryByText("Asha")).not.toBeInTheDocument();
    vi.restoreAllMocks();
  });
  it("prevents duplicate loads and unsubscribes on unmount", async () => {
    const unsubscribe = vi.fn(); mocks.observe.mockReturnValue(unsubscribe);
    mocks.list.mockReturnValue(new Promise(() => {}));
    const view = render(<CreatedChildrenPanel />);
    const button = await screen.findByRole("button", { name: "Load profiles" });
    fireEvent.click(button); fireEvent.click(button); expect(mocks.list).toHaveBeenCalledTimes(1);
    view.unmount(); expect(unsubscribe).toHaveBeenCalledTimes(1);
  });
  it("ignores a late session callback and response after unmount", async () => {
    let notify!: (event: string) => void, finish!: (value: unknown) => void;
    mocks.observe.mockImplementation((callback) => { notify = callback; return () => {}; });
    mocks.list.mockReturnValue(new Promise((resolve) => { finish = resolve; }));
    const view = render(<CreatedChildrenPanel />); fireEvent.click(await screen.findByRole("button", { name: "Load profiles" }));
    view.unmount(); act(() => notify("SIGNED_OUT"));
    await act(async () => finish({ ok: true, children: [{ id: child, name: "Old private name" }] }));
    expect(screen.queryByText("Old private name")).not.toBeInTheDocument();
  });

});
