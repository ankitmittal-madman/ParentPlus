import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { useSessionBoundary } from "./session-boundary";
const m = vi.hoisted(() => ({ session: vi.fn(), observe: vi.fn(), reset: vi.fn(), changed: undefined as undefined | (() => void) }));
vi.mock("@/lib/families/actions", () => ({ familySession: m.session }));
vi.mock("@/lib/auth/session-observer", () => ({ observeSessionChanges: m.observe }));
const a = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", b = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
let current: () => boolean;
function Probe() {
  const v = useSessionBoundary(m.reset);
  return <>
    <p>{v.actorId ?? "private view cleared"}
    </p>
    <button onClick={() => {
      current = v.capture();
    }}>Capture</button>
    <button onClick={v.invalidateView}>Scope</button>
  </>;
}
beforeEach(() => {
  vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
  m.session.mockResolvedValue({ ok: true, data: a });
  m.observe.mockImplementation((cb) => {
    m.changed = cb;
    return () => {
    };
  });
  m.reset.mockClear();
});
it("verifies actor automatically and fences late work on scope focus and auth changes", async () => {
  render(<Probe />);
  await screen.findByText(a);
  fireEvent.click(screen.getByText("Capture"));
  expect(current()).toBe(true);
  fireEvent.click(screen.getByText("Scope"));
  expect(current()).toBe(false);
  fireEvent.click(screen.getByText("Capture"));
  m.session.mockResolvedValue({ ok: true, data: b });
  act(() => window.dispatchEvent(new Event("focus")));
  expect(screen.getByText("private view cleared")).toBeVisible();
  expect(current()).toBe(false);
  await screen.findByText(b);
  fireEvent.click(screen.getByText("Capture"));
  act(() => m.changed?.());
  expect(current()).toBe(false);
  await screen.findByText(b);
});
it("ignores an older account promise and clears private view before auth recovery", async () => {
  let resolve!: (v: unknown) => void;
  m.session.mockReturnValueOnce(new Promise(r => {
    resolve = r;
  }));
  const v = render(<Probe />);
  await waitFor(() => expect(m.session).toHaveBeenCalled());
  m.session.mockResolvedValue({ ok: true, data: b });
  act(() => m.changed?.());
  await screen.findByText(b);
  await act(async () => resolve({ ok: true, data: a }));
  expect(screen.queryByText(a)).not.toBeInTheDocument();
  fireEvent.click(screen.getByText("Capture"));
  v.unmount();
  expect(current()).toBe(false);
});
it("fails closed when session observation or verification is unavailable", async () => {
  m.session.mockResolvedValue({ ok: false });
  render(<Probe />);
  await waitFor(() => expect(m.reset).toHaveBeenCalled());
  expect(screen.getByText("private view cleared")).toBeVisible();
});
it("clears hidden private views and defers authentication reload until visible", async () => {
  render(<Probe />);
  await screen.findByText(a);
  const count = m.session.mock.calls.length;
  Object.defineProperty(document, "visibilityState", { configurable: true, value: "hidden" });
  act(() => document.dispatchEvent(new Event("visibilitychange")));
  expect(screen.getByText("private view cleared")).toBeVisible();
  act(() => m.changed?.());
  await act(async () => {
  });
  expect(m.session).toHaveBeenCalledTimes(count);
  Object.defineProperty(document, "visibilityState", { configurable: true, value: "visible" });
  act(() => document.dispatchEvent(new Event("visibilitychange")));
  await screen.findByText(a);
});
