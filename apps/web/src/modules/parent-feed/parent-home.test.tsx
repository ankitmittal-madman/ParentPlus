import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { ParentHome } from "./parent-home";
import { readPending, writePending } from "../attendance/pending";
const m = vi.hoisted(() => ({ session: vi.fn(), observe: vi.fn(), children: vi.fn(), academies: vi.fn(), batches: vi.fn(), sessions: vi.fn(), items: vi.fn(), week: vi.fn(), send: vi.fn(), status: vi.fn(), changed: undefined as undefined | (() => void) }));
vi.mock("@/lib/families/actions", () => ({ familySession: m.session }));
vi.mock("@/lib/auth/session-observer", () => ({ observeSessionChanges: m.observe }));
vi.mock("@/lib/parent-feed/actions", () => ({ listParentChildren: m.children, listParentAcademies: m.academies, listParentBatches: m.batches, listParentSessions: m.sessions, listParentItems: m.items, loadParentWeek: m.week, sendParentSignal: m.send, parentSignalRequestStatus: m.status }));
const a = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", b = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", c = "cccccccc-cccc-4ccc-8ccc-cccccccccccc", d = "dddddddd-dddd-4ddd-8ddd-dddddddddddd", t = "2026-11-10T20:30:00Z";
const session = { id: d, batchId: c, batchName: "Morning Art", courseName: "Painting", startsAt: "2026-11-11T10:00:00Z", endsAt: "2026-11-11T11:00:00Z", status: "scheduled", version: 2, enrollmentId: b, enrollmentStatus: "active", attendance: { status: "late", confirmedAt: t }, ownLatestSignal: null, canSignal: true };
const item = { id: d, childId: b, classId: c, type: "attendance", schemaVersion: 1, priority: 0, createdAt: t, expiresAt: null, payload: { session_id: d, date: "2026-11-11", status: "late", confirmed_at: t, title: "Attendance recorded", body: "late on 2026-11-11" } };
const payload = { operation: "send_parent_signal" as const, child_id: b, workspace_id: a, session_id: d, expected_session_version: 2, type: "missing_today" as const, reason: "unwell" as const };
const pending = { format: 1 as const, actorId: a, requestId: d, payload };
const receipt = { requestId: d, signalId: c, sessionId: d, childId: b, type: "missing_today", reason: "unwell", createdAt: t };
function deferred() { let resolve!: (v: unknown) => void; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; }
const sessionPage = (sessions = [session]) => ({ ok: true, data: { date: "2026-11-11", timeZone: "Asia/Kolkata", serverNow: t, sessions, next: null } });
beforeEach(() => {
  vi.resetAllMocks(); vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true"); vi.setSystemTime(new Date(t)); sessionStorage.clear(); localStorage.clear();
  m.session.mockResolvedValue({ ok: true, data: a }); m.observe.mockImplementation(cb => { m.changed = cb; return () => {}; });
  m.children.mockResolvedValue({ ok: true, data: [{ id: b, name: "Asha" }, { id: c, name: "Kabir" }] });
  m.academies.mockResolvedValue({ ok: true, data: { academies: [{ workspaceId: a, name: "River Academy", timeZone: "Asia/Kolkata" }, { workspaceId: b, name: "North Academy", timeZone: "UTC" }], nextAfter: null } });
  m.batches.mockResolvedValue({ ok: true, data: { batches: [{ batchId: c, batchName: "Morning Art", courseName: "Painting", enrollmentId: b, enrollmentStatus: "active" }], nextAfter: null } });
  m.sessions.mockImplementation(async (_actor, input) => ({ ok: true, data: { date: input.date, timeZone: input.workspaceId === a ? "Asia/Kolkata" : "UTC", serverNow: t, sessions: [session], next: null } }));
  m.items.mockResolvedValue({ ok: true, data: { items: [item], next: null } });
  m.week.mockResolvedValue({ ok: true, data: { weekStart: "2026-11-09", timeZone: "Asia/Kolkata", attendedCount: 1, recordedCount: 1, rows: [{ sessionId: d, batchId: c, batchName: "Morning Art", date: "2026-11-11", status: "late", confirmedAt: t }], hasMore: false } });
  m.send.mockResolvedValue({ ok: false, kind: "unknown" }); m.status.mockResolvedValue({ ok: true, data: { state: "unknown", receipt: null } });
});
it("autoloads own child dedicated academy class feed and exact week using academy-local today", async () => {
  render(<ParentHome />); await screen.findByText("Attendance recorded"); expect(m.children).toHaveBeenCalledWith(a); expect(m.academies).toHaveBeenCalledWith(a, { childId: b, after: null }); expect(m.batches).toHaveBeenCalledWith(a, { childId: b, workspaceId: a, after: null }); expect(m.sessions).toHaveBeenCalledWith(a, { childId: b, workspaceId: a, batchId: c, date: "2026-11-11", after: null }); expect(m.items).toHaveBeenCalledWith(a, { childId: b, workspaceId: a, batchId: c, before: null }); expect(m.week).toHaveBeenCalledWith(a, { childId: b, workspaceId: a, batchId: c, weekStart: "2026-11-09" }); expect(screen.getByLabelText("Session date")).toHaveValue("2026-11-11"); expect(screen.getAllByRole("button", { name: /Select session date/ })).toHaveLength(7); expect(screen.getByRole("region", { name: "This week" })).toHaveTextContent("1Attended this week"); expect(screen.getByRole("link", { name: "Profiles and connections" })).toHaveAttribute("href", "/parent/children"); expect(screen.queryByText(/Meera|Creative Room|%|fees due/i)).not.toBeInTheDocument();
});
it("keeps independent academy class session and feed pagination cursors", async () => {
  m.academies.mockResolvedValueOnce({ ok: true, data: { academies: [{ workspaceId: a, name: "River Academy", timeZone: "Asia/Kolkata" }], nextAfter: a } }).mockResolvedValue({ ok: true, data: { academies: [{ workspaceId: b, name: "North Academy", timeZone: "UTC" }], nextAfter: null } });
  m.batches.mockResolvedValueOnce({ ok: true, data: { batches: [{ batchId: c, batchName: "Morning Art", courseName: "Painting", enrollmentId: b, enrollmentStatus: "active" }], nextAfter: c } }).mockResolvedValue({ ok: true, data: { batches: [{ batchId: d, batchName: "Evening Art", courseName: "Painting", enrollmentId: d, enrollmentStatus: "active" }], nextAfter: null } });
  m.sessions.mockResolvedValueOnce({ ok: true, data: { ...sessionPage().data, next: { startsAt: session.startsAt, id: d } } }).mockResolvedValue(sessionPage([{ ...session, id: c, batchName: "Second session" }]));
  m.items.mockResolvedValueOnce({ ok: true, data: { items: [item], next: { createdAt: t, id: d } } }).mockResolvedValue({ ok: true, data: { items: [{ ...item, id: c, payload: { title: "Older update", body: "History" } }], next: null } });
  render(<ParentHome />); await screen.findByText("Attendance recorded"); for (const name of ["Load more academies", "Load more classes", "Load more sessions", "Load more updates"]) fireEvent.click(screen.getByRole("button", { name })); await screen.findByText("Older update"); await screen.findByRole("option", { name: /Evening Art/ }); expect(m.academies).toHaveBeenLastCalledWith(a, { childId: b, after: a }); expect(m.batches).toHaveBeenLastCalledWith(a, { childId: b, workspaceId: a, after: c }); expect(m.sessions).toHaveBeenLastCalledWith(a, { childId: b, workspaceId: a, batchId: c, date: "2026-11-11", after: { startsAt: session.startsAt, id: d } }); expect(m.items).toHaveBeenLastCalledWith(a, { childId: b, workspaceId: a, batchId: c, before: { createdAt: t, id: d } });
});
it("clears dependent private facts and discards stale child academy date and class reads", async () => {
  render(<ParentHome />); await screen.findByText("Attendance recorded"); const old = deferred(); m.items.mockReturnValueOnce(old.promise); fireEvent.change(screen.getByLabelText("Session date"), { target: { value: "2026-11-12" } }); expect(screen.queryByText("Attendance recorded")).not.toBeInTheDocument(); fireEvent.change(screen.getByLabelText("Child"), { target: { value: c } }); await waitFor(() => expect(m.academies).toHaveBeenLastCalledWith(a, { childId: c, after: null })); await act(async () => old.resolve({ ok: true, data: { items: [{ ...item, payload: { title: "Old child secret" } }], next: null } })); expect(screen.queryByText("Old child secret")).not.toBeInTheDocument(); await screen.findByLabelText("Academy"); fireEvent.change(screen.getByLabelText("Academy"), { target: { value: b } }); await waitFor(() => expect(m.sessions).toHaveBeenLastCalledWith(a, expect.objectContaining({ childId: c, workspaceId: b, date: "2026-11-10" }))); fireEvent.change(screen.getByLabelText("Class"), { target: { value: "" } }); await waitFor(() => expect(m.items).toHaveBeenLastCalledWith(a, { childId: c, workspaceId: b, batchId: null, before: null }));
});
it("does not accept a stale initial child list after account switch or unmount", async () => {
  const old = deferred(); m.children.mockReturnValueOnce(old.promise); const v = render(<ParentHome />); await waitFor(() => expect(m.children).toHaveBeenCalledWith(a)); m.session.mockResolvedValue({ ok: true, data: d }); m.children.mockResolvedValue({ ok: true, data: [] }); act(() => m.changed?.()); await screen.findByText(/No child profiles available/); await act(async () => old.resolve({ ok: true, data: [{ id: b, name: "Private old child" }] })); expect(screen.queryByText("Private old child")).not.toBeInTheDocument(); expect(m.academies).not.toHaveBeenCalled(); v.unmount();
});
it("owns loading and error state by current scope when obsolete requests finish last", async () => {
  render(<ParentHome />); await screen.findByText("Attendance recorded"); const old = deferred(), newer = deferred(); m.sessions.mockReturnValueOnce(old.promise).mockReturnValueOnce(newer.promise); fireEvent.change(screen.getByLabelText("Session date"), { target: { value: "2026-11-12" } }); fireEvent.change(screen.getByLabelText("Session date"), { target: { value: "2026-11-13" } }); await act(async () => old.resolve({ ok: false, kind: "unknown" })); expect(screen.getAllByRole("status").some(s => s.textContent === "Loading…")).toBe(true); expect(screen.queryByRole("alert")).not.toBeInTheDocument(); await act(async () => newer.resolve({ ok: true, data: { date: "2026-11-13", timeZone: "Asia/Kolkata", serverNow: t, sessions: [], next: null } })); await screen.findByText("No sessions on this date.");
});
it("clears private views on focus and revoked access while retaining durable recovery bytes", async () => {
  writePending(pending); render(<ParentHome />); await screen.findByText("Attendance recorded"); const check = deferred(); m.session.mockReturnValueOnce(check.promise); fireEvent.focus(window); expect(screen.queryByText("Attendance recorded")).not.toBeInTheDocument(); expect(readPending(a, "signal").kind).toBe("pending"); await act(async () => check.resolve({ ok: true, data: a })); await screen.findByText("Attendance recorded"); m.sessions.mockResolvedValue({ ok: false, kind: "forbidden" }); fireEvent.click(screen.getByRole("button", { name: "Refresh parent home" })); await screen.findByRole("alert"); expect(screen.queryByText("Attendance recorded")).not.toBeInTheDocument();
});
it("shows honest no-child no-academy no-class empty and invalid-zone views", async () => {
  m.children.mockResolvedValueOnce({ ok: true, data: [] }); const v=render(<ParentHome />); await screen.findByText(/No child profiles available/); v.unmount(); m.academies.mockResolvedValueOnce({ ok: true, data: { academies: [], nextAfter: null } }); const v2=render(<ParentHome />); await screen.findByText("No eligible academy connections for this child."); v2.unmount(); m.batches.mockResolvedValueOnce({ ok: true, data: { batches: [], nextAfter: null } }); const v3=render(<ParentHome />); await screen.findByText("No saved classes for this child at this academy."); v3.unmount(); m.academies.mockResolvedValueOnce({ ok: true, data: { academies: [{ workspaceId: a, name: "Unset", timeZone: null }], nextAfter: null } }); render(<ParentHome />); await screen.findByText(/time zone is unavailable/); expect(screen.queryByLabelText("Session date")).not.toBeInTheDocument();
});
it("retains paused completed cancelled history and exposes reports only for eligible active sessions", async () => {
  m.sessions.mockResolvedValue(sessionPage([{ ...session, canSignal: false, enrollmentStatus: "paused" }, { ...session, id: c, batchName: "Ended", canSignal: false, enrollmentStatus: "completed", status: "cancelled" }])); render(<ParentHome />); await screen.findByText("Paused enrolment"); expect(screen.getByText("Completed enrolment")).toBeVisible(); expect(screen.getByText("Cancelled")).toBeVisible(); expect(screen.getByText("Attendance recorded")).toBeVisible(); expect(screen.queryByRole("button", { name: /Send parent report for/ })).not.toBeInTheDocument();
});
it("persists exact unknown report before send and never changes saved attendance or weekly counts optimistically", async () => {
  render(<ParentHome />); fireEvent.click(await screen.findByRole("button", { name: /Send parent report for Morning Art/ })); fireEvent.click(screen.getByRole("button", { name: "Missing today" })); expect(screen.getByRole("button", { name: "Send report" })).toBeDisabled(); fireEvent.change(screen.getByLabelText("Missing reason"), { target: { value: "unwell" } }); fireEvent.click(screen.getByRole("button", { name: "Send report" })); await screen.findByRole("button", { name: "Check report result" }); const saved=readPending(a,"signal"); expect(saved.kind).toBe("pending"); if(saved.kind==="pending") { expect(saved.value.payload).toEqual(payload); expect(m.send).toHaveBeenCalledWith(a,{requestId:saved.value.requestId,payload}); } expect(within(screen.getByRole("region", { name: "This week" })).getByText("1", { selector: "strong" })).toBeVisible(); expect(m.week).toHaveBeenCalledTimes(1); expect(screen.getAllByText("Late").length).toBeGreaterThan(0);
});
it("restores original signal UUID and payload after reload and refreshes latest facts on known recovery", async () => {
  writePending(pending); m.status.mockResolvedValue({ ok: true, data: { state: "known", receipt } }); render(<ParentHome />); await screen.findByText("Attendance recorded"); fireEvent.click(await screen.findByRole("button", { name: "Check report result" })); await waitFor(()=>expect(m.status).toHaveBeenCalledWith(a,{requestId:d,payload})); await waitFor(()=>expect(readPending(a,"signal").kind).toBe("none")); await waitFor(()=>expect(m.week).toHaveBeenCalledTimes(2)); expect(m.send).not.toHaveBeenCalled();
});
it("retains unknown report through transient status failure and retries the same full identity", async () => {
  writePending(pending); m.status.mockResolvedValue({ok:false,kind:"unknown"}); render(<ParentHome />); fireEvent.click(await screen.findByRole("button",{name:"Check report result"})); await screen.findByText(/Report result is unconfirmed/); expect(readPending(a,"signal")).toEqual({kind:"pending",value:pending}); fireEvent.click(screen.getByRole("button",{name:"Retry same report"})); await waitFor(()=>expect(m.send).toHaveBeenCalledWith(a,{requestId:d,payload})); expect(readPending(a,"signal")).toEqual({kind:"pending",value:pending});
});
it("blocks replacement reports for corrupt recovery and does not replay another account operation", async () => {
  sessionStorage.setItem(`parentplus:signal-pending:${a}`,"bad"); render(<ParentHome />); await screen.findByText(/Saved recovery data cannot be read/); expect(screen.queryByRole("button",{name:/Send parent report for/})).not.toBeInTheDocument(); expect(m.send).not.toHaveBeenCalled(); m.session.mockResolvedValue({ok:true,data:d}); act(()=>m.changed?.()); await waitFor(()=>expect(m.children).toHaveBeenLastCalledWith(d)); expect(screen.queryByText(/Saved recovery data cannot be read/)).not.toBeInTheDocument(); expect(m.status).not.toHaveBeenCalled();
});
it("renders Hindi controls statuses and date labels without exposing contact provenance", async () => {
  render(<ParentHome />); await screen.findByText("Attendance recorded"); fireEvent.change(screen.getByLabelText("Page language / पृष्ठ की भाषा"),{target:{value:"hi"}}); expect(screen.getByRole("heading",{name:"अभिभावक होम"})).toBeVisible(); expect(screen.getAllByText("देर से").length).toBeGreaterThan(0); expect(screen.getByLabelText("सत्र की तारीख")).toHaveValue("2026-11-11"); expect(screen.queryByText(/@|actor_id|phone|email/)).not.toBeInTheDocument();
});
it("discards obsolete academy and batch pages without sticking new-scope loading ownership", async () => {
  const old=deferred();m.academies.mockReturnValueOnce(old.promise);render(<ParentHome />);await screen.findByLabelText("Child");fireEvent.change(screen.getByLabelText("Child"),{target:{value:c}});await screen.findByText("Attendance recorded");await act(async()=>old.resolve({ok:true,data:{academies:[{workspaceId:d,name:"Private old academy",timeZone:"UTC"}],nextAfter:null}}));expect(screen.queryByText("Private old academy")).not.toBeInTheDocument();const oldBatch=deferred();m.batches.mockReturnValueOnce(oldBatch.promise);fireEvent.change(screen.getByLabelText("Academy"),{target:{value:b}});fireEvent.change(screen.getByLabelText("Academy"),{target:{value:a}});await screen.findByText("Attendance recorded");await act(async()=>oldBatch.resolve({ok:false,kind:"forbidden"}));expect(screen.queryByRole("alert")).not.toBeInTheDocument();expect(screen.getByLabelText("Academy")).toHaveValue(a);
});
it("removes an open report form when visible polling makes the session ineligible", async () => {
  vi.useFakeTimers({toFake:["setInterval","clearInterval"]}); render(<ParentHome />);fireEvent.click(await screen.findByRole("button",{name:/Send parent report for Morning Art/})); expect(screen.getByRole("button",{name:"Send report"})).toBeVisible();m.sessions.mockResolvedValue(sessionPage([{...session,enrollmentStatus:"paused",canSignal:false}]));await act(async()=>{await vi.advanceTimersByTimeAsync(15000);});vi.useRealTimers();expect(screen.queryByRole("button",{name:"Send report"})).not.toBeInTheDocument();expect(screen.getByText("Paused enrolment")).toBeVisible();
});
it("keeps an original report pending when its reply arrives after child selection changes", async () => {
  writePending(pending);const old=deferred();m.status.mockReturnValueOnce(old.promise);render(<ParentHome />);await screen.findByText("Attendance recorded");fireEvent.click(screen.getByRole("button",{name:"Check report result"}));fireEvent.change(screen.getByLabelText("Child"),{target:{value:c}});await waitFor(()=>expect(m.items).toHaveBeenLastCalledWith(a,{childId:c,workspaceId:a,batchId:c,before:null}));await act(async()=>old.resolve({ok:true,data:{state:"known",receipt}}));expect(readPending(a,"signal")).toEqual({kind:"pending",value:pending});expect(screen.getByRole("button",{name:"Check report result"})).toBeEnabled();m.status.mockResolvedValue({ok:true,data:{state:"known",receipt}});fireEvent.click(screen.getByRole("button",{name:"Check report result"}));await waitFor(()=>expect(readPending(a,"signal").kind).toBe("none"));expect(m.week).toHaveBeenLastCalledWith(a,{childId:c,workspaceId:a,batchId:c,weekStart:"2026-11-09"});
});
it("retains volatile recovery when storage fails and resolves it without claiming durable storage", async () => {
  render(<ParentHome />);fireEvent.click(await screen.findByRole("button",{name:/Send parent report for Morning Art/}));const storage=vi.spyOn(Storage.prototype,"setItem").mockImplementation(()=>{throw Error("storage disabled");});fireEvent.click(screen.getByRole("button",{name:"Send report"}));await screen.findByText(/Keep this tab open until the report is checked/);expect(m.send).toHaveBeenCalledTimes(1);const write=m.send.mock.calls[0][1];storage.mockRestore();m.status.mockResolvedValue({ok:true,data:{state:"known",receipt:{...receipt,requestId:write.requestId,type:"running_late",reason:null}}});fireEvent.click(screen.getByRole("button",{name:"Check report result"}));await waitFor(()=>expect(screen.queryByRole("button",{name:"Check report result"})).not.toBeInTheDocument());
});
it("clears only definitively rejected original report and reloads factual data", async () => {
  writePending(pending);m.status.mockResolvedValue({ok:false,kind:"conflict"});render(<ParentHome />);await screen.findByText("Attendance recorded");fireEvent.click(screen.getByRole("button",{name:"Check report result"}));await waitFor(()=>expect(readPending(a,"signal").kind).toBe("none"));expect(await screen.findByText(/session or request changed/)).toBeVisible();await waitFor(()=>expect(m.week).toHaveBeenCalledTimes(2));
});
it("refreshes the selected child academy class and date instead of returning to the first selection", async () => {
  render(<ParentHome />);await screen.findByText("Attendance recorded");fireEvent.change(screen.getByLabelText("Child"),{target:{value:c}});await screen.findByText("Attendance recorded");fireEvent.change(screen.getByLabelText("Academy"),{target:{value:b}});await waitFor(()=>expect(m.items).toHaveBeenLastCalledWith(a,{childId:c,workspaceId:b,batchId:c,before:null}));fireEvent.change(screen.getByLabelText("Class"),{target:{value:""}});fireEvent.change(screen.getByLabelText("Session date"),{target:{value:"2026-11-14"}});fireEvent.click(screen.getByRole("button",{name:"Refresh parent home"}));await waitFor(()=>expect(m.sessions).toHaveBeenLastCalledWith(a,{childId:c,workspaceId:b,batchId:null,date:"2026-11-14",after:null}));expect(screen.getByLabelText("Child")).toHaveValue(c);expect(screen.getByLabelText("Academy")).toHaveValue(b);expect(screen.getByLabelText("Session date")).toHaveValue("2026-11-14");
});
it("focuses the report form after explicit selection and submits other report types with null reason", async () => {
  render(<ParentHome />);fireEvent.click(await screen.findByRole("button",{name:/Send parent report for Morning Art/}));expect(screen.getByRole("heading",{name:"Parent report"})).toHaveFocus();fireEvent.click(screen.getByRole("button",{name:"Picked up"}));fireEvent.click(screen.getByRole("button",{name:"Send report"}));await screen.findByRole("button",{name:"Check report result"});expect(m.send).toHaveBeenCalledWith(a,expect.objectContaining({payload:{operation:"send_parent_signal",child_id:b,workspace_id:a,session_id:d,expected_session_version:2,type:"picked_up",reason:null}}));expect(screen.getByRole("region",{name:"Parent report"})).toHaveTextContent("Parent reports are not confirmed attendance or verified handover.");
});
it("refreshes saved feed and exact weekly facts with visible session polling after a coach correction", async () => {
  vi.useFakeTimers({toFake:["setInterval","clearInterval"]});render(<ParentHome />);await screen.findByText("Attendance recorded");m.items.mockResolvedValue({ok:true,data:{items:[{...item,payload:{...item.payload,status:"absent",body:"absent on 2026-11-11"}}],next:null}});m.week.mockResolvedValue({ok:true,data:{weekStart:"2026-11-09",timeZone:"Asia/Kolkata",attendedCount:0,recordedCount:1,rows:[{sessionId:d,batchId:c,batchName:"Morning Art",date:"2026-11-11",status:"absent",confirmedAt:t}],hasMore:false}});m.sessions.mockResolvedValue(sessionPage([{...session,attendance:{status:"absent",confirmedAt:t}}]));await act(async()=>{await vi.advanceTimersByTimeAsync(15000);});vi.useRealTimers();expect(screen.getByRole("region",{name:"This week"})).toHaveTextContent("0Attended this week");expect(screen.getAllByText("Absent").length).toBeGreaterThan(0);expect(screen.queryByText("Late")).not.toBeInTheDocument();
});
it("releases recovery loading ownership after same-scope refresh invalidates an in-flight status check", async () => {
  writePending(pending);const old=deferred();m.status.mockReturnValueOnce(old.promise);render(<ParentHome />);await screen.findByText("Attendance recorded");fireEvent.click(screen.getByRole("button",{name:"Check report result"}));expect(screen.getByRole("button",{name:"Check report result"})).toBeDisabled();fireEvent.click(screen.getByRole("button",{name:"Refresh parent home"}));await screen.findByText("Attendance recorded");await act(async()=>old.resolve({ok:true,data:{state:"known",receipt}}));expect(readPending(a,"signal")).toEqual({kind:"pending",value:pending});expect(screen.getByRole("button",{name:"Check report result"})).toBeEnabled();m.status.mockResolvedValue({ok:true,data:{state:"known",receipt}});fireEvent.click(screen.getByRole("button",{name:"Check report result"}));await waitFor(()=>expect(readPending(a,"signal").kind).toBe("none"));
});
it("refreshes class bootstrap when Refresh cancels the first pending batch read", async () => {
  const original = deferred();
  const replacement = deferred();
  const reply = {
    ok: true,
    data: {
      batches: [{ batchId: c, batchName: "Morning Art", courseName: "Painting", enrollmentId: b, enrollmentStatus: "active" }],
      nextAfter: null,
    },
  };
  m.batches.mockReturnValueOnce(original.promise).mockReturnValueOnce(replacement.promise);
  render(<ParentHome />);
  await waitFor(() => expect(m.batches).toHaveBeenCalledTimes(1));
  fireEvent.click(screen.getByRole("button", { name: "Refresh parent home" }));
  await act(async () => {
    original.resolve(reply);
    replacement.resolve(reply);
  });
  expect(await screen.findByLabelText("Class")).toHaveValue(c);
  expect(await screen.findByText("Attendance recorded")).toBeVisible();
  expect(m.batches).toHaveBeenCalledTimes(2);
  expect(m.sessions).toHaveBeenLastCalledWith(a, { childId: b, workspaceId: a, batchId: c, date: "2026-11-11", after: null });
});
it("resolves the first enabled recovery Check while automatic class bootstrap changes the selected scope", async () => {
  writePending(pending);
  const bootstrap = deferred();
  const status = deferred();
  m.batches.mockReturnValueOnce(bootstrap.promise);
  m.status.mockReturnValueOnce(status.promise);
  render(<ParentHome />);
  await waitFor(() => expect(m.batches).toHaveBeenCalledTimes(1));
  const check = await screen.findByRole("button", { name: "Check report result" });
  expect(check).toBeEnabled();
  fireEvent.click(check);
  expect(m.status).toHaveBeenCalledWith(a, { requestId: d, payload });
  await act(async () => bootstrap.resolve({
    ok: true,
    data: {
      batches: [{ batchId: c, batchName: "Morning Art", courseName: "Painting", enrollmentId: b, enrollmentStatus: "active" }],
      nextAfter: null,
    },
  }));
  await screen.findByText("Attendance recorded");
  await act(async () => status.resolve({ ok: true, data: { state: "known", receipt } }));
  await waitFor(() => expect(readPending(a, "signal").kind).toBe("none"));
  expect(m.status).toHaveBeenCalledTimes(1);
  expect(m.send).not.toHaveBeenCalled();
  expect(screen.getByText("Parent report saved.")).toBeVisible();
});
