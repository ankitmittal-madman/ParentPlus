"use client";
import { useEffect, useRef, useState } from "react";
import { parentSignalRequestStatus, sendParentSignal } from "@/lib/parent-feed/actions";
import { button, buttonClass, field } from "../attendance/copy";
import { type SignalReason, type SignalType } from "../attendance/contracts";
import { clearPending, readPending, readVolatilePending, retainVolatilePending, writePending, type PendingOperation } from "../attendance/pending";
import type { ParentSession } from "./contracts";
import { useParentCopy } from "./copy";
type Props = { actorId: string; selection: { childId: string; workspaceId: string; session: ParentSession } | null; scopeKey: string; capture: () => () => boolean; onResolved: (outcome: "saved" | "rejected" | "conflict") => void; onPending: (blocked: boolean) => void };
export function SignalCenter({ actorId, selection, scopeKey, capture, onResolved, onPending }: Props) {
  const { t } = useParentCopy();
  const [pending, setPending] = useState<PendingOperation | null>(null), [corrupt, setCorrupt] = useState(false), [volatile, setVolatile] = useState(false);
  const [type, setType] = useState<SignalType>("running_late"), [reason, setReason] = useState<SignalReason | "">("");
  const [busy, setBusy] = useState(false), [unknown, setUnknown] = useState(false);
  const heading = useRef<HTMLHeadingElement>(null), lock = useRef(false), attempt = useRef(0);
  const props = useRef({ onPending, onResolved });
  useEffect(() => { props.current = { onPending, onResolved }; });
  useEffect(() => {
    let alive = true;
    queueMicrotask(() => {
      if (!alive) return;
      const saved = readPending(actorId, "signal"), value = saved.kind === "pending" ? saved.value : readVolatilePending(actorId, "signal");
      setPending(value); setCorrupt(saved.kind === "corrupt"); setVolatile(saved.kind === "unavailable"); props.current.onPending(saved.kind === "corrupt" || value !== null);
    });
    return () => { alive = false; lock.current = false; };
  }, [actorId]);
  // Recovery follows deliberate view invalidation, not automatic selector loading.
  useEffect(() => {
    attempt.current++;
    lock.current = false;
    queueMicrotask(() => setBusy(false));
  }, [scopeKey]);
  useEffect(() => {
    queueMicrotask(() => { setType("running_late"); setReason(""); });
  }, [scopeKey, selection?.session.id, selection?.session.version]);
  useEffect(() => { if (selection?.session.id && !pending && !corrupt) heading.current?.focus(); }, [selection?.session.id, pending, corrupt]);
  async function execute(operation: PendingOperation, check: boolean) {
    if (lock.current) return;
    lock.current = true; setBusy(true); setUnknown(false);
    const current = capture(), sequence = ++attempt.current;
    try {
      const input = { requestId: operation.requestId, payload: operation.payload };
      const result = check ? await parentSignalRequestStatus(actorId, input) : await sendParentSignal(actorId, input);
      if (!current() || sequence !== attempt.current) return;
      if (result.ok && (!check || ("state" in result.data && result.data.state === "known"))) {
        clearPending(operation); setPending(null); setVolatile(false); props.current.onPending(false); props.current.onResolved("saved");
      } else if (!result.ok && result.kind !== "unknown") {
        clearPending(operation); setPending(null); setVolatile(false); props.current.onPending(false); props.current.onResolved(result.kind === "conflict" ? "conflict" : "rejected");
      } else setUnknown(true);
    } catch { if (current() && sequence === attempt.current) setUnknown(true); }
    finally { if (current() && sequence === attempt.current) { lock.current = false; setBusy(false); } }
  }
  function send() {
    if (!selection || pending || corrupt || lock.current || !selection.session.canSignal || (type === "missing_today" && !reason)) return;
    const saved = readPending(actorId, "signal"), memory = readVolatilePending(actorId, "signal");
    if (saved.kind === "corrupt") { setCorrupt(true); props.current.onPending(true); return; }
    if (saved.kind === "pending" || memory) { setPending(saved.kind === "pending" ? saved.value : memory); props.current.onPending(true); return; }
    const operation: PendingOperation = { format: 1, actorId, requestId: crypto.randomUUID(), payload: { operation: "send_parent_signal", child_id: selection.childId, workspace_id: selection.workspaceId, session_id: selection.session.id, expected_session_version: selection.session.version, type, reason: type === "missing_today" ? reason as SignalReason : null } };
    const stored = writePending(operation);
    if (stored === "blocked") { setCorrupt(true); props.current.onPending(true); return; }
    if (stored === "unavailable") { if (!retainVolatilePending(operation)) { setCorrupt(true); props.current.onPending(true); return; } setVolatile(true); }
    setPending(operation); props.current.onPending(true); void execute(operation, false);
  }
  if (!pending && !corrupt && !selection) return null;
  return <section className="mt-5 rounded-2xl border border-[#D5E3DE] bg-white p-4" aria-label={t.report}>
    <h2 ref={heading} tabIndex={-1} className="font-bold">{t.report}</h2><p className="mt-2 text-xs">{t.reportNotice}</p>
    {corrupt && <p role="alert" className="mt-3">{t.corrupt}</p>}{volatile && <p role="status" className="mt-3 text-sm">{t.keepTabOpen}</p>}
    {pending ? <><p role="status" className="mt-3 text-sm">{unknown ? t.unknown : t.pendingReport}</p><div className="mt-3 flex flex-wrap gap-2"><button className={button} disabled={busy} onClick={() => void execute(pending, true)}>{t.check}</button><button className={button} disabled={busy} onClick={() => void execute(pending, false)}>{t.retry}</button></div></> : !corrupt && selection?.session.canSignal ? <>
      <p className="mt-3 text-sm font-semibold">{selection.session.batchName}</p><div className="mt-3 grid grid-cols-2 gap-2">{(["running_late", "missing_today", "dropped_off", "picked_up"] as const).map(value => <button key={value} className={buttonClass(type === value ? "selected" : "default")} aria-pressed={type === value} onClick={() => { setType(value); setReason(""); }}>{t[value]}</button>)}</div>
      {type === "missing_today" && <label className="mt-3 block text-sm">{t.reason}<select aria-label={t.reason} className={`${field} mt-1`} value={reason} onChange={e => setReason(e.target.value as SignalReason | "")}><option value="">{t.chooseReason}</option>{(["unwell", "travelling", "other"] as const).map(value => <option key={value} value={value}>{t[value]}</option>)}</select></label>}
      <button className={`${buttonClass("primary")} mt-3 w-full`} disabled={busy || (type === "missing_today" && !reason)} onClick={send}>{t.send}</button>
    </> : null}
  </section>;
}
