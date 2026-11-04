"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { observeSessionChanges } from "@/lib/auth/session-observer";
import { runChildCreation } from "@/lib/parent/child-creation-journey";
import { CHILD_CREATION_CONFIRMED, CHILD_PROFILES_CHANGED } from "@/lib/parent/events";

type Current = { intentId: string; childId: string; name: string; acknowledged: boolean; priorIntentId: string | null; requestId: string };
type Recovery = { actor: string; operation: "begin" | "ack"; priorIntentId: string | null; requestId: string | null; displayName: string | null };
const sameId = (left: string | null, right: string | null) => (left?.toLowerCase() ?? null) === (right?.toLowerCase() ?? null);

export default function ChildCreationPanel() {
  const [monitor, setMonitor] = useState<"checking" | "ready" | "unavailable">("checking");
  const [actor, setActor] = useState("");
  const [checked, setChecked] = useState(false);
  const [current, setCurrent] = useState<Current | null>(null);
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [retryReady, setRetryReady] = useState(false);
  const [recoveryLocked, setRecoveryLocked] = useState(false);
  const inFlight = useRef(false);
  const generation = useRef(0);
  const writeContext = useRef<Recovery | null>(null);
  const requiredRecovery = useRef<Recovery | null>(null);

  useEffect(() => {
    let active = true;
    let unsubscribe: (() => void) | undefined;
    const invalidate = () => {
      if (!active) return;
      if (writeContext.current) requiredRecovery.current = { ...writeContext.current, displayName: null };
      else if (requiredRecovery.current) requiredRecovery.current = { ...requiredRecovery.current, displayName: null };
      setRecoveryLocked(requiredRecovery.current !== null);
      writeContext.current = null; generation.current += 1; inFlight.current = false;
      setActor(""); setChecked(false); setCurrent(null); setAdding(false); setName(""); setBusy(false); setRetryReady(false);
      setNotice(requiredRecovery.current ? "A request may still be processing. Sign in to the original account and check its status." : "Your session may have changed. Check creation status again.");
    };
    const visible = () => { if (document.visibilityState === "visible") invalidate(); };
    try {
      if (process.env.NEXT_PUBLIC_ENABLE_LIVE_OTP !== "true") throw new Error("Session observation disabled");
      unsubscribe = observeSessionChanges(invalidate);
      window.addEventListener("focus", invalidate);
      document.addEventListener("visibilitychange", visible);
      queueMicrotask(() => { if (active) setMonitor("ready"); });
    } catch { queueMicrotask(() => { if (active) setMonitor("unavailable"); }); }
    return () => {
      active = false; generation.current += 1;
      window.removeEventListener("focus", invalidate);
      document.removeEventListener("visibilitychange", visible);
      unsubscribe?.();
    };
  }, []);

  async function checkStatus() {
    if (monitor !== "ready" || inFlight.current) return;
    inFlight.current = true; setBusy(true); setNotice(""); setActor(""); setChecked(false); setCurrent(null); setAdding(false); setName(""); setRetryReady(false);
    const currentGeneration = ++generation.current;
    const required = requiredRecovery.current;
    try {
      const result = await runChildCreation(required ? { operation: "status", expectedActorId: required.actor } : { operation: "status" });
      if (currentGeneration !== generation.current) return;
      if (!result.ok || result.operation !== "status" || (required && result.actorId.toLowerCase() !== required.actor.toLowerCase())) {
        setNotice("Unable to confirm the profile. Sign in to the original account and check its status."); return;
      }
      if (required) {
        const resolved = result.current && (required.operation === "begin"
          ? sameId(result.current.requestId, required.requestId) && sameId(result.current.priorIntentId, required.priorIntentId)
          : sameId(result.current.intentId, required.priorIntentId) && result.current.acknowledged);
        if (resolved) {
          if (required.operation === "begin") window.dispatchEvent(new Event(CHILD_CREATION_CONFIRMED));
          requiredRecovery.current = null; setRecoveryLocked(false);
        } else {
          setActor(result.actorId);
          const canRetry = required.operation === "begin" && required.displayName !== null && required.requestId !== null;
          setRetryReady(canRetry);
          setNotice(canRetry ? "Unable to confirm the earlier request. Check its status or retry the same request." : "Unable to confirm the earlier request. Do not start another until it is resolved."); return;
        }
      }
      setActor(result.actorId); setChecked(true); setCurrent(result.current); setAdding(result.current === null);
    } catch { if (currentGeneration === generation.current) setNotice("Unable to confirm the profile. Check its status again."); }
    finally { if (currentGeneration === generation.current) { inFlight.current = false; setBusy(false); } }
  }

  async function perform(operation: "begin" | "ack", retry?: Recovery) {
    if (!actor || inFlight.current || (!retry && (!checked || requiredRecovery.current))) return;
    if (retry && (retry !== requiredRecovery.current || retry.actor.toLowerCase() !== actor.toLowerCase()
        || retry.operation !== "begin" || !retry.displayName || !retry.requestId)) return;
    const cleanName = retry?.displayName ?? name.trim();
    if (operation === "begin" && (!cleanName || Array.from(cleanName).length > 120)) { setNotice("Enter a child name of up to 120 characters."); return; }
    if (operation === "ack" && !current) return;
    const priorIntentId = retry ? retry.priorIntentId : operation === "ack" ? current!.intentId : current?.intentId ?? null;
    let requestId: string | null = retry?.requestId ?? null;
    if (operation === "begin" && !requestId) {
      try { requestId = globalThis.crypto.randomUUID(); }
      catch { setNotice("Unable to start the request. Please try again."); return; }
    }
    const scope: Recovery = { actor, operation, priorIntentId, requestId, displayName: operation === "begin" ? cleanName : null };
    writeContext.current = scope; inFlight.current = true; setBusy(true); setRetryReady(false); setNotice("");
    const currentGeneration = ++generation.current;
    if (operation === "begin") window.dispatchEvent(new Event(CHILD_PROFILES_CHANGED));
    try {
      const result = operation === "begin"
        ? await runChildCreation({ operation, expectedActorId: actor, displayName: cleanName, priorIntentId, requestId })
        : await runChildCreation({ operation, expectedActorId: actor, intentId: priorIntentId });
      if (currentGeneration !== generation.current) return;
      if (!result.ok || result.operation !== operation) throw new Error("unconfirmed");
      const expectedIntent = result.operation === "begin" ? result.current.intentId : priorIntentId;
      const confirmation = await runChildCreation({ operation: "status", expectedActorId: actor });
      if (currentGeneration !== generation.current) return;
      if (!confirmation.ok || confirmation.operation !== "status" || confirmation.actorId.toLowerCase() !== actor.toLowerCase()
          || !confirmation.current || confirmation.current.intentId !== expectedIntent
          || (result.operation === "begin" && (confirmation.current.childId !== result.current.childId || confirmation.current.name !== result.current.name
            || !sameId(confirmation.current.requestId, requestId) || !sameId(confirmation.current.priorIntentId, priorIntentId)))
          || (operation === "ack" && (!confirmation.current.acknowledged || confirmation.current.childId !== current?.childId || confirmation.current.name !== current.name))) throw new Error("unconfirmed");
      if (operation === "begin") window.dispatchEvent(new Event(CHILD_CREATION_CONFIRMED));
      requiredRecovery.current = null; setRecoveryLocked(false); setChecked(true); setCurrent(confirmation.current); setAdding(false); setName("");
    } catch {
      if (currentGeneration === generation.current) {
        requiredRecovery.current = scope; setRecoveryLocked(true); setChecked(false); setCurrent(null); setAdding(false); setName("");
        setNotice("Unable to confirm the profile. Check creation status before trying again.");
      }
    } finally {
      if (currentGeneration === generation.current) {
        writeContext.current = null; inFlight.current = false; setBusy(false);
      }
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); void perform("begin"); }

  return <section aria-labelledby="child-creation-title" className="mt-8 rounded-2xl bg-white p-5 shadow-sm">
    <h2 id="child-creation-title" className="text-lg font-bold">Create a child profile</h2>
    <p className="mt-2 text-sm">This records a provisional relationship. It does not verify guardianship or connect to an academy.</p>
    {monitor === "checking" && <p role="status">Checking session monitoring…</p>}
    {monitor === "unavailable" && <p role="alert">Session monitoring is unavailable. Profiles cannot be created.</p>}
    {monitor === "ready" && <>
      <button type="button" disabled={busy} onClick={checkStatus} className="mt-4 rounded-lg bg-[#1F6F6B] px-4 py-2 font-semibold text-white disabled:opacity-50">Check creation status</button>
      {busy && <p role="status">Checking…</p>}
      {notice && <p role="alert">{notice}</p>}
      {retryReady && <button type="button" disabled={busy} onClick={() => { const retry = requiredRecovery.current; if (retry) void perform("begin", retry); }} className="mt-3 rounded-lg border px-4 py-2">Retry same request</button>}
      {checked && current && <div className="mt-3"><p>Profile: {current.name}</p><p>{current.acknowledged ? "Result confirmed" : "Please confirm you have seen this result."}</p></div>}
      {checked && current && !current.acknowledged && !recoveryLocked && <button type="button" disabled={busy} onClick={() => { void perform("ack"); }} className="mt-3 rounded-lg border px-4 py-2">Confirm result</button>}
      {checked && current?.acknowledged && !adding && !recoveryLocked && <button type="button" disabled={busy} onClick={() => setAdding(true)} className="mt-3 rounded-lg border px-4 py-2">Add another profile</button>}
      {checked && adding && !recoveryLocked && <form onSubmit={submit} className="mt-4 space-y-3">
        <label htmlFor="new-child-name" className="block font-semibold">Child name</label>
        <input id="new-child-name" value={name} disabled={busy} onChange={(event) => { setName(event.target.value); setNotice(""); }} className="w-full rounded-lg border p-2" />
        <button type="submit" disabled={busy} className="rounded-lg bg-[#1F6F6B] px-4 py-2 font-semibold text-white disabled:opacity-50">Create profile</button>
      </form>}
    </>}
  </section>;
}
