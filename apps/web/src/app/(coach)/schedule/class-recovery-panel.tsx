"use client";

import { useEffect, useRef, useState } from "react";
import { observeSessionChanges } from "@/lib/auth/session-observer";
import { listClassWorkspaces } from "@/lib/scheduling/list-class-workspaces";
import { recoverCurrentClassSetup } from "@/lib/scheduling/recover-current-class-setup";

type Workspace = { id: string; name: string };
type Recovery = Extract<Awaited<ReturnType<typeof recoverCurrentClassSetup>>, { ok: true }>;

export default function ClassRecoveryPanel() {
  const [monitor, setMonitor] = useState<"checking" | "ready" | "unavailable">("checking");
  const [actor, setActor] = useState("");
  const [workspaces, setWorkspaces] = useState<Workspace[] | null>(null);
  const [selected, setSelected] = useState("");
  const [recovery, setRecovery] = useState<Recovery | null>(null);
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(false);
  const generation = useRef(0);
  const busy = useRef(false);

  useEffect(() => {
    let active = true;
    let unsubscribe: (() => void) | undefined;
    const invalidate = () => {
      if (!active) return;
      generation.current += 1; busy.current = false;
      setActor(""); setWorkspaces(null); setSelected(""); setRecovery(null); setLoading(false);
      setNotice("Your session may have changed. Load academies again to continue.");
    };
    const visible = () => { if (document.visibilityState === "visible") invalidate(); };
    try {
      if (process.env.NEXT_PUBLIC_ENABLE_LIVE_OTP !== "true") throw new Error("Session observation disabled");
      unsubscribe = observeSessionChanges(invalidate);
      window.addEventListener("focus", invalidate);
      document.addEventListener("visibilitychange", visible);
      queueMicrotask(() => { if (active) setMonitor("ready"); });
    } catch {
      queueMicrotask(() => { if (active) setMonitor("unavailable"); });
    }
    return () => {
      active = false; generation.current += 1;
      window.removeEventListener("focus", invalidate);
      document.removeEventListener("visibilitychange", visible);
      unsubscribe?.();
    };
  }, []);

  async function loadAcademies() {
    if (monitor !== "ready" || busy.current) return;
    busy.current = true; setLoading(true); setNotice(""); setActor(""); setWorkspaces(null); setSelected(""); setRecovery(null);
    const current = ++generation.current;
    try {
      const result = await listClassWorkspaces();
      if (current !== generation.current) return;
      if (!result.ok) { setNotice("Unable to load academies. Please try again."); return; }
      setActor(result.actorId); setWorkspaces(result.workspaces);
    } catch { if (current === generation.current) setNotice("Unable to load academies. Please try again."); }
    finally { if (current === generation.current) { busy.current = false; setLoading(false); } }
  }

  async function selectAcademy(id: string) {
    const current = ++generation.current;
    setSelected(id); setRecovery(null); setNotice(""); setLoading(false); busy.current = false;
    if (!actor || !workspaces?.some((workspace) => workspace.id === id)) return;
    setLoading(true);
    try {
      const result = await recoverCurrentClassSetup({ workspaceId: id, expectedActorId: actor });
      if (current !== generation.current) return;
      if (!result.ok) { setNotice("Unable to check this setup. Do not start a new request until it is resolved."); return; }
      setRecovery(result);
    } catch { if (current === generation.current) setNotice("Unable to check this setup. Do not start a new request until it is resolved."); }
    finally { if (current === generation.current) setLoading(false); }
  }

  return (
    <section aria-labelledby="class-recovery-title" className="mt-8 rounded-2xl bg-white p-5 shadow-sm">
      <h2 id="class-recovery-title" className="text-lg font-bold">Check class setup</h2>
      <p className="mt-2 text-sm">Review current account data for an academy. This screen does not create or change a class.</p>
      {monitor === "checking" && <p role="status">Checking session monitoring…</p>}
      {monitor === "unavailable" && <p role="alert">Session monitoring is unavailable. Class setup cannot be checked.</p>}
      {monitor === "ready" && <>
        <button type="button" disabled={loading} onClick={loadAcademies} className="mt-4 rounded-lg bg-[#1F6F6B] px-4 py-2 font-semibold text-white disabled:opacity-50">Load academies</button>
        {workspaces?.length === 0 && <p className="mt-3">No eligible academies were found.</p>}
        {workspaces && workspaces.length > 0 && <div className="mt-4">
          <label htmlFor="recovery-academy" className="block font-semibold">Academy</label>
          <select id="recovery-academy" value={selected} onChange={(event) => { void selectAcademy(event.target.value); }} className="mt-1 w-full rounded-lg border p-2">
            <option value="">Choose an academy</option>
            {workspaces.map((workspace) => <option key={workspace.id} value={workspace.id}>{workspace.name}</option>)}
          </select>
        </div>}
        {loading && <p role="status" className="mt-3">Checking…</p>}
        {notice && <p role="alert" className="mt-3">{notice}</p>}
        {recovery?.state === "unknown" && <p role="status" className="mt-3">We cannot confirm the current setup. Do not start a new request until it is resolved.</p>}
        {recovery && recovery.state !== "unknown" && <div role="status" className="mt-3">
          <p>{recovery.state === "pending" ? "Setup pending" : recovery.acknowledged ? "Setup completed — acknowledged" : "Setup completed — not yet acknowledged"}</p>
          <p>Course: {recovery.courseName}</p><p>Batch: {recovery.batchName}</p>
        </div>}
      </>}
    </section>
  );
}
