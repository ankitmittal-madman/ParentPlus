import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { runClassSetupOperation } from "./class-setup-operations";

const mocks = vi.hoisted(() => ({ createClient: vi.fn(), getUser: vi.fn(), rpc: vi.fn() }));
vi.mock("@/lib/supabase/server", () => ({ createClient: mocks.createClient }));
const actor="b0000000-0000-4000-8000-000000000001", workspace="a0000000-0000-4000-8000-000000000001";
const intent="e0000000-0000-4000-8000-000000000001", request="e0000000-0000-4000-8000-000000000002";
const course="c0000000-0000-4000-8000-000000000001", batch="d0000000-0000-4000-8000-000000000001";
const base={workspaceId:workspace,expectedActorId:actor};

describe("runClassSetupOperation", () => {
  beforeEach(() => {
    vi.resetAllMocks(); vi.stubEnv("PARENTPLUS_ENABLE_CLASS_SETUP","true");
    mocks.createClient.mockResolvedValue({auth:{getUser:mocks.getUser},rpc:mocks.rpc});
    mocks.getUser.mockResolvedValue({data:{user:{id:actor}},error:null});
    mocks.rpc.mockResolvedValue({data:intent,error:null});
  });
  afterEach(() => vi.unstubAllEnvs());
  it("fails closed before contacting the provider when disabled", async () => {
    vi.stubEnv("PARENTPLUS_ENABLE_CLASS_SETUP","false");
    expect(await runClassSetupOperation({...base,operation:"reserve",courseName:"Art",batchName:"Morning"})).toEqual({ok:false,error:"Class setup is not available."});
    expect(mocks.createClient).not.toHaveBeenCalled();
  });
  it("rejects invalid inputs and operation-specific identifiers before provider access", async () => {
    for (const x of [null,{...base,operation:"unknown"},{...base,operation:{toString:()=>{throw new Error("invalid");}}},{...base,operation:"complete",intentId:"bad"},{...base,operation:"advance",priorIntentId:intent,requestId:"bad",courseName:"Art",batchName:"Morning"},{...base,operation:"reserve",courseName:" ",batchName:"Morning"},{...base,operation:"reserve",courseName:"x".repeat(121),batchName:"Morning"},{...base,operation:"acknowledge",intentId:intent,workspaceId:"bad"}]) {
      expect(await runClassSetupOperation(x)).toEqual({ok:false,error:"Check the class setup details."});
    }
    expect(mocks.createClient).not.toHaveBeenCalled();
  });
  it("rejects missing or changed identities before any write", async () => {
    mocks.getUser.mockResolvedValueOnce({data:{user:null},error:null}).mockResolvedValue({data:{user:{id:request}},error:null});
    expect(await runClassSetupOperation({...base,operation:"complete",intentId:intent})).toEqual({ok:false,error:"Please sign in to continue."});
    for (const x of [
      {...base,operation:"reserve",courseName:"Art",batchName:"Morning"},
      {...base,operation:"complete",intentId:intent},
      {...base,operation:"acknowledge",intentId:intent},
      {...base,operation:"advance",priorIntentId:intent,requestId:request,courseName:"Art",batchName:"Morning"},
    ]) expect(await runClassSetupOperation(x)).toEqual({ok:false,error:"Your account has changed. Sign in to the original account before continuing."});
    expect(mocks.rpc).not.toHaveBeenCalled();
  });
  it("reserves normalized names without sending a caller-supplied actor", async () => {
    expect(await runClassSetupOperation({...base,operation:"reserve",courseName:" Art ",batchName:" Morning ",actorId:"untrusted"})).toEqual({ok:true,operation:"reserve",intentId:intent});
    expect(mocks.rpc).toHaveBeenCalledWith("app_reserve_class_setup",{p_workspace_id:workspace,p_course_name:"Art",p_batch_name:"Morning"});
  });
  it("completes a reservation and validates returned identifiers", async () => {
    mocks.rpc.mockResolvedValue({data:[{course_id:course,batch_id:batch}],error:null});
    expect(await runClassSetupOperation({...base,operation:"complete",intentId:intent})).toEqual({ok:true,operation:"complete",courseId:course,batchId:batch});
    expect(mocks.rpc).toHaveBeenCalledWith("app_complete_class_setup",{p_workspace_id:workspace,p_intent_id:intent});
  });
  it("acknowledges only an explicit successful acknowledgement", async () => {
    mocks.rpc.mockResolvedValue({data:true,error:null});
    expect(await runClassSetupOperation({...base,operation:"acknowledge",intentId:intent})).toEqual({ok:true,operation:"acknowledge"});
    expect(mocks.rpc).toHaveBeenCalledWith("app_acknowledge_class_setup",{p_workspace_id:workspace,p_intent_id:intent});
  });
  it("advances with the original prior and request IDs", async () => {
    expect(await runClassSetupOperation({...base,operation:"advance",priorIntentId:intent,requestId:request,courseName:"Art",batchName:"Morning"})).toEqual({ok:true,operation:"advance",intentId:intent});
    expect(mocks.rpc).toHaveBeenCalledWith("app_advance_class_setup",{p_workspace_id:workspace,p_prior_intent_id:intent,p_request_id:request,p_course_name:"Art",p_batch_name:"Morning"});
  });
  it("treats RPC errors and thrown calls as uncertain without retrying", async () => {
    const x={...base,operation:"reserve",courseName:"Art",batchName:"Morning"};
    mocks.rpc.mockResolvedValueOnce({data:null,error:{message:"private"}}).mockRejectedValueOnce(new Error("private"));
    for (let n=0;n<2;n++) expect(await runClassSetupOperation(x)).toEqual({ok:false,error:"Unable to confirm class setup. Check its status before retrying."});
    expect(mocks.rpc).toHaveBeenCalledTimes(2);
  });
  it("does not claim success for malformed operation results", async () => {
    for (const [operation,data] of [["reserve","bad"],["advance",null],["acknowledge",false],["complete",[]],["complete",[{course_id:course,batch_id:"bad"}]]]) {
      mocks.rpc.mockResolvedValue({data,error:null});
      const x={...base,operation,courseName:"Art",batchName:"Morning",intentId:intent,priorIntentId:intent,requestId:request};
      expect(await runClassSetupOperation(x)).toEqual({ok:false,error:"Unable to confirm class setup. Check its status before retrying."});
    }
  });
});
