"use client";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { listTodayAcademies, listTodaySessions } from "@/lib/attendance/actions";
import { CoachHeader } from "@/ui/components/coach-header";
import { AttendancePanel, type AttendanceResolution } from "../attendance/attendance-panel";
import { AttendanceCopyProvider, AttendanceLanguageSelect, button, buttonClass, field, useAttendanceCopy } from "../attendance/copy";
import { readPending, readVolatilePending, type PendingOperation } from "../attendance/pending";
import { useSessionBoundary } from "../attendance/session-boundary";
import { date as isDate } from "../attendance/validation";
import { dateStrip, localDate, type Academy, type Session, type SessionCursor } from "./contracts";
export function TodayPanel() {
  return <AttendanceCopyProvider>
    <Today />
  </AttendanceCopyProvider>;
}
function Today() {
  const { t, lang } = useAttendanceCopy();
  const [academies, setAcademies] = useState<Academy[]>([]);
  const [nextAcademy, setNextAcademy] = useState<string | null>(null);
  const [academyId, setAcademyId] = useState("");
  const [date, setDate] = useState("");
  const [sessions, setSessions] = useState<Session[]>([]);
  const [nextSession, setNextSession] = useState<SessionCursor | null>(null);
  const [selected, setSelected] = useState<{
    workspaceId: string;
    sessionId: string;
  } | null>(null);
  const [recovery, setRecovery] = useState<PendingOperation | null>(null);
  const [corrupt, setCorrupt] = useState(false);
  const [recoveryOutcome, setRecoveryOutcome] = useState<AttendanceResolution | null>(null);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [pageBusy, setPageBusy] = useState(false);
  const pageSequence = useRef(0);
  const academySequence = useRef(0);
  const clearPrivate = useCallback(() => {
    setAcademies([]);
    setAcademyId("");
    setDate("");
    setSessions([]);
    setNextAcademy(null);
    setNextSession(null);
    setSelected(null);
    setRecovery(null);
    setCorrupt(false);
    setRecoveryOutcome(null);
    setFailed(false);
    setLoaded(false);
    setPageBusy(false);
    setLoading(false);
    pageSequence.current++;
    academySequence.current++;
  }, []);
  const { actorId, ready, capture, invalidateView } = useSessionBoundary(clearPrivate);
  const academy = academies.find(a => a.workspaceId === academyId);
  const fetchSessions = useCallback(async (actor: string, workspaceId: string, selectedDate: string, after: SessionCursor | null, current: () => boolean) => {
    setPageBusy(true);
    setFailed(false);
    const sequence = ++pageSequence.current;
    try {
      const result = await listTodaySessions(actor, { workspaceId, date: selectedDate, after });
      if (!current() || sequence !== pageSequence.current)
        return;
      if (result.ok) {
        setSessions(old => after ? [...old, ...result.data.sessions] : result.data.sessions);
        setNextSession(result.data.next);
        setLoaded(true);
      }
      else {
        setSessions([]);
        setNextSession(null);
        setFailed(true);
        setLoaded(false);
      }
    }
    catch {
      if (current() && sequence === pageSequence.current) {
        setSessions([]);
        setFailed(true);
        setLoaded(false);
      }
    }
    finally {
      if (current() && sequence === pageSequence.current)
        setPageBusy(false);
    }
  }, []);
  const initial = useCallback(async (actor: string, current: () => boolean, preferredAcademy?: string, preferredDate?: string) => {
    const request = ++academySequence.current;
    setLoading(true);
    setFailed(false);
    try {
      const result = await listTodayAcademies(actor, { after: null });
      if (!current() || request !== academySequence.current)
        return;
      if (!result.ok) {
        setFailed(true);
        setAcademies([]);
        setAcademyId("");
        return;
      }
      // Academy loading ends here; the dated session read owns pageBusy.
      setLoading(false);
      setAcademies(result.data.academies);
      setNextAcademy(result.data.nextAfter);
      const chosen = result.data.academies.find(a => a.workspaceId === preferredAcademy) ?? result.data.academies[0];
      setAcademyId(chosen?.workspaceId ?? "");
      if (chosen?.timeZone) {
        const day = chosen.workspaceId === preferredAcademy && preferredDate && isDate(preferredDate) ? preferredDate : localDate(chosen.timeZone);
        setDate(day);
        await fetchSessions(actor, chosen.workspaceId, day, null, current);
      }
      else {
        setDate("");
        setSessions([]);
        setLoaded(true);
      }
    }
    catch {
      if (current() && request === academySequence.current) {
        setFailed(true);
        setAcademies([]);
        setAcademyId("");
      }
    }
    finally {
      if (current() && request === academySequence.current)
        setLoading(false);
    }
  }, [fetchSessions]);
  useEffect(() => {
    if (!actorId)
      return;
    const current = capture();
    queueMicrotask(() => {
      if (!current())
        return;
      const saved = readPending(actorId, "attendance");
      setCorrupt(saved.kind === "corrupt");
      setRecovery(saved.kind === "pending" ? saved.value : readVolatilePending(actorId, "attendance"));
      void initial(actorId, current);
    });
  }, [actorId, capture, initial]);
  const cancelScopeReads = () => {
    invalidateView();
    academySequence.current++;
    pageSequence.current++;
    setLoading(false);
    setPageBusy(false);
  };
  const changeDate = (day: string) => {
    cancelScopeReads();
    setDate(day);
    setSessions([]);
    setNextSession(null);
    setSelected(null);
    setLoaded(false);
    if (actorId && academy && isDate(day))
      void fetchSessions(actorId, academy.workspaceId, day, null, capture());
  };
  const chooseAcademy = (workspaceId: string) => {
    cancelScopeReads();
    setAcademyId(workspaceId);
    setSessions([]);
    setSelected(null);
    setNextSession(null);
    setLoaded(false);
    setPageBusy(false);
    setFailed(false);
    const chosen = academies.find(a => a.workspaceId === workspaceId);
    const day = chosen?.timeZone ? localDate(chosen.timeZone) : "";
    setDate(day);
    if (actorId && chosen?.timeZone)
      void fetchSessions(actorId, workspaceId, day, null, capture());
  };
  const moreAcademies = async () => {
    if (!actorId || !nextAcademy || loading)
      return;
    const current = capture();
    const request = ++academySequence.current;
    setLoading(true);
    try {
      const result = await listTodayAcademies(actorId, { after: nextAcademy });
      if (!current() || request !== academySequence.current)
        return;
      if (result.ok) {
        setAcademies(old => [...old, ...result.data.academies]);
        setNextAcademy(result.data.nextAfter);
      }
      else
        setFailed(true);
    }
    catch {
      if (current() && request === academySequence.current)
        setFailed(true);
    }
    finally {
      if (current() && request === academySequence.current)
        setLoading(false);
    }
  };
  const panel = recovery ? { workspaceId: recovery.payload.workspace_id, sessionId: recovery.payload.session_id } : selected;
  const sessionTime = (value: string) => new Intl.DateTimeFormat(lang, { timeZone: academy?.timeZone ?? "UTC", hour: "numeric", minute: "2-digit" }).format(new Date(value));
  return <main className="min-h-screen bg-[#F3F5F1] text-[#22303A]">
    <div className="mx-auto min-h-screen max-w-md pb-32 shadow-sm">
      <CoachHeader academyName={academy?.name} />
      <section className="px-5 pt-6">
        <h1 className="text-3xl font-extrabold tracking-tight">{t.today}
        </h1>
        <p className="mt-1 text-sm text-[#5C6B73]">{t.intro}
        </p>
        <AttendanceLanguageSelect />
        {!actorId ? <div className="mt-5 rounded-2xl bg-white p-4">
          <p role="status" className="text-sm">{ready ? t.sessionNeeded : t.monitorUnavailable}
          </p>
          <Link href="/login" className={`${button} mt-3 inline-flex items-center`}>{t.signIn}
          </Link>
        </div> : <>
          <button className={`${button} mt-4`} disabled={loading} onClick={() => {
            cancelScopeReads();
            setSessions([]);
            setSelected(null);
            setLoaded(false);
            void initial(actorId, capture(), academyId, date);
          }}>{t.refresh}
          </button>
          {(loading || pageBusy) && <p role="status" className="mt-3 text-sm">{t.loading}
          </p>}
          {failed && <p role="alert" className="mt-3 rounded-xl bg-[#FFF0D5] p-3 text-sm">{t.failed}
          </p>}
          {recoveryOutcome && <p role="status" aria-live="polite" className="mt-3 text-sm font-semibold">{t[recoveryOutcome]}
          </p>}
          {corrupt && <p role="alert" className="mt-3 rounded-xl bg-[#FFF0D5] p-3 text-sm">{t.corrupt}
          </p>}
          {!loading && !failed && academies.length === 0 && <p className="mt-5 rounded-2xl bg-white p-4 text-sm">{t.noAcademies}
          </p>}
          {academies.length > 0 && <div className="mt-4 rounded-2xl bg-white p-4">
            <label className="block text-sm font-semibold">{t.academy}<select aria-label={t.academy} className={`${field} mt-1`} value={academyId} onChange={e => chooseAcademy(e.target.value)}>{academies.map(a => <option key={a.workspaceId} value={a.workspaceId}>{a.name}
            </option>)}
            </select>
            </label>{nextAcademy && <button className={`${button} mt-3`} disabled={loading} onClick={() => void moreAcademies()}>{t.moreAcademies}
            </button>}
          </div>}
          {academy && !academy.timeZone && <div className="mt-4 rounded-2xl bg-[#FFF0D5] p-4">
            <p className="text-sm">{t.zoneUnavailable}
            </p>
            <Link href="/schedule" className={`${button} mt-3 inline-flex items-center`}>{t.setup}
            </Link>
          </div>}
          {academy?.timeZone && <>
            <label className="mt-5 block text-sm font-semibold">{t.date}<input className={`${field} mt-1`} aria-label={t.date} type="date" min="2000-01-01" max="2100-12-31" value={date} onChange={e => changeDate(e.target.value)} />
            </label>
            {isDate(date) && <div className="mt-3 flex gap-1 overflow-x-auto pb-2">{dateStrip(date).map(day => <button key={day} className={`${buttonClass(day === date ? "selected" : "default")} flex min-w-14 flex-col items-center px-2`} aria-label={`${t.dateSelect} ${day}`} aria-pressed={day === date} data-qa-action="Select session date" onClick={() => changeDate(day)}>
              <span className="text-[10px]">{new Intl.DateTimeFormat(lang, { weekday: "short", timeZone: "UTC" }).format(new Date(`${day}T12:00:00Z`))}
              </span>
              <span>{day.slice(-2)}
              </span>
            </button>)}
            </div>}
            {loaded && !pageBusy && !failed && sessions.length === 0 && <p className="mt-4 rounded-2xl bg-white p-4 text-sm">{t.noSessions}
            </p>}
            <div className="mt-3 space-y-3">{sessions.map((s, i) => <article key={s.id} className={`rounded-2xl border-l-4 ${i % 3 === 0 ? "border-[#1F6F6B] bg-[#E1F0ED]" : i % 3 === 1 ? "border-[#D5A04B] bg-[#FFF1D9]" : "border-[#9D89B1] bg-[#EFE9F6]"} p-4`}>
              <p className="text-xs text-[#5C6B73]">{sessionTime(s.startsAt)} – {sessionTime(s.endsAt)} · {s.courseName}
              </p>
              <h2 className="mt-1 text-lg font-bold">{s.batchName}
              </h2>
              <p className="mt-1 text-sm">{s.rosterTooLarge ? t.rosterLimit : `${s.rosterSize} ${t.enrolled}`}
              </p>
              <p className="mt-2 text-xs font-semibold">{s.status === "cancelled" ? t.cancelled : s.attendanceCurrent ? t.current : t.needed}
              </p>
              <button className={`${button} mt-3`} aria-label={`${t.open} ${s.batchName}`} data-qa-action="Open attendance" onClick={() => setSelected({ workspaceId: academyId, sessionId: s.id })}>{t.attendance}
              </button>
            </article>)}
            </div>
            {nextSession && <button className={`${button} mt-4 w-full`} disabled={pageBusy} onClick={() => void fetchSessions(actorId, academyId, date, nextSession, capture())}>{t.moreSessions}
            </button>}
          </>}
          {panel && <AttendancePanel key={`${actorId}:${panel.workspaceId}:${panel.sessionId}`} actorId={actorId} workspaceId={panel.workspaceId} sessionId={panel.sessionId} onResolved={outcome => {
            if (recovery) {
              setRecoveryOutcome(outcome);
              setRecovery(null);
            }
          }} onSaved={() => {
            if (academy?.timeZone && isDate(date))
              void fetchSessions(actorId, academyId, date, null, capture());
          }} />}
        </>}
      </section>
    </div>
  </main>;
}
