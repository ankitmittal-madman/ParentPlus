"use client";
import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { observeSessionChanges } from "@/lib/auth/session-observer";
import { checkWorkspaceSetup, createFirstWorkspace } from "@/lib/workspace/first-use";
const STORAGE = "parentplus.workspace-first-use.v1";
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
type Marker = { version: 1; actorId: string; requestId: string };
function readMarker(): Marker | null {
  const value = localStorage.getItem(STORAGE);
  if (value === null) return null;
  const marker = JSON.parse(value);
  if (marker?.version !== 1 || typeof marker.actorId !== "string" || !UUID.test(marker.actorId) || typeof marker.requestId !== "string" || !UUID.test(marker.requestId)) throw new Error("Invalid saved request");
  return { version: 1, actorId: marker.actorId, requestId: marker.requestId };
}

export default function WorkspaceForm() {
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(false);
  const [marker, setMarker] = useState<Marker | null>(null);
  const [workspace, setWorkspace] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [type, setType] = useState("independent");
  const [notice, setNotice] = useState("");
  const generation = useRef(0);
  const pending = useRef(false);
  useEffect(() => {
    const cancelPending = () => { generation.current += 1; };
    const invalidate = () => { generation.current++; setMarker(null); setWorkspace(null); setName(""); setNotice("Your session may have changed. Check workspace setup again."); };
    const visible = () => { if (document.visibilityState === "visible") invalidate(); };
    let unsubscribe: (() => void) | undefined;
    try {
      if (process.env.NEXT_PUBLIC_ENABLE_LIVE_OTP !== "true" || !navigator.locks?.request) throw new Error("Safe monitoring or storage locking unavailable");
      unsubscribe = observeSessionChanges(invalidate);
      window.addEventListener("focus", invalidate); window.addEventListener("storage", invalidate);
      document.addEventListener("visibilitychange", visible);
      queueMicrotask(() => setReady(true));
    } catch { queueMicrotask(() => setNotice("Session monitoring is unavailable.")); }
    return () => { cancelPending(); unsubscribe?.(); window.removeEventListener("focus", invalidate); window.removeEventListener("storage", invalidate); document.removeEventListener("visibilitychange", visible); };
  }, []);
  async function check() {
    if (pending.current) return;
    pending.current = true; setBusy(true); setMarker(null); setWorkspace(null); setNotice("");
    const current = ++generation.current;
    try {
      let saved = readMarker();
      const result = await checkWorkspaceSetup(saved ? { expectedActorId: saved.actorId, requestId: saved.requestId } : {});
      if (current !== generation.current) return;
      if (!result.ok) { setNotice(result.error); return; }
      // Storage events can arrive after the server response. Serialize allocation
      // across tabs and compare the exact marker before retaining this result.
      const confirmed = await navigator.locks.request(STORAGE, () => {
        if (current !== generation.current) return null;
        if (JSON.stringify(readMarker()) !== JSON.stringify(saved)) throw new Error("Saved request changed");
        if (!saved) {
          saved = { version: 1, actorId: result.actorId, requestId: crypto.randomUUID() };
          localStorage.setItem(STORAGE, JSON.stringify(saved));
        }
        return saved;
      });
      if (!confirmed || current !== generation.current) return;
      setMarker(confirmed); setWorkspace(result.workspaceId);
      setNotice(result.workspaceId ? "Workspace setup confirmed." : "No completed result is visible for this request. If you already tried, re-enter the original details to retry the same request.");
    } catch { if (current === generation.current) setNotice("Saved request information is unavailable. Do not clear storage while a request may be unresolved."); }
    finally { pending.current = false; setBusy(false); }
  }
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!marker || workspace || pending.current) return;
    pending.current = true; setBusy(true); setNotice("");
    const current = ++generation.current;
    try {
      const stored = readMarker();
      if (!stored || stored.actorId !== marker.actorId || stored.requestId !== marker.requestId) throw new Error("Saved request changed");
      const result = await createFirstWorkspace({ expectedActorId: marker.actorId, requestId: marker.requestId, name, type });
      if (current !== generation.current) return;
      if (result.ok && result.workspaceId) { setWorkspace(result.workspaceId); setName(""); setNotice("Workspace setup confirmed."); }
      else setNotice(result.ok ? "Workspace setup remains unresolved." : result.error);
    } catch { if (current === generation.current) setNotice("Workspace setup is unresolved. Check this request before retrying."); }
    finally { pending.current = false; setBusy(false); }
  }
  return <section className="mt-6 space-y-4 rounded-2xl bg-white p-5">
    <p>Create your own workspace or recover the same setup request. Existing academy access still requires an invitation.</p>
    <button type="button" disabled={!ready || busy} onClick={check} className="rounded-xl bg-brand p-3 font-semibold text-white">Check workspace setup</button>
    {marker && !workspace && <form onSubmit={create} className="space-y-3">
      <label htmlFor="workspace-name" className="block font-semibold">Workspace name</label>
      <input id="workspace-name" required minLength={2} maxLength={120} value={name} onChange={e => setName(e.target.value)} className="w-full rounded-xl border p-3" />
      <label htmlFor="workspace-type" className="block font-semibold">Workspace type</label>
      <select id="workspace-type" value={type} onChange={e => setType(e.target.value)} className="w-full rounded-xl border p-3"><option value="independent">Independent coach</option><option value="academy">Academy</option></select>
      <button disabled={busy} className="rounded-xl bg-brand p-3 font-semibold text-white">{busy ? "Creating…" : "Create workspace"}</button>
    </form>}
    {workspace && <Link href="/schedule" prefetch={false} className="block font-semibold text-brand underline">Continue to class setup</Link>}
    {notice && <p role="status">{notice}</p>}
  </section>;
}
