"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { observeSessionChanges } from "@/lib/auth/session-observer";
import { runChildCreation } from "@/lib/parent/child-creation-journey";
import { clearRecoveryMarker, readRecoveryMarker, writeRecoveryMarker, type RecoveryMarker } from "@/lib/parent/child-creation-recovery";
import { CHILD_CREATION_CONFIRMED, CHILD_PROFILES_CHANGED } from "@/lib/parent/events";

type Current = { intentId: string; childId: string; name: string; acknowledged: boolean; priorIntentId: string | null; requestId: string };
type Recovery = { actor: string; operation: "begin" | "ack"; priorIntentId: string | null; requestId: string | null; displayName: string | null };
const markerFor = (r: Recovery): RecoveryMarker => ({ version: 1, actor: r.actor, operation: r.operation, priorIntentId: r.priorIntentId, requestId: r.requestId });
const sameId = (left: string | null, right: string | null) => (left?.toLowerCase() ?? null) === (right?.toLowerCase() ?? null);

export default function ChildCreationPanel() {
  const [monitor, setMonitor] = useState<"checking" | "ready" | "unavailable" | "storage-unavailable">("checking");
  const [actor, setActor] = useState("");
  const [checked, setChecked] = useState(false);
  const [current, setCurrent] = useState<Current | null>(null);
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [retryReady, setRetryReady] = useState(false);
  const [retryAckReady, setRetryAckReady] = useState(false);
  const [fenceReady, setFenceReady] = useState(false);
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
      setActor(""); setChecked(false); setCurrent(null); setAdding(false); setName(""); setBusy(false); setRetryReady(false); setRetryAckReady(false); setFenceReady(false);
      setNotice(requiredRecovery.current ? "A request may still be processing. Sign in to the original account and check its status." : "Your session may have changed. Check creation status again.");
    };
    const visible = () => { if (document.visibilityState === "visible") invalidate(); };
    try {
      if (process.env.NEXT_PUBLIC_ENABLE_LIVE_OTP !== "true") throw new Error("Session observation disabled");
      const stored = readRecoveryMarker();
      if (stored.state === "unavailable") {
        queueMicrotask(() => { if (active) setMonitor("storage-unavailable"); });
        return () => { active = false; generation.current += 1; };
      }
      if (stored.state === "present") {
        requiredRecovery.current = { ...stored.marker, displayName: null };
        queueMicrotask(() => { if (active) { setRecoveryLocked(true); setNotice("An earlier request needs checking. Sign in to the original account and check its status."); } });
      }
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
    inFlight.current = true; setBusy(true); setNotice(""); setActor(""); setChecked(false); setCurrent(null); setAdding(false); setName(""); setRetryReady(false); setRetryAckReady(false); setFenceReady(false);
    const currentGeneration = ++generation.current;
    let required = requiredRecovery.current;
    try {
      const stored = readRecoveryMarker();
      if (stored.state === "unavailable" || (required && (stored.state !== "present" || !writeRecoveryMarker(markerFor(required))))) {
        setNotice("Recovery information is unavailable. Do not start another request."); return;
      }
      if (!required && stored.state === "present") {
        required = { ...stored.marker, displayName: null }; requiredRecovery.current = required; setRecoveryLocked(true);
      }
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
          if (!clearRecoveryMarker(markerFor(required))) { setNotice("Unable to complete recovery. Check the status again."); return; }
          window.dispatchEvent(new Event(CHILD_CREATION_CONFIRMED));
          requiredRecovery.current = null; setRecoveryLocked(false);
        } else {
          setActor(result.actorId);
          const canRetry = required.operation === "begin" && required.displayName !== null && required.requestId !== null;
          const canRetryAck = required.operation === "ack" && !!result.current && sameId(result.current.intentId, required.priorIntentId) && !result.current.acknowledged;
          setRetryReady(canRetry); setRetryAckReady(canRetryAck);
          setFenceReady(required.operation === "begin" && required.requestId !== null);
          if (canRetryAck) setCurrent(result.current);
          setNotice(canRetry ? "Unable to confirm the earlier request. Check its status or retry the same request." : canRetryAck ? "Confirmation is not yet confirmed. You can retry the same confirmation." : "Unable to confirm the earlier request. Do not start another until it is resolved."); return;
        }
      }
      if (!required) {
        if (readRecoveryMarker().state !== "none") { setRecoveryLocked(true); setNotice("Recovery information changed. Check status again."); return; }
        setRecoveryLocked(false);
      }
      setActor(result.actorId); setChecked(true); setCurrent(result.current); setAdding(result.current === null);
    } catch { if (currentGeneration === generation.current) setNotice("Unable to confirm the profile. Check its status again."); }
    finally { if (currentGeneration === generation.current) { inFlight.current = false; setBusy(false); } }
  }

  async function resolveEarlierRequest() {
    const required = requiredRecovery.current;
    if (!fenceReady || !required || required.operation !== "begin" || !required.requestId || !actor || inFlight.current || !sameId(actor, required.actor)) return;
    const stored = readRecoveryMarker();
    if (stored.state !== "present" || !writeRecoveryMarker(markerFor(required))) { setNotice("Recovery information is unavailable. Check creation status again."); return; }
    inFlight.current = true; writeContext.current = required; setBusy(true); setFenceReady(false); setRetryReady(false); setNotice("");
    const currentGeneration = ++generation.current;
    try {
      const result = await runChildCreation({ operation: "fence", expectedActorId: required.actor, priorIntentId: required.priorIntentId, requestId: required.requestId });
      if (currentGeneration !== generation.current) return;
      if (!result.ok || result.operation !== "fence" || !sameId(result.actorId, required.actor)) throw new Error("unresolved");
      let historical = false;
      if (result.disposition === "unknown") {
        const history = await runChildCreation({ operation: "history", expectedActorId: required.actor, priorIntentId: required.priorIntentId, requestId: required.requestId });
        if (currentGeneration !== generation.current) return;
        if (!history.ok || history.operation !== "history" || !sameId(history.actorId, required.actor) || history.disposition !== "found") throw new Error("unresolved");
        historical = true;
      }
      const status = await runChildCreation({ operation: "status", expectedActorId: required.actor });
      if (currentGeneration !== generation.current) return;
      if (!status.ok || status.operation !== "status" || !sameId(status.actorId, required.actor)) throw new Error("unresolved");
      const matching = status.current && sameId(status.current.requestId, required.requestId) && sameId(status.current.priorIntentId, required.priorIntentId);
      const priorCurrent = required.priorIntentId === null ? status.current === null : !!status.current && sameId(status.current.intentId, required.priorIntentId) && status.current.acknowledged;
      if (!historical && ((result.disposition === "created" && !matching) || (result.disposition === "fenced" && !priorCurrent))) throw new Error("unresolved");
      if (!clearRecoveryMarker(markerFor(required))) throw new Error("unresolved");
      requiredRecovery.current = null; setRecoveryLocked(false); setChecked(!historical); setCurrent(historical ? null : status.current); setAdding(!historical && status.current === null); setName("");
      setNotice(historical ? "An earlier request created a profile. Check creation status before adding another." : result.disposition === "fenced" ? "The earlier request cannot create a profile. You can start a new request." : "The earlier profile was found. Please check the result.");
      window.dispatchEvent(new Event(CHILD_CREATION_CONFIRMED));
    } catch {
      if (currentGeneration === generation.current) { setChecked(false); setCurrent(null); setAdding(false); setRecoveryLocked(true); setNotice("Unable to resolve the earlier request. Check creation status again."); }
    } finally {
      if (currentGeneration === generation.current) { writeContext.current = null; inFlight.current = false; setBusy(false); }
    }
  }

  async function perform(operation: "begin" | "ack", retry?: Recovery) {
    if (!actor || inFlight.current || (!retry && (!checked || requiredRecovery.current))) return;
    if (retry && (retry !== requiredRecovery.current || retry.actor.toLowerCase() !== actor.toLowerCase()
        || retry.operation !== operation || (operation === "begin" && (!retry.displayName || !retry.requestId))
        || (operation === "ack" && (!retryAckReady || !current || !sameId(current.intentId, retry.priorIntentId) || current.acknowledged)))) return;
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
    const stored = readRecoveryMarker();
    if ((!retry && stored.state !== "none") || (retry && stored.state !== "present") || !writeRecoveryMarker(markerFor(scope))) {
      setChecked(false); setAdding(false); setName(""); setRecoveryLocked(true);
      if (stored.state === "present") requiredRecovery.current = { ...stored.marker, displayName: null };
      setNotice("Recovery information is unavailable or another request is unresolved. Check its status before continuing."); return;
    }
    writeContext.current = scope; inFlight.current = true; setBusy(true); setRetryReady(false); setRetryAckReady(false); setFenceReady(false); setNotice("");
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
      if (!clearRecoveryMarker(markerFor(scope))) throw new Error("recovery marker not cleared");
      window.dispatchEvent(new Event(CHILD_CREATION_CONFIRMED));
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
    {monitor === "storage-unavailable" && <p role="alert">Saved request information is unavailable. Check browser storage settings and reload. Do not clear saved data while a request may be pending.</p>}
    {monitor === "ready" && <>
      <button type="button" disabled={busy} onClick={checkStatus} className="mt-4 rounded-lg bg-[#1F6F6B] px-4 py-2 font-semibold text-white disabled:opacity-50">Check creation status</button>
      {busy && <p role="status">Checking…</p>}
      {notice && <p role="alert">{notice}</p>}
      {fenceReady && <div><p className="mt-3 text-sm">This attempts to permanently stop the request if it has not created a profile. If it already created one and the result is still available, we will show it. Otherwise the request may remain unresolved.</p><button type="button" disabled={busy} onClick={() => { void resolveEarlierRequest(); }} className="mt-3 rounded-lg border px-4 py-2">Stop waiting for this request</button></div>}
      {retryAckReady && <button type="button" disabled={busy} onClick={() => { const retry = requiredRecovery.current; if (retry) void perform("ack", retry); }} className="mt-3 rounded-lg border px-4 py-2">Retry confirmation</button>}
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
