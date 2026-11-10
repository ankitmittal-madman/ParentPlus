"use client";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { listParentChildren, listParentAcademies, listParentBatches, listParentSessions, listParentItems, loadParentWeek } from "@/lib/parent-feed/actions";
import type { Result } from "../attendance/contracts";
import { button, buttonClass, field } from "../attendance/copy";
import { useSessionBoundary } from "../attendance/session-boundary";
import { date as validDate } from "../attendance/validation";
import { dateStrip, localDate, type Academy, type SessionCursor } from "../today/contracts";
import { mondayOf, type ItemCursor, type ParentBatch, type ParentChild, type ParentItemEnvelope, type ParentSession, type ParentWeek } from "./contracts";
import { ParentCopyProvider, ParentLanguageSelect, parentDate, useParentCopy } from "./copy";
import { ParentItemCard } from "./parent-item-card";
import { SignalCenter } from "./signal-center";
type Slot = "children" | "academies" | "batches" | "sessions" | "items" | "week";
type Scope = { childId: string; workspaceId: string; batchId: string | null; day: string; timeZone: string };
export function ParentHome() { return <ParentCopyProvider><Home /></ParentCopyProvider>; }
function Home() {
  const { t, lang } = useParentCopy();
  const [children, setChildren] = useState<ParentChild[]>([]), [childId, setChild] = useState("");
  const [academies, setAcademies] = useState<Academy[]>([]), [academyId, setAcademy] = useState("");
  const [batches, setBatches] = useState<ParentBatch[]>([]), [batchId, setBatch] = useState("");
  const [day, setDay] = useState("");
  const [viewRevision, setViewRevision] = useState(0);
  const [sessions, setSessions] = useState<ParentSession[]>([]), [items, setItems] = useState<ParentItemEnvelope[]>([]), [week, setWeek] = useState<ParentWeek | null>(null);
  const [nextAcademy, setNextAcademy] = useState<string | null>(null), [nextBatch, setNextBatch] = useState<string | null>(null), [nextSession, setNextSession] = useState<SessionCursor | null>(null), [nextItem, setNextItem] = useState<ItemCursor | null>(null);
  const [busy, setBusy] = useState<Partial<Record<Slot, boolean>>>({}), [errors, setErrors] = useState<Partial<Record<Slot, boolean>>>({}), [loaded, setLoaded] = useState<Partial<Record<Slot, boolean>>>({});
  const [selection, setSelection] = useState<ParentSession | null>(null), [blocked, setBlocked] = useState(false), [outcome, setOutcome] = useState<"saved" | "rejected" | "conflict" | null>(null), [lastRefresh, setLastRefresh] = useState("");
  const sequences = useRef<Record<Slot, number>>({ children: 0, academies: 0, batches: 0, sessions: 0, items: 0, week: 0 });
  const clearFacts = useCallback(() => {
    setSessions([]); setItems([]); setWeek(null); setNextSession(null); setNextItem(null); setSelection(null); setLastRefresh("");
  }, []);
  const resetReads = useCallback(() => {
    for (const key of Object.keys(sequences.current) as Slot[]) sequences.current[key]++;
    setBusy({}); setErrors({}); setLoaded({});
  }, []);
  const clearPrivate = useCallback(() => {
    resetReads(); clearFacts(); setChildren([]); setChild(""); setAcademies([]); setAcademy(""); setBatches([]); setBatch(""); setDay(""); setNextAcademy(null); setNextBatch(null); setBlocked(false); setOutcome(null);
  }, [clearFacts, resetReads]);
  const { actorId, ready, capture, invalidateView } = useSessionBoundary(clearPrivate);
  const academy = academies.find(a => a.workspaceId === academyId);
  const cancel = useCallback(() => { invalidateView(); setViewRevision(value => value + 1); resetReads(); clearFacts(); setOutcome(null); }, [invalidateView, resetReads, clearFacts]);
  const deny = useCallback(() => {
    cancel(); setAcademies([]); setAcademy(""); setBatches([]); setBatch(""); setDay(""); setNextAcademy(null); setNextBatch(null); setErrors({ academies: true });
  }, [cancel]);
  const perform = useCallback(async <T,>(slot: Slot, current: () => boolean, request: () => Promise<Result<T>>, apply: (v: T) => void) => {
    const sequence = ++sequences.current[slot];
    setBusy(old => ({ ...old, [slot]: true })); setErrors(old => ({ ...old, [slot]: false }));
    try {
      const result = await request();
      if (!current() || sequence !== sequences.current[slot]) return;
      if (result.ok) { setLoaded(old => ({ ...old, [slot]: true })); apply(result.data); }
      else if (result.kind === "forbidden") deny();
      else setErrors(old => ({ ...old, [slot]: true }));
    } catch { if (current() && sequence === sequences.current[slot]) setErrors(old => ({ ...old, [slot]: true })); }
    finally { if (current() && sequence === sequences.current[slot]) setBusy(old => ({ ...old, [slot]: false })); }
  }, [deny]);
  const fetchSessions = useCallback((actor: string, scope: Scope, after: SessionCursor | null, current: () => boolean) => perform("sessions", current, () => listParentSessions(actor, { childId: scope.childId, workspaceId: scope.workspaceId, batchId: scope.batchId, date: scope.day, after }), data => {
    if (data.timeZone !== scope.timeZone) { setSessions([]); setSelection(null); setLastRefresh(""); setErrors(old => ({ ...old, sessions: true })); return; }
    setSessions(old => after ? [...old, ...data.sessions] : data.sessions);
    if (!after) setSelection(old => old ? data.sessions.find(s => s.id === old.id && s.canSignal) ?? null : null);
    setNextSession(data.next); setLastRefresh(data.serverNow);
  }), [perform]);
  const fetchItems = useCallback((actor: string, scope: Scope, before: ItemCursor | null, current: () => boolean) => perform("items", current, () => listParentItems(actor, { childId: scope.childId, workspaceId: scope.workspaceId, batchId: scope.batchId, before }), data => {
    setItems(old => before ? [...old, ...data.items] : data.items); setNextItem(data.next);
  }), [perform]);
  const loadFacts = useCallback((actor: string, scope: Scope, current: () => boolean) => {
    if (!validDate(scope.day)) return;
    void fetchSessions(actor, scope, null, current); void fetchItems(actor, scope, null, current);
    void perform("week", current, () => loadParentWeek(actor, { childId: scope.childId, workspaceId: scope.workspaceId, batchId: scope.batchId, weekStart: mondayOf(scope.day) }), data => {
      if (data.timeZone === scope.timeZone) setWeek(data); else { setWeek(null); setErrors(old => ({ ...old, week: true })); }
    });
  }, [fetchSessions, fetchItems, perform]);
  const loadBatches = useCallback((actor: string, child: string, chosen: Academy, current: () => boolean) => {
    const selectedDay = chosen.timeZone ? localDate(chosen.timeZone) : ""; setDay(selectedDay);
    void perform("batches", current, () => listParentBatches(actor, { childId: child, workspaceId: chosen.workspaceId, after: null }), data => {
      setBatches(data.batches); setNextBatch(data.nextAfter); const selectedBatch = data.batches[0]?.batchId ?? ""; setBatch(selectedBatch);
      if (chosen.timeZone && data.batches.length) loadFacts(actor, { childId: child, workspaceId: chosen.workspaceId, batchId: selectedBatch || null, day: selectedDay, timeZone: chosen.timeZone }, current);
    });
  }, [perform, loadFacts]);
  const loadAcademies = useCallback((actor: string, child: string, current: () => boolean) => {
    void perform("academies", current, () => listParentAcademies(actor, { childId: child, after: null }), data => {
      setAcademies(data.academies); setNextAcademy(data.nextAfter); const chosen = data.academies[0]; setAcademy(chosen?.workspaceId ?? ""); if (chosen) loadBatches(actor, child, chosen, current);
    });
  }, [perform, loadBatches]);
  const initial = useCallback((actor: string, current: () => boolean) => {
    void perform("children", current, () => listParentChildren(actor), data => { setChildren(data); setChild(data[0]?.id ?? ""); if (data[0]) loadAcademies(actor, data[0].id, current); });
  }, [perform, loadAcademies]);
  useEffect(() => { if (!actorId) return; const current = capture(); queueMicrotask(() => { if (current()) initial(actorId, current); }); }, [actorId, capture, initial]);
  const scope: Scope | null = childId && academy?.timeZone && batches.length > 0 && validDate(day) ? { childId, workspaceId: academyId, batchId: batchId || null, day, timeZone: academy.timeZone } : null;
  const scopeRef = useRef(scope), actorRef = useRef(actorId);
  useEffect(() => { scopeRef.current = scope; actorRef.current = actorId; });
  // Keep all saved facts current together; session/account changes clear fetched private views first.
  useEffect(() => {
    if (!actorId) return;
    const timer = setInterval(() => { const value = scopeRef.current; if (document.visibilityState === "visible" && actorRef.current && value) loadFacts(actorRef.current, value, capture()); }, 15000);
    return () => clearInterval(timer);
  }, [actorId, capture, loadFacts]);
  function chooseChild(value: string) {
    cancel(); setChild(value); setAcademies([]); setAcademy(""); setBatches([]); setBatch(""); setDay(""); setNextAcademy(null); setNextBatch(null);
    if (actorId && children.some(c => c.id === value)) loadAcademies(actorId, value, capture());
  }
  function chooseAcademy(value: string) {
    cancel(); setAcademy(value); setBatches([]); setBatch(""); setNextBatch(null); setDay(""); const chosen = academies.find(a => a.workspaceId === value);
    if (actorId && chosen) loadBatches(actorId, childId, chosen, capture());
  }
  function chooseFacts(newDay: string, newBatch: string) {
    cancel(); setDay(newDay); setBatch(newBatch);
    if (actorId && academy?.timeZone && validDate(newDay)) loadFacts(actorId, { childId, workspaceId: academyId, batchId: newBatch || null, day: newDay, timeZone: academy.timeZone }, capture());
  }
  function refresh() {
    cancel(); if (!actorId) return; const current = capture();
    if (scope) { loadFacts(actorId, scope, current); return; }
    if (childId && academy) { setBatches([]); setNextBatch(null); loadBatches(actorId, childId, academy, current); return; }
    if (childId) { setAcademies([]); setNextAcademy(null); loadAcademies(actorId, childId, current); return; }
    initial(actorId, current);
  }
  const clock = (value: string) => new Intl.DateTimeFormat(lang === "en" ? "en-IN" : "hi-IN", { timeZone: academy?.timeZone ?? "UTC", hour: "numeric", minute: "2-digit" }).format(new Date(value));
  // Automatic selector bootstrap does not invalidate recovery for the same actor.
  // Explicit scope/Refresh changes advance this private view revision in cancel().
  const scopeKey = `${viewRevision}`;
  return <main className="min-h-screen bg-[#F3F5F1] text-[#22303A]"><div className="mx-auto min-h-screen max-w-lg pb-28 shadow-sm">
    <header className="rounded-b-3xl bg-[#1F6F6B] px-5 pb-6 pt-8 text-white"><p className="text-sm font-bold tracking-wide">ParentPlus</p><h1 className="mt-4 text-3xl font-extrabold">{t.title}</h1><p className="mt-2 text-sm">{t.intro}</p>{academy && <p className="mt-3 text-sm font-semibold">{academy.name}</p>}</header>
    <div className="space-y-5 px-5 pt-5"><ParentLanguageSelect />
      {!actorId ? <section className="rounded-2xl bg-white p-4"><p role="status">{ready ? t.sessionNeeded : t.monitorUnavailable}</p><Link href="/login" className={`${button} mt-3 inline-flex items-center`}>{t.signIn}</Link></section> : <>
        <button className={button} disabled={!!busy.children} onClick={refresh}>{t.refresh}</button>
        {Object.values(busy).some(Boolean) && <p role="status" aria-live="polite">{t.loading}</p>}
        {Object.values(errors).some(Boolean) && <p role="alert" className="rounded-xl bg-[#FFF0D5] p-3 text-sm">{t.failed}</p>}
        {outcome && <p role="status" aria-live="polite" className="rounded-xl bg-[#E1F0ED] p-3 text-sm">{t[outcome]}</p>}
        {loaded.children && !children.length && <p>{t.noChildren}</p>}
        {!!children.length && <label className="block text-sm font-semibold">{t.child}<select aria-label={t.child} className={`${field} mt-1`} value={childId} onChange={e => chooseChild(e.target.value)}>{children.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select></label>}
        {loaded.academies && !academies.length && <p>{t.noAcademies}</p>}
        {!!academies.length && <section className="rounded-2xl bg-white p-4"><label className="block text-sm font-semibold">{t.academy}<select aria-label={t.academy} className={`${field} mt-1`} value={academyId} onChange={e => chooseAcademy(e.target.value)}>{academies.map(a => <option key={a.workspaceId} value={a.workspaceId}>{a.name}</option>)}</select></label>{nextAcademy && <button className={`${button} mt-3`} disabled={busy.academies} onClick={() => { if (actorId) void perform("academies", capture(), () => listParentAcademies(actorId, { childId, after: nextAcademy }), data => { setAcademies(old => [...old, ...data.academies]); setNextAcademy(data.nextAfter); }); }}>{t.moreAcademies}</button>}</section>}
        {academy && !academy.timeZone && <p className="rounded-2xl bg-[#FFF0D5] p-4 text-sm">{t.zoneUnavailable}</p>}
        {loaded.batches && !batches.length && <p>{t.noBatches}</p>}
        {!!batches.length && <label className="block text-sm font-semibold">{t.batch}<select aria-label={t.batch} className={`${field} mt-1`} value={batchId} onChange={e => chooseFacts(day, e.target.value)}><option value="">{t.allClasses}</option>{batches.map(b => <option key={b.batchId} value={b.batchId}>{b.batchName} · {b.courseName}</option>)}</select>{nextBatch && <button className={`${button} mt-3`} disabled={busy.batches} onClick={() => { if (actorId) void perform("batches", capture(), () => listParentBatches(actorId, { childId, workspaceId: academyId, after: nextBatch }), data => { setBatches(old => [...old, ...data.batches]); setNextBatch(data.nextAfter); }); }}>{t.moreBatches}</button>}</label>}
        {academy?.timeZone && !!batches.length && <>
          <label className="block text-sm font-semibold">{t.date}<input type="date" aria-label={t.date} className={`${field} mt-1`} min="2000-01-01" max="2100-12-31" value={day} onChange={e => chooseFacts(e.target.value, batchId)} /></label>
          {validDate(day) && <div className="flex gap-1 overflow-x-auto pb-2">{dateStrip(day).map(value => <button key={value} className={`${buttonClass(value === day ? "selected" : "default")} flex min-w-14 flex-col items-center px-2`} aria-label={`${t.dateSelect} ${parentDate(value, lang)}`} aria-pressed={value === day} data-qa-action="Select parent session date" onClick={() => chooseFacts(value, batchId)}><span className="text-[10px]">{new Intl.DateTimeFormat(lang, { weekday: "short", timeZone: "UTC" }).format(new Date(`${value}T12:00:00Z`))}</span><span>{new Intl.NumberFormat(lang).format(Number(value.slice(-2)))}</span></button>)}</div>}
          <section aria-label={t.sessions}><h2 className="text-lg font-bold">{t.sessions}</h2>{lastRefresh && <p className="mt-1 text-xs text-[#5C6B73]">{t.lastRefresh}: {clock(lastRefresh)}</p>}{loaded.sessions && !busy.sessions && !errors.sessions && !sessions.length && <p className="mt-3 rounded-2xl bg-white p-4 text-sm">{t.noSessions}</p>}
            <div className="mt-3 space-y-3">{sessions.map((s, i) => <article key={s.id} className={`rounded-2xl border-l-4 p-4 ${i % 2 ? "border-[#D5A04B] bg-[#FFF1D9]" : "border-[#1F6F6B] bg-[#E1F0ED]"}`}><p className="text-xs">{clock(s.startsAt)} – {clock(s.endsAt)} · {s.courseName}</p><h3 className="mt-1 text-lg font-bold">{s.batchName}</h3><p className="mt-2 text-sm">{t[s.enrollmentStatus]}</p>{s.status === "cancelled" && <p className="mt-2 text-sm font-semibold">{t.cancelled}</p>}<p className="mt-2 text-sm font-semibold">{s.attendance ? `${t.confirmed}: ${t[s.attendance.status]}` : t.notRecorded}</p>{s.ownLatestSignal && <p className="mt-2 text-xs">{t.report}: {t[s.ownLatestSignal.type]}{s.ownLatestSignal.reason ? ` · ${t[s.ownLatestSignal.reason]}` : ""} · {clock(s.ownLatestSignal.createdAt)}</p>}{s.canSignal && !blocked ? <button className={`${button} mt-3`} aria-label={`${t.reportFor} ${s.batchName} ${clock(s.startsAt)}`} data-qa-action="Open parent report" onClick={() => setSelection(s)}>{t.report}</button> : <p className="mt-2 text-xs">{blocked ? t.pendingReport : t.reportUnavailable}</p>}</article>)}</div>
            {nextSession && scope && <button className={`${button} mt-3 w-full`} disabled={busy.sessions} onClick={() => void fetchSessions(actorId, scope, nextSession, capture())}>{t.moreSessions}</button>}
          </section>
          {week && <section aria-label={t.week} className="rounded-2xl bg-white p-4"><h2 className="text-lg font-bold">{t.week}</h2><p className="mt-1 text-xs">{t.weekStart} {parentDate(week.weekStart, lang)}</p><div className="mt-3 flex gap-6"><p className="text-sm"><strong className="block text-2xl text-[#1F6F6B]">{new Intl.NumberFormat(lang).format(week.attendedCount)}</strong>{t.attended}</p><p className="text-sm"><span className="block text-2xl font-bold">{new Intl.NumberFormat(lang).format(week.recordedCount)}</span>{t.recorded}</p></div>{!week.rows.length && <p className="mt-3 text-sm">{t.weekEmpty}</p>}<ul className="mt-3 space-y-2">{week.rows.map(r => <li key={r.sessionId} className="border-t border-[#E4ECE8] pt-2 text-xs">{parentDate(r.date, lang)} · {r.batchName} · {t[r.status]}</li>)}</ul>{week.hasMore && <p className="mt-3 text-xs">{t.weekMore}</p>}</section>}
          <section aria-label={t.feed}><h2 className="text-lg font-bold">{t.feed}</h2>{loaded.items && !busy.items && !errors.items && !items.length && <p className="mt-3 text-sm">{t.noItems}</p>}<div className="mt-3 space-y-3">{items.map(item => <ParentItemCard key={item.id} item={item} />)}</div>{nextItem && scope && <button className={`${button} mt-3 w-full`} disabled={busy.items} onClick={() => void fetchItems(actorId, scope, nextItem, capture())}>{t.moreItems}</button>}</section>
        </>}
        <SignalCenter key={actorId} actorId={actorId} scopeKey={scopeKey} capture={capture} selection={selection ? { childId, workspaceId: academyId, session: selection } : null} onPending={setBlocked} onResolved={value => { const current = capture(); setOutcome(value); clearFacts(); if (scope) loadFacts(actorId, scope, current); }} />
      </>}
      <p className="text-xs text-[#5C6B73]">{t.reportNotice}</p>
    </div>
    <nav className="fixed inset-x-0 bottom-0 z-10 mx-auto flex min-h-16 max-w-lg items-center justify-around border-t border-[#D5E3DE] bg-white px-3 pb-[env(safe-area-inset-bottom)]" aria-label={t.title}><Link href="/parent" className={`${buttonClass("selected")} inline-flex items-center`} aria-current="page">{t.home}</Link><Link href="/parent/children" prefetch={false} className={`${button} inline-flex items-center`}>{t.profiles}</Link></nav>
  </div></main>;
}
