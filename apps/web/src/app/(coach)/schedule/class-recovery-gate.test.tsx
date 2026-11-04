import { afterEach, describe, expect, it, vi } from "vitest";
import ClassRecoveryGate from "./class-recovery-gate";
import ClassRecoveryPanel from "./class-recovery-panel";

const mocks=vi.hoisted(()=>({connection:vi.fn()}));
vi.mock("next/server",()=>({connection:mocks.connection}));

describe("ClassRecoveryGate",()=>{
  afterEach(()=>{vi.unstubAllEnvs();vi.clearAllMocks();});
  it("checks the server flag after establishing a request and stays hidden by default",async()=>{
    vi.stubEnv("PARENTPLUS_ENABLE_CLASS_SETUP","false");
    expect(await ClassRecoveryGate()).toBeNull();
    expect(mocks.connection).toHaveBeenCalledOnce();
  });
  it("only exposes the read-only panel when explicitly enabled",async()=>{
    vi.stubEnv("PARENTPLUS_ENABLE_CLASS_SETUP","true");
    const result=await ClassRecoveryGate();
    expect(result?.type).toBe(ClassRecoveryPanel);
    expect(mocks.connection).toHaveBeenCalledOnce();
  });
});
