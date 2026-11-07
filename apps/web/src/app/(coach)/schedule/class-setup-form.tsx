"use client";

import { useRef, useState } from "react";
import type { FormEvent } from "react";
import { expandSchedule, ScheduleTimeError } from "@/lib/scheduling/occurrences";
import { runClassSetupOperation } from "@/lib/scheduling/class-setup-operations";
import type { recoverCurrentClassSetup } from "@/lib/scheduling/recover-current-class-setup";

type Recovery = Extract<Awaited<ReturnType<typeof recoverCurrentClassSetup>>, { ok: true }>;
type WeeklySchedule = { timeZone: string; startDate: string; startTime: string; endDate: string; durationMinutes: number };
type Props = {
  actorId: string;
  workspaceId: string;
  timeZone: string | null;
  recovery: Recovery;
  refresh: () => Promise<void>;
};

export default function ClassSetupForm({ actorId, workspaceId, timeZone, recovery, refresh }: Props) {
  const [courseName, setCourseName] = useState(recovery.state === "pending" ? recovery.courseName : "");
  const [batchName, setBatchName] = useState(recovery.state === "pending" ? recovery.batchName : "");
  const [scheduleTimeZone, setScheduleTimeZone] = useState(timeZone ?? "");
  const [startDate, setStartDate] = useState("");
  const [startTime, setStartTime] = useState("");
  const [endDate, setEndDate] = useState("");
  const [durationMinutes, setDurationMinutes] = useState(60);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const attempt = useRef<{ generation: number; requestId: string; courseName: string; batchName: string } | null>(null);

  const canStart = recovery.state === "unknown"
    || (recovery.state === "completed" && recovery.acknowledged);
  const needsDetails = canStart || recovery.state === "pending";
  let occurrenceCount: number | null = null;
  if (startDate && startTime && endDate && scheduleTimeZone) {
    try {
      occurrenceCount = expandSchedule({ startDate, startTime, timeZone: scheduleTimeZone, durationMinutes, recurrence: { kind: "weekly", untilDate: endDate } }).length;
    } catch { /* The form presents detailed validation after submission. */ }
  }

  async function saveSchedule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || !needsDetails) return;
    setBusy(true);
    setNotice("");
    const course = recovery.state === "pending" ? recovery.courseName : courseName.trim();
    const batch = recovery.state === "pending" ? recovery.batchName : batchName.trim();
    let schedule: WeeklySchedule;
    let sessionCount: number;
    try {
      schedule = { timeZone: scheduleTimeZone, startDate, startTime, endDate, durationMinutes };
      sessionCount = expandSchedule({ ...schedule, recurrence: { kind: "weekly", untilDate: endDate } }).length;
      if (!course || !batch) throw new RangeError("Enter a course and batch name.");
    } catch (error) {
      const message = error instanceof ScheduleTimeError
        ? `The ${error.kind} local time on ${error.localDate} needs a different time in ${error.timeZone}.`
        : error instanceof Error ? error.message : "Check the schedule details.";
      setNotice(message);
      setBusy(false);
      return;
    }

    try {
      let intentId: string;
      if (recovery.state === "pending") {
        intentId = recovery.intentId;
      } else {
        const current = await runClassSetupOperation({ operation: "generation", workspaceId, expectedActorId: actorId });
        if (!current.ok || current.operation !== "generation") {
          setNotice("Unable to check this academy. Review the current setup before trying again.");
          await refresh();
          return;
        }
        if (!current.available) {
          setNotice("A class setup is already being resolved in this academy. Refresh the status before starting another.");
          await refresh();
          return;
        }

        let request = attempt.current;
        if (!request || request.generation !== current.generation) {
          request = { generation: current.generation, requestId: crypto.randomUUID(), courseName: course, batchName: batch };
          attempt.current = request;
        } else if (request.courseName !== course || request.batchName !== batch) {
          setNotice("The previous request is still being checked. Refresh its status before changing these details.");
          await refresh();
          return;
        }

        const reserved = await runClassSetupOperation({
          operation: "reserve", workspaceId, expectedActorId: actorId,
          generation: request.generation, requestId: request.requestId,
          courseName: request.courseName, batchName: request.batchName,
        });
        if (!reserved.ok || reserved.operation !== "reserve") {
          setNotice("We could not confirm the request. Check the setup status before trying again.");
          await refresh();
          return;
        }
        intentId = reserved.intentId;
      }

      const completed = await runClassSetupOperation({ operation: "complete", workspaceId, expectedActorId: actorId, intentId, schedule });
      if (!completed.ok || completed.operation !== "complete") {
        setNotice("We could not confirm the course and weekly sessions. Refresh the setup status before continuing.");
        await refresh();
        return;
      }
      if (completed.occurrenceCount !== sessionCount) {
        setNotice("The saved schedule count needs review. Refresh the setup status before continuing.");
        await refresh();
        return;
      }
      setNotice(`Course and batch saved with ${completed.occurrenceCount} weekly sessions. Review the schedule and confirm to finish.`);
      await refresh();
    } catch {
      setNotice("We could not confirm the course and weekly sessions. Refresh the setup status before continuing.");
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  async function acknowledgeSetup() {
    if (busy || recovery.state !== "completed" || recovery.acknowledged) return;
    setBusy(true);
    setNotice("");
    try {
      const result = await runClassSetupOperation({ operation: "acknowledge", workspaceId, expectedActorId: actorId, intentId: recovery.intentId });
      setNotice(result.ok && result.operation === "acknowledge"
        ? "Setup confirmed. You can create another course and batch when ready."
        : "We could not confirm your acknowledgement. Refresh the setup status before continuing.");
      await refresh();
    } catch {
      setNotice("We could not confirm your acknowledgement. Refresh the setup status before continuing.");
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mt-4 border-t pt-4">
      {recovery.state === "completed" && recovery.schedule && <div className="mt-3 rounded-lg bg-[#F4F8F7] p-3 text-sm" aria-label="Saved weekly schedule">
        <p className="font-semibold">Weekly schedule: {recovery.schedule.occurrenceCount} sessions</p>
        <p>{recovery.schedule.startTime} · {recovery.schedule.timeZone}</p>
        <p>{recovery.schedule.startDate} through {recovery.schedule.endDate} · {recovery.schedule.durationMinutes} minutes</p>
      </div>}
      {recovery.state === "completed" && !recovery.schedule && <p role="status" className="mt-3 text-sm">This earlier setup has no saved weekly schedule.</p>}
      {recovery.state === "completed" && !recovery.acknowledged && <button type="button" disabled={busy} onClick={() => void acknowledgeSetup()} className="mt-3 rounded-lg bg-[#1F6F6B] px-4 py-2 font-semibold text-white disabled:opacity-50">Confirm course, batch and schedule</button>}
      {needsDetails && <form onSubmit={(event) => void saveSchedule(event)} className="space-y-3">
        <h3 className="font-bold">{recovery.state === "pending" ? "Finish the saved course and batch" : "Create a course and weekly batch"}</h3>
        {recovery.state !== "pending" && <>
          <label htmlFor="setup-course" className="block text-sm font-semibold">Course name</label>
          <input id="setup-course" required maxLength={120} value={courseName} onChange={(event) => setCourseName(event.target.value)} disabled={busy} className="w-full rounded-lg border p-2" />
          <label htmlFor="setup-batch" className="block text-sm font-semibold">Batch name</label>
          <input id="setup-batch" required maxLength={120} value={batchName} onChange={(event) => setBatchName(event.target.value)} disabled={busy} className="w-full rounded-lg border p-2" />
        </>}
        {recovery.state === "pending" && <p className="text-sm">Course: {recovery.courseName} · Batch: {recovery.batchName}</p>}
        <label htmlFor="setup-time-zone" className="block text-sm font-semibold">Academy time zone</label>
        <input id="setup-time-zone" required list="setup-time-zones" placeholder="e.g., Asia/Kolkata" value={scheduleTimeZone} onChange={(event) => setScheduleTimeZone(event.target.value)} disabled={busy || timeZone !== null} className="w-full rounded-lg border p-2" />
        {timeZone === null && <datalist id="setup-time-zones">{["Asia/Kolkata", "Asia/Dubai", "UTC", "Europe/London", "America/New_York", "America/Los_Angeles", "Australia/Sydney"].map((zone) => <option key={zone} value={zone} />)}</datalist>}
        {timeZone === null && <p className="text-xs text-gray-600">Choose the academy’s time zone. It sets the local time for every weekly session.</p>}
        {timeZone !== null && <p className="text-xs text-gray-600">The academy time zone is already set and cannot be changed here.</p>}
        <label htmlFor="setup-start-date" className="block text-sm font-semibold">First session date</label>
        <input id="setup-start-date" type="date" required value={startDate} onChange={(event) => setStartDate(event.target.value)} disabled={busy} className="w-full rounded-lg border p-2" />
        <label htmlFor="setup-start-time" className="block text-sm font-semibold">Local start time</label>
        <input id="setup-start-time" type="time" required value={startTime} onChange={(event) => setStartTime(event.target.value)} disabled={busy} className="w-full rounded-lg border p-2" />
        <label htmlFor="setup-duration" className="block text-sm font-semibold">Session duration (minutes)</label>
        <input id="setup-duration" type="number" min={1} max={1440} required value={durationMinutes} onChange={(event) => setDurationMinutes(Number(event.target.value))} disabled={busy} className="w-full rounded-lg border p-2" />
        <label htmlFor="setup-end-date" className="block text-sm font-semibold">Last date for weekly sessions</label>
        <input id="setup-end-date" type="date" required value={endDate} onChange={(event) => setEndDate(event.target.value)} disabled={busy} className="w-full rounded-lg border p-2" />
        {occurrenceCount !== null && <p className="text-sm">This creates {occurrenceCount} weekly sessions, including the first date and any matching week on the end date.</p>}
        <button type="submit" disabled={busy || !scheduleTimeZone || !startDate || !startTime || !endDate || (recovery.state !== "pending" && (!courseName.trim() || !batchName.trim()))} className="rounded-lg bg-[#1F6F6B] px-4 py-2 font-semibold text-white disabled:opacity-50">
          {busy ? "Saving…" : recovery.state === "pending" ? "Finish course, batch and schedule" : "Create course, batch and weekly sessions"}
        </button>
      </form>}
      {notice && <p role="status" aria-live="polite" className="mt-3 text-sm">{notice}</p>}
    </div>
  );
}
