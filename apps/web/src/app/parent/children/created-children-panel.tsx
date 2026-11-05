"use client";

import { useEffect, useRef, useState } from "react";
import { observeSessionChanges } from "@/lib/auth/session-observer";
import { listCreatedChildren } from "@/lib/parent/list-created-children";
import { readRecoveryMarker } from "@/lib/parent/child-creation-recovery";
import { CHILD_CREATION_CONFIRMED, CHILD_PROFILES_CHANGED } from "@/lib/parent/events";

const storageNotice = "The list cannot be loaded until browser storage can be checked. Check browser settings and reload; saved information may also be invalid. Do not clear saved data while a request may be pending.";

type Children = { id: string; name: string }[];

export default function CreatedChildrenPanel() {
  const [monitor, setMonitor] = useState<"checking" | "ready" | "unavailable">("checking");
  const [children, setChildren] = useState<Children | null>(null);
  const [loading, setLoading] = useState(false);
  const [creationPending, setCreationPending] = useState(false);
  const [notice, setNotice] = useState("");
  const generation = useRef(0);
  const busy = useRef(false);
  const creationPendingRef = useRef(false);

  useEffect(() => {
    let active = true;
    let unsubscribe: (() => void) | undefined;
    const invalidate = () => {
      if (!active) return;
      generation.current += 1; busy.current = false;
      setChildren(null); setLoading(false);
      setNotice(creationPendingRef.current ? (readRecoveryMarker().state === "unavailable" ? storageNotice : "A profile request remains unresolved. The list will be available after recovery is completed.") : "Your session may have changed. Load profiles again to continue.");
    };
    const visible = () => { if (document.visibilityState === "visible") invalidate(); };
    const clearForCreation = (pending: boolean, unavailable = false) => {
      if (!active) return;
      creationPendingRef.current = pending; setCreationPending(pending);
      generation.current += 1; busy.current = false;
      setChildren(null); setLoading(false);
      setNotice(unavailable ? storageNotice : pending ? "A profile request remains unresolved. The list will be available after recovery is completed." : "The profile list may have changed. Load profiles again to refresh.");
    };
    const profileChanged = () => clearForCreation(true);
    const profileConfirmed = () => { const state = readRecoveryMarker().state; clearForCreation(state !== "none", state === "unavailable"); };
    try {
      if (process.env.NEXT_PUBLIC_ENABLE_LIVE_OTP !== "true") throw new Error("Session observation disabled");
      const stored = readRecoveryMarker();
      if (stored.state !== "none") clearForCreation(true, stored.state === "unavailable");
      unsubscribe = observeSessionChanges(invalidate);
      window.addEventListener("focus", invalidate);
      window.addEventListener(CHILD_PROFILES_CHANGED, profileChanged);
      window.addEventListener(CHILD_CREATION_CONFIRMED, profileConfirmed);
      document.addEventListener("visibilitychange", visible);
      queueMicrotask(() => { if (active) setMonitor("ready"); });
    } catch { queueMicrotask(() => { if (active) setMonitor("unavailable"); }); }
    return () => {
      active = false; generation.current += 1;
      window.removeEventListener("focus", invalidate);
      window.removeEventListener(CHILD_PROFILES_CHANGED, profileChanged);
      window.removeEventListener(CHILD_CREATION_CONFIRMED, profileConfirmed);
      document.removeEventListener("visibilitychange", visible);
      unsubscribe?.();
    };
  }, []);

  async function load() {
    if (monitor !== "ready" || busy.current || creationPendingRef.current) return;
    const stored = readRecoveryMarker();
    if (stored.state !== "none") {
      creationPendingRef.current = true; setCreationPending(true); setChildren(null);
      setNotice(stored.state === "unavailable" ? storageNotice : "A profile request remains unresolved. The list will be available after recovery is completed."); return;
    }
    busy.current = true; setLoading(true); setChildren(null); setNotice("");
    const current = ++generation.current;
    try {
      const result = await listCreatedChildren();
      if (current !== generation.current) return;
      if (!result.ok) { setNotice("Unable to load profiles. Please try again."); return; }
      setChildren(result.children);
    } catch { if (current === generation.current) setNotice("Unable to load profiles. Please try again."); }
    finally { if (current === generation.current) { busy.current = false; setLoading(false); } }
  }

  return <section aria-labelledby="created-children-title" className="mt-8 rounded-2xl bg-white p-5 shadow-sm">
    <h2 id="created-children-title" className="text-lg font-bold">Profiles you created</h2>
    <p className="mt-2 text-sm">This list may not include all linked children or profiles you can no longer access. It does not verify guardianship.</p>
    {monitor === "checking" && <p role="status">Checking session monitoring…</p>}
    {monitor === "unavailable" && <p role="alert">Session monitoring is unavailable. Profiles cannot be loaded.</p>}
    {monitor === "ready" && <>
      <button type="button" disabled={loading || creationPending} onClick={load} className="mt-4 rounded-lg bg-[#1F6F6B] px-4 py-2 font-semibold text-white disabled:opacity-50">Load profiles</button>
      {loading && <p role="status">Loading profiles…</p>}
      {notice && <p role="alert">{notice}</p>}
      {children?.length === 0 && <p>No profiles available for this account.</p>}
      {children && children.length > 0 && <ul className="mt-3 list-disc pl-5">{children.map((child) => <li key={child.id}>{child.name}</li>)}</ul>}
    </>}
  </section>;
}
