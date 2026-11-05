import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ClassRecoveryPanel from "./class-recovery-panel";

const mocks = vi.hoisted(() => ({ list: vi.fn(), recover: vi.fn(), observe: vi.fn() }));
vi.mock("@/lib/scheduling/list-class-workspaces", () => ({ listClassWorkspaces: mocks.list }));
vi.mock("@/lib/scheduling/recover-current-class-setup", () => ({ recoverCurrentClassSetup: mocks.recover }));
vi.mock("@/lib/auth/session-observer", () => ({ observeSessionChanges: mocks.observe }));
const actor="b0000000-0000-4000-8000-000000000001", academy="a0000000-0000-4000-8000-000000000001", second="a0000000-0000-4000-8000-000000000002";

describe("ClassRecoveryPanel", () => {
  beforeEach(() => {
    vi.resetAllMocks(); vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true"); mocks.observe.mockReturnValue(() => {});
    mocks.list.mockResolvedValue({ok:true,actorId:actor,workspaces:[{id:academy,name:"Badminton Academy"},{id:second,name:"Art Academy"}]});
    mocks.recover.mockResolvedValue({ok:true,state:"pending",intentId:"e0000000-0000-4000-8000-000000000001",priorIntentId:null,requestId:null,courseName:"Dance",batchName:"Morning"});
  });
  afterEach(() => { vi.unstubAllEnvs(); vi.restoreAllMocks(); });
  it("loads authorised academies only after a deliberate request", async () => {
    render(<ClassRecoveryPanel />); expect(mocks.list).not.toHaveBeenCalled();
    fireEvent.click(await screen.findByRole("button",{name:"Load academies"}));
    expect(await screen.findByRole("option",{name:"Badminton Academy"})).toBeInTheDocument();
    expect(mocks.recover).not.toHaveBeenCalled();
  });
  it("shows a selected academy's pending recovery without creating a class", async () => {
    render(<ClassRecoveryPanel />);fireEvent.click(await screen.findByRole("button",{name:"Load academies"}));
    await screen.findByRole("option",{name:"Badminton Academy"});
    fireEvent.change(screen.getByLabelText("Academy"),{target:{value:academy}});
    expect(await screen.findByText(/Dance/)).toBeInTheDocument();
    expect(mocks.recover).toHaveBeenCalledWith({workspaceId:academy,expectedActorId:actor});
    expect(screen.queryByRole("button",{name:/create/i})).not.toBeInTheDocument();
  });
  it("does not describe unknown as a failed or absent setup", async () => {
    mocks.recover.mockResolvedValue({ok:true,state:"unknown"}); render(<ClassRecoveryPanel />);
    fireEvent.click(await screen.findByRole("button",{name:"Load academies"}));await screen.findByRole("option",{name:"Badminton Academy"});
    fireEvent.change(screen.getByLabelText("Academy"),{target:{value:academy}});
    expect(await screen.findByText(/cannot confirm the current setup/i)).toBeInTheDocument();
  });
  it("ignores an earlier academy response after selection changes", async () => {
    let finish!: (x: unknown)=>void; mocks.recover.mockReturnValueOnce(new Promise((resolve)=>{finish=resolve;})).mockResolvedValueOnce({ok:true,state:"unknown"});
    render(<ClassRecoveryPanel />);fireEvent.click(await screen.findByRole("button",{name:"Load academies"}));await screen.findByRole("option",{name:"Badminton Academy"});
    fireEvent.change(screen.getByLabelText("Academy"),{target:{value:academy}});fireEvent.change(screen.getByLabelText("Academy"),{target:{value:second}});
    await screen.findByText(/cannot confirm the current setup/i);
    await act(async()=>finish({ok:true,state:"pending",courseName:"Stale private name",batchName:"Old"}));
    expect(screen.queryByText(/Stale private name/)).not.toBeInTheDocument();
  });
  it("clears displayed details on an authentication change", async () => {
    let notify!: (event:string)=>void; mocks.observe.mockImplementation((callback)=>{notify=callback;return ()=>{};});
    render(<ClassRecoveryPanel />);fireEvent.click(await screen.findByRole("button",{name:"Load academies"}));await screen.findByRole("option",{name:"Badminton Academy"});
    fireEvent.change(screen.getByLabelText("Academy"),{target:{value:academy}});await screen.findByText(/Dance/);
    act(()=>notify("SIGNED_OUT"));expect(screen.queryByText(/Dance/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Academy")).not.toBeInTheDocument();
  });
  it("fails closed if session observation cannot be installed", async () => {
    mocks.observe.mockImplementation(()=>{throw new Error("private provider detail");});
    render(<ClassRecoveryPanel />);expect(await screen.findByRole("alert")).toHaveTextContent(/session monitoring is unavailable/i);
    expect(screen.queryByRole("button",{name:"Load academies"})).not.toBeInTheDocument();
  });
  it("fails closed when live session observation is disabled", async () => {
    vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "false");
    render(<ClassRecoveryPanel />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/session monitoring is unavailable/i);
    expect(mocks.observe).not.toHaveBeenCalled(); expect(mocks.list).not.toHaveBeenCalled();
  });
  it("shows a safe empty state when no academy is eligible", async () => {
    mocks.list.mockResolvedValue({ok:true,actorId:actor,workspaces:[]});render(<ClassRecoveryPanel />);
    fireEvent.click(await screen.findByRole("button",{name:"Load academies"}));expect(await screen.findByText(/no eligible academies/i)).toBeInTheDocument();
    expect(mocks.recover).not.toHaveBeenCalled();
  });
  it("clears sensitive details when the page regains focus", async () => {
    render(<ClassRecoveryPanel />);fireEvent.click(await screen.findByRole("button",{name:"Load academies"}));await screen.findByRole("option",{name:"Badminton Academy"});
    fireEvent.change(screen.getByLabelText("Academy"),{target:{value:academy}});await screen.findByText(/Dance/);
    fireEvent.focus(window);await waitFor(()=>expect(screen.queryByText(/Dance/)).not.toBeInTheDocument());
  });
  it("ignores a pending academy list after an authentication change", async () => {
    let notify!: (event:string)=>void, finish!: (x:unknown)=>void;
    mocks.observe.mockImplementation((callback)=>{notify=callback;return ()=>{};});
    mocks.list.mockReturnValue(new Promise((resolve)=>{finish=resolve;}));
    render(<ClassRecoveryPanel />);fireEvent.click(await screen.findByRole("button",{name:"Load academies"}));
    act(()=>notify("SIGNED_OUT"));
    await act(async()=>finish({ok:true,actorId:actor,workspaces:[{id:academy,name:"Stale academy"}]}));
    expect(screen.queryByText("Stale academy")).not.toBeInTheDocument();
  });
  it("ignores pending recovery after an authentication change", async () => {
    let notify!: (event:string)=>void, finish!: (x:unknown)=>void;
    mocks.observe.mockImplementation((callback)=>{notify=callback;return ()=>{};});
    mocks.recover.mockReturnValue(new Promise((resolve)=>{finish=resolve;}));
    render(<ClassRecoveryPanel />);fireEvent.click(await screen.findByRole("button",{name:"Load academies"}));await screen.findByRole("option",{name:"Badminton Academy"});
    fireEvent.change(screen.getByLabelText("Academy"),{target:{value:academy}});act(()=>notify("SIGNED_OUT"));
    await act(async()=>finish({ok:true,state:"pending",courseName:"Stale private name",batchName:"Old"}));
    expect(screen.queryByText(/Stale private name/)).not.toBeInTheDocument();
  });
  it("does not send a workspace outside the returned list", async () => {
    render(<ClassRecoveryPanel />);fireEvent.click(await screen.findByRole("button",{name:"Load academies"}));await screen.findByRole("option",{name:"Badminton Academy"});
    fireEvent.change(screen.getByLabelText("Academy"),{target:{value:"unapproved"}});
    expect(mocks.recover).not.toHaveBeenCalled();
  });
  it("does not reveal provider error details", async () => {
    mocks.list.mockResolvedValue({ok:false,error:"private provider information"});render(<ClassRecoveryPanel />);
    fireEvent.click(await screen.findByRole("button",{name:"Load academies"}));
    expect(await screen.findByRole("alert")).toHaveTextContent(/unable to load academies/i);
    expect(screen.queryByText(/private provider information/)).not.toBeInTheDocument();
  });
  it("prevents duplicate loads and unsubscribes on unmount", async () => {
    const unsubscribe=vi.fn();mocks.observe.mockReturnValue(unsubscribe);
    mocks.list.mockReturnValue(new Promise(()=>{}));const view=render(<ClassRecoveryPanel />);
    const button=await screen.findByRole("button",{name:"Load academies"});fireEvent.click(button);fireEvent.click(button);
    expect(mocks.list).toHaveBeenCalledTimes(1);view.unmount();expect(unsubscribe).toHaveBeenCalledTimes(1);
  });
  it("clears displayed details when the page becomes visible", async () => {
    vi.spyOn(document,"visibilityState","get").mockReturnValue("visible");render(<ClassRecoveryPanel />);
    fireEvent.click(await screen.findByRole("button",{name:"Load academies"}));await screen.findByRole("option",{name:"Badminton Academy"});
    fireEvent.change(screen.getByLabelText("Academy"),{target:{value:academy}});await screen.findByText(/Dance/);
    fireEvent(document,new Event("visibilitychange"));expect(screen.queryByText(/Dance/)).not.toBeInTheDocument();
  });
  it("distinguishes an acknowledged completion", async () => {
    mocks.recover.mockResolvedValue({ok:true,state:"completed",courseName:"Dance",batchName:"Morning",acknowledged:true});
    render(<ClassRecoveryPanel />);fireEvent.click(await screen.findByRole("button",{name:"Load academies"}));await screen.findByRole("option",{name:"Badminton Academy"});
    fireEvent.change(screen.getByLabelText("Academy"),{target:{value:academy}});
    expect(await screen.findByText("Setup completed — acknowledged")).toBeInTheDocument();
  });
  it("ignores a late session callback after unmount", async () => {
    let notify!: (event:string)=>void;const unsubscribe=vi.fn();
    mocks.observe.mockImplementation((callback)=>{notify=callback;return unsubscribe;});
    const view=render(<ClassRecoveryPanel />);await screen.findByRole("button",{name:"Load academies"});
    view.unmount();act(()=>notify("SIGNED_OUT"));expect(unsubscribe).toHaveBeenCalledTimes(1);
  });
  it("shows completed state without assuming it was acknowledged", async () => {
    mocks.recover.mockResolvedValue({ok:true,state:"completed",courseName:"Dance",batchName:"Morning",acknowledged:false});
    render(<ClassRecoveryPanel />);fireEvent.click(await screen.findByRole("button",{name:"Load academies"}));await screen.findByRole("option",{name:"Badminton Academy"});
    fireEvent.change(screen.getByLabelText("Academy"),{target:{value:academy}});
    expect(await screen.findByText("Setup completed — not yet acknowledged")).toBeInTheDocument();
  });

});
