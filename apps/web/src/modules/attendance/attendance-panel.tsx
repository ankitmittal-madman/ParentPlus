"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { attendanceRequestStatus, listSessionSignals, loadAttendanceSheet, saveAttendance } from "@/lib/attendance/actions";
import { canonicalAttendancePayload, type AttendanceSheet, type AttendanceStatus, type Signal, type SignalCursor } from "./contracts";
import { clearPending, readPending, writePending, readVolatilePending, retainVolatilePending, type PendingOperation } from "./pending";
import { useSessionBoundary } from "./session-boundary";
import { button, buttonClass, useAttendanceCopy } from "./copy";
export type AttendanceResolution = "saved" | "conflict" | "rejected";
type Props = {
  actorId: string;
  workspaceId: string;
  sessionId: string;
  onSaved: () => void;
  onResolved?: (outcome: AttendanceResolution) => void;
};
export function AttendancePanel({ actorId, workspaceId, sessionId, onSaved, onResolved }: Props) {
  const { t, lang } = useAttendanceCopy();
  const context = `${actorId}:${workspaceId}:${sessionId}`;
  const [view, setView] = useState<{
    context: string;
    sheet: AttendanceSheet;
  } | null>(null);
  const [marks, setMarks] = useState<Record<string, AttendanceStatus | null>>({});
  const [signals, setSignals] = useState<Signal[]>([]);
  const [nextSignals, setNextSignals] = useState<SignalCursor | null>(null);
  const [refreshed, setRefreshed] = useState<string | null>(null);
  const [signalsFailed, setSignalsFailed] = useState(false);
  const [review, setReview] = useState(false);
  const [pending, setPending] = useState<PendingOperation | null>(null);
  const [corrupt, setCorrupt] = useState(false);
  const [volatile, setVolatile] = useState(false);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);
  const [notice, setNotice] = useState<"saved" | "conflict" | "rejected" | "unknown" | null>(null);
  const locked = useRef(false);
  const signalSequence = useRef(0);
  const callbacks = useRef({ onSaved, onResolved });
  useEffect(() => {
    callbacks.current = { onSaved, onResolved };
  });
  const clearPrivate = useCallback(() => {
    setView(null);
    setMarks({});
    setSignals([]);
    setNextSignals(null);
    setRefreshed(null);
    setReview(false);
    setNotice(null);
    setBusy(false);
    locked.current = false;
    signalSequence.current++;
  }, []);
  const { actorId: verifiedActor, ready, capture, invalidateView } = useSessionBoundary(clearPrivate);
  const valid = verifiedActor === actorId;
  const sheet = valid && view?.context === context ? view.sheet : null;
  const loadSheet = useCallback(async (current: () => boolean) => {
    setLoading(true);
    setFailed(false);
    try {
      const result = await loadAttendanceSheet(actorId, { workspaceId, sessionId });
      if (!current())
        return;
      if (result.ok) {
        setView({ context, sheet: result.data });
        setMarks(Object.fromEntries(result.data.rows.map(r => [r.enrollmentId, r.status])));
      }
      else {
        setView(null);
        setMarks({});
        setFailed(true);
      }
    }
    catch {
      if (current()) {
        setView(null);
        setMarks({});
        setFailed(true);
      }
    }
    finally {
      if (current())
        setLoading(false);
    }
  }, [actorId, workspaceId, sessionId, context]);
  useEffect(() => {
    invalidateView();
    if (!valid)
      return;
    const current = capture();
    queueMicrotask(() => {
      if (!current())
        return;
      clearPrivate();
      const restored = readPending(actorId, "attendance");
      const memory = readVolatilePending(actorId, "attendance");
      setCorrupt(restored.kind === "corrupt");
      setVolatile(restored.kind === "unavailable" || !!memory);
      setPending(restored.kind === "pending" ? restored.value : memory);
      if (restored.kind === "pending" || memory)
        setNotice("unknown");
      void loadSheet(current);
    });
    return invalidateView;
  }, [actorId, workspaceId, sessionId, valid, capture, invalidateView, clearPrivate, loadSheet]);
  const loadSignals = useCallback(async (after: SignalCursor | null) => {
    if (!valid || document.visibilityState !== "visible")
      return;
    const current = capture();
    const sequence = ++signalSequence.current;
    try {
      const result = await listSessionSignals(actorId, { workspaceId, sessionId, after });
      if (!current() || sequence !== signalSequence.current)
        return;
      if (result.ok) {
        setSignals(old => after ? [...old, ...result.data.signals] : result.data.signals);
        setNextSignals(result.data.next);
        setRefreshed(result.data.serverNow);
        setSignalsFailed(false);
      }
      else {
        setSignalsFailed(true);
        if (result.kind === "forbidden") {
          setView(null);
          setMarks({});
          setSignals([]);
          setNextSignals(null);
          setRefreshed(null);
        }
      }
    }
    catch {
      if (current() && sequence === signalSequence.current)
        setSignalsFailed(true);
    }
  }, [valid, capture, actorId, workspaceId, sessionId]);
  useEffect(() => {
    if (!valid)
      return;
    let alive = true;
    queueMicrotask(() => {
      if (alive)
        void loadSignals(null);
    });
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible")
        void loadSignals(null);
    }, 15000);
    return () => {
      alive = false;
      window.clearInterval(timer);
    };
  }, [valid, loadSignals]);
  const perform = async (op: PendingOperation, check: boolean) => {
    if (locked.current || !valid || op.actorId !== actorId || op.payload.operation !== "save_attendance")
      return;
    locked.current = true;
    setBusy(true);
    setNotice(null);
    const current = capture();
    try {
      const input = { requestId: op.requestId, payload: op.payload };
      const result = check ? await attendanceRequestStatus(actorId, input) : await saveAttendance(actorId, input);
      if (!current())
        return;
      if (result.ok && (!("state" in result.data) || result.data.state === "known")) {
        clearPending(op);
        setPending(null);
        setVolatile(false);
        await loadSheet(current);
        if (!current())
          return;
        setNotice("saved");
        callbacks.current.onResolved?.("saved");
        callbacks.current.onSaved();
      }
      else if (!result.ok && result.kind !== "unknown") {
        clearPending(op);
        setPending(null);
        setVolatile(false);
        const outcome = result.kind === "conflict" ? "conflict" : "rejected";
        setNotice(outcome);
        callbacks.current.onResolved?.(outcome);
        if (current())
          await loadSheet(current);
      }
      else
        setNotice("unknown");
    }
    catch {
      if (current())
        setNotice("unknown");
    }
    finally {
      if (current()) {
        locked.current = false;
        setBusy(false);
      }
    }
  };
  const save = () => {
    if (!sheet || locked.current || pending || corrupt)
      return;
    const payload = canonicalAttendancePayload({ operation: "save_attendance", workspace_id: workspaceId, session_id: sessionId, expected_session_version: sheet.session.version, expected_sheet_version: sheet.sheetVersion, roster_token: sheet.rosterToken, records: sheet.rows.map(r => ({ enrollment_id: r.enrollmentId, child_id: r.childId, status: marks[r.enrollmentId] ?? null })) });
    if (!payload)
      return;
    const value: PendingOperation = { format: 1, actorId, requestId: crypto.randomUUID(), payload };
    const storage = writePending(value);
    if (storage === "blocked") {
      const restored = readPending(actorId, "attendance");
      setCorrupt(restored.kind === "corrupt");
      if (restored.kind === "pending")
        setPending(restored.value);
      return;
    }
    if (storage === "unavailable") {
      if (!retainVolatilePending(value)) {
        setPending(readVolatilePending(actorId, "attendance"));
        return;
      }
      setVolatile(true);
    }
    setPending(value);
    void perform(value, false);
  };
  const readOnly = !sheet || sheet.session.status === "cancelled" || sheet.rosterTooLarge || sheet.rows.length === 0;
  const disabled = readOnly || busy || !!pending || corrupt;
  const time = (value: string) => new Intl.DateTimeFormat(lang, { timeZone: sheet?.timeZone ?? "UTC", hour: "numeric", minute: "2-digit" }).format(new Date(value));
  const label = (status: AttendanceStatus) => t[status];
  const markButton = (status: AttendanceStatus, childName: string, enrollmentId: string) => <button type="button" key={status} data-qa-action={`Mark ${status}`} className={buttonClass(marks[enrollmentId] === status ? "selected" : "default")} aria-label={`${label(status)} ${t.forChild} ${childName}`} aria-pressed={marks[enrollmentId] === status} disabled={disabled} onClick={() => {
    setMarks(old => ({ ...old, [enrollmentId]: status }));
    setNotice(null);
  }}>{status === "present" ? "P" : status === "late" ? "L" : status === "absent" ? "A" : label(status)}
  </button>;
  return <section aria-label={t.attendance} className="mt-5 rounded-3xl border border-[#DCE6DF] bg-[#FFFEFA] p-4 shadow-sm">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <h2 className="text-xl font-bold">{t.attendance}
      </h2>
      <button className={button} disabled={!valid || busy || loading} onClick={() => {
        invalidateView();
        void loadSheet(capture());
        void loadSignals(null);
      }}>{t.refreshSheet}
      </button>
    </div>
    {!valid && <p role="status" className="mt-3 text-sm">{ready ? t.sessionNeeded : t.monitorUnavailable}
    </p>}
    {valid && loading && <p role="status">{t.loading}
    </p>}
    {valid && failed && <p role="alert" className="mt-3 text-sm">{t.failed}
    </p>}
    {valid && corrupt && <p role="alert" className="mt-3 rounded-xl bg-[#FFF0D5] p-3 text-sm">{t.corrupt}
    </p>}
    {valid && volatile && <p role="status" className="mt-3 rounded-xl bg-[#FFF0D5] p-3 text-sm">{t.keepTabOpen}
    </p>}
    {valid && pending && <div className="mt-3 rounded-xl bg-[#FFF0D5] p-3">
      <p className="text-sm">{t.pendingOther}
      </p>
      <div className="mt-2 flex flex-wrap gap-2">
        <button className={button} disabled={busy} onClick={() => void perform(pending, true)}>{t.check}
        </button>
        <button className={button} disabled={busy} onClick={() => void perform(pending, false)}>{t.retry}
        </button>
      </div>
    </div>}
    <p role="status" aria-live="polite" className="mt-3 text-sm font-semibold">{busy ? t.working : valid && notice ? t[notice] : ""}
    </p>
    {sheet && <>
      <p className="mb-3 text-sm text-[#5C6B73]">{sheet.session.batchName} · {sheet.session.courseName} · {time(sheet.session.startsAt)}
      </p>
      {sheet.session.status === "cancelled" ? <p className="rounded-xl bg-[#F8E8E0] p-3 text-sm">{t.cancelledSheet}
      </p> : sheet.rosterTooLarge ? <p className="rounded-xl bg-[#FFF0D5] p-3 text-sm">{t.oversized}
      </p> : sheet.rows.length === 0 ? <p className="py-4 text-sm">{t.emptyRoster}
      </p> : <p className="mb-3 text-xs text-[#5C6B73]">{t.complete}
      </p>}
      <button className={`${button} mb-3`} disabled={disabled} onClick={() => setMarks(old => Object.fromEntries(sheet.rows.map(r => [r.enrollmentId, old[r.enrollmentId] ?? "present"])))}>{t.markAll}
      </button>
      <ul className="divide-y divide-[#E7ECE6]">{sheet.rows.map(r => <li key={r.enrollmentId} className="py-3">
        <div className="mb-2 flex items-center justify-between gap-2">
          <span className="font-semibold">{r.childName}
          </span>
          <span className="text-xs text-[#5C6B73]">{marks[r.enrollmentId] ? label(marks[r.enrollmentId]!) : t.unmarked}
          </span>
        </div>
        <div className="flex flex-wrap gap-2">{(["present", "late", "absent"] as const).map(s => markButton(s, r.childName, r.enrollmentId))}<details>
          <summary className={`${button} flex cursor-pointer items-center`} aria-label={`${t.moreMarks} ${r.childName}`} data-qa-action="More attendance marks">{t.more}
          </summary>
          <div className="mt-2 flex flex-wrap gap-2">{(["excused", "make_up"] as const).map(s => markButton(s, r.childName, r.enrollmentId))}
          </div>
        </details>
        </div>
      </li>)}
      </ul>
      <button className={`${buttonClass("primary")} mt-4 w-full`} disabled={disabled || !sheet.rows.every(r => !!marks[r.enrollmentId])} onClick={save}>{t.save}
      </button>
      <div className="mt-5 border-t border-[#E7ECE6] pt-4">
        <button className={button} aria-expanded={review} onClick={() => setReview(v => !v)}>{t.reviewSignals}
        </button>{refreshed && <p className="mt-2 text-xs text-[#5C6B73]">{t.lastRefresh}: <time dateTime={refreshed}>{time(refreshed)}
        </time>
        </p>}
        {signalsFailed && <p role="status" className="text-sm">{t.signalsFailed}
        </p>}
        {review && <div className="mt-3 rounded-2xl bg-[#EAF3ED] p-3">
          <p className="text-xs">{t.reportNotice}
          </p>{signals.length === 0 && <p className="py-3 text-sm">{t.noSignals}
          </p>}<ul>{signals.map(s => <li key={`${s.childId}:${s.actorId}`} className="py-2 text-sm">{sheet.rows.find(r => r.childId === s.childId)?.childName ?? ""} · {t.parentReport}: {t[s.type]}{s.reason ? ` · ${t[s.reason]}` : ""} · <time dateTime={s.createdAt}>{time(s.createdAt)}
          </time>
          </li>)}
          </ul>{nextSignals && <button className={button} onClick={() => void loadSignals(nextSignals)}>{t.moreSignals}
          </button>}<button className={`${button} mt-3 w-full`} disabled={disabled} onClick={() => setMarks(old => Object.fromEntries(sheet.rows.map(r => [r.enrollmentId, old[r.enrollmentId] ?? (signals.some(s => s.childId === r.childId && s.type === "missing_today") ? "absent" : null)])))}>{t.applySuggestions}
          </button>
        </div>}
      </div>
    </>}
  </section>;
}
