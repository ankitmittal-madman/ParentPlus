"use client";
import Link from "next/link";
import { useCallback, useRef, useState } from "react";
import {
  familySession,
  familyAcademies,
  familyRoster,
  issueFamilyInvite,
} from "@/lib/families/actions";
import { type Child, type RosterRow } from "./contracts";
import { useCopy, useBoundary, button, field, card } from "./shared";
export default function StudentsPanel() {
  const { t, selector } = useCopy();
  const [actor, setActor] = useState(""),
    [academies, setAcademies] = useState<Child[] | null>(null),
    [academy, setAcademy] = useState(""),
    [roster, setRoster] = useState<RosterRow[] | null>(null),
    [link, setLink] = useState(""),
    [expiry, setExpiry] = useState(""),
    [notice, setNotice] = useState<keyof typeof t | null>(null),
    [cursor, setCursor] = useState<string | null>(null);
  const intent = useRef<{
    actor: string;
    workspace: string;
    request: string;
    token: string;
  } | null>(null);
  const reset = useCallback(() => {
    setActor("");
    setAcademies(null);
    setAcademy("");
    setRoster(null);
    setLink("");
    setExpiry("");
    setNotice(null);
    setCursor(null);
    intent.current = null;
  }, []);
  const b = useBoundary(reset);
  async function load() {
    await b.run(async (current) => {
      reset();
      const s = await familySession();
      if (!current()) return;
      if (!s.ok) {
        setNotice("failed");
        return;
      }
      const a = await familyAcademies(s.data);
      if (!current()) return;
      if (!a.ok) {
        setNotice("failed");
        return;
      }
      setActor(s.data);
      setAcademies(a.data);
    });
  }
  async function students(after: string | null) {
    await b.run(async (current) => {
      setNotice(null);
      const r = await familyRoster(actor, academy, after);
      if (!current()) return;
      if (!r.ok) {
        setRoster(null);
        setNotice("failed");
        return;
      }
      setRoster(r.data);
      setCursor(after);
    });
  }
  async function issue() {
    await b.run(async (current) => {
      setNotice(null);
      if (!intent.current) {
        const bytes = crypto.getRandomValues(new Uint8Array(32));
        intent.current = {
          actor,
          workspace: academy,
          request: crypto.randomUUID(),
          token: Array.from(bytes, (v) => v.toString(16).padStart(2, "0")).join(
            "",
          ),
        };
      }
      const i = intent.current;
      if (i.actor !== actor || i.workspace !== academy) {
        setNotice("failed");
        return;
      }
      const r = await issueFamilyInvite(
        i.actor,
        i.workspace,
        i.request,
        i.token,
      ).catch(() => ({ ok: false as const }));
      if (!current()) return;
      if (!r.ok) {
        setNotice("unknownInvite");
        return;
      }
      setLink(`${location.origin}/join#${i.token}`);
      setExpiry(r.data.expiresAt);
    });
  }
  return (
    <section aria-labelledby="students-title">
      <div className="mt-6 flex items-start justify-between gap-4">
        <div>
          <h1 id="students-title" className="text-3xl font-extrabold">
            {t.students}
          </h1>
          <p className="mt-3 text-sm text-[#5C6B73]">{t.studentsIntro}</p>
        </div>
        <div className="w-32 shrink-0">{selector}</div>
      </div>
      <div className={card}>
        {!b.ready && <p role="status">{t.monitorUnavailable}</p>}
        <button className={button} disabled={!b.ready || b.busy} onClick={load}>
          {t.loadAcademies}
        </button>
        {academies?.length === 0 && (
          <>
            <p className="mt-3">{t.noAcademies}</p>
            <Link href="/coach-onboarding" className="underline">
              {t.createAcademy}
            </Link>
          </>
        )}
        {academies && academies.length > 0 && (
          <>
            <label className="mt-4 block">
              {t.academy}
              <select
                aria-label={t.academy}
                className={field}
                value={academy}
                disabled={b.busy}
                onChange={(e) => {
                  setAcademy(e.target.value);
                  setRoster(null);
                  setLink("");
                  setExpiry("");
                  setNotice(null);
                  setCursor(null);
                  intent.current = null;
                }}
              >
                <option value="">{t.choose}</option>
                {academies.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </select>
            </label>
            <div className="flex flex-wrap gap-2">
              <button
                className={button}
                disabled={!academy || b.busy}
                onClick={() => students(null)}
              >
                {t.loadStudents}
              </button>
              <button
                className={button}
                disabled={!academy || b.busy || !!link}
                onClick={issue}
              >
                {notice === "unknownInvite" ? t.retryInvite : t.addStudent}
              </button>
            </div>
          </>
        )}
        {link && (
          <div className="mt-4">
            <label>
              {t.inviteLink}
              <input
                data-private="invite-link"
                readOnly
                className={field}
                value={link}
              />
            </label>
            <p className="mt-2 text-sm">{t.inviteHelp}</p>
            <p className="mt-2 text-sm">
              {t.expires}: {new Date(expiry).toLocaleDateString()}
            </p>
            <button
              className={button}
              disabled={b.busy}
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(link);
                  setNotice("copied");
                } catch {
                  setNotice("copyFailed");
                }
              }}
            >
              {t.copy}
            </button>
            <button
              className="ml-3 underline"
              disabled={b.busy}
              onClick={() => {
                setLink("");
                setExpiry("");
                setNotice(null);
                intent.current = null;
              }}
            >
              {t.cancel}
            </button>
          </div>
        )}
      </div>
      {roster && (
        <div className={card}>
          {roster.length === 0 && <p>{t.emptyRoster}</p>}
          <ul>
            {roster.map((r) => (
              <li
                className="flex items-center justify-between border-b border-[#EDF0EB] py-4"
                key={r.id}
              >
                <span className="font-semibold">{r.name}</span>
                <span className="rounded-full bg-[#EDF4EF] px-3 py-1 text-xs">
                  {t[r.status]}
                </span>
              </li>
            ))}
          </ul>
          <div className="flex gap-2">
            {cursor && (
              <button
                className={button}
                disabled={b.busy}
                onClick={() => students(null)}
              >
                {t.firstPage}
              </button>
            )}
            {roster.length === 50 && (
              <button
                className={button}
                disabled={b.busy}
                onClick={() => students(roster.at(-1)!.id)}
              >
                {t.nextPage}
              </button>
            )}
          </div>
        </div>
      )}
      {b.busy && (
        <p role="status" className="mt-4">
          {t.loading}
        </p>
      )}
      {(b.failed || b.changed || notice) && (
        <p role="alert" className="mt-4 text-sm">
          {notice ? t[notice] : b.failed ? t.failed : t.sessionChanged}
        </p>
      )}
    </section>
  );
}
