"use client";
import { useRef, useState } from "react";
import { familyAcademies, familySession } from "@/lib/families/actions";
import {
  listEnrollmentBatches,
  listEnrollmentCandidates,
  listBatchEnrollments,
  saveEnrollment,
  changeEnrollment,
} from "@/lib/enrollments/actions";
import type { Child } from "@/modules/families/contracts";
import type {
  Batch,
  Candidate,
  Enrollment,
  EnrollmentState,
  EnrollmentReason,
  SaveInput,
  ChangeInput,
} from "./contracts";
import {
  useEnrollmentCopy,
  useEnrollmentBoundary,
  button,
  field,
  card,
} from "./shared";

type Intent = {
  actor: string;
  workspace: string;
  batch: string;
  confirmed: boolean;
  rejected?: boolean;
} & (
  { kind: "save"; input: SaveInput } | { kind: "change"; input: ChangeInput }
);
export default function EnrollmentPanel() {
  const { t, selector } = useEnrollmentCopy();
  const [actor, setActor] = useState(""),
    [academies, setAcademies] = useState<Child[] | null>(null),
    [academy, setAcademy] = useState("");
  const [batches, setBatches] = useState<Batch[] | null>(null),
    [batch, setBatch] = useState("");
  const [candidates, setCandidates] = useState<Candidate[] | null>(null),
    [child, setChild] = useState("");
  const [roster, setRoster] = useState<Enrollment[] | null>(null),
    [cursor, setCursor] = useState<string | null>(null),
    [childCursor, setChildCursor] = useState<string | null>(null);
  const [reasons, setReasons] = useState<Record<string, EnrollmentReason | "">>(
    {},
  );
  const [notice, setNotice] = useState<
      "failed" | "unknown" | "original" | "saved" | "conflict" | null
    >(null),
    [pending, setPending] = useState(false),
    [pendingActor, setPendingActor] = useState("");
  const intent = useRef<Intent | null>(null);
  function reset() {
    setActor("");
    setAcademies(null);
    setAcademy("");
    setBatches(null);
    setBatch("");
    setCandidates(null);
    setChild("");
    setRoster(null);
    setCursor(null);
    setChildCursor(null);
    setReasons({});
    setNotice(null);
    // Unresolved write identity and payload intentionally survive session/focus invalidation in memory.
  }
  function fail() {
    setNotice("failed");
  }
  async function readRoster(
    who: string,
    workspace: string,
    selected: string,
    after: string | null,
    current: () => boolean,
  ) {
    setRoster(null);
    setReasons({});
    const result = await listBatchEnrollments(who, workspace, selected, after);
    if (!current()) return false;
    if (!result.ok) {
      fail();
      return false;
    }
    setRoster(result.data);
    setCursor(after);
    return true;
  }
  async function readCandidates(
    who: string,
    workspace: string,
    after: string | null,
    current: () => boolean,
  ) {
    setCandidates(null);
    setChild("");
    const result = await listEnrollmentCandidates(who, workspace, after);
    if (!current()) return;
    if (!result.ok) {
      fail();
      return;
    }
    setCandidates(result.data);
    setChildCursor(after);
  }
  async function readAcademy(
    who: string,
    workspace: string,
    current: () => boolean,
    preferred = "",
  ) {
    setAcademy(workspace);
    setBatch("");
    setBatches(null);
    setCandidates(null);
    setChild("");
    setRoster(null);
    setCursor(null);
    setChildCursor(null);
    setReasons({});
    const [batchResult, childResult] = await Promise.all([
      listEnrollmentBatches(who, workspace),
      listEnrollmentCandidates(who, workspace, null),
    ]);
    if (!current()) return;
    if (childResult.ok) setCandidates(childResult.data);
    else fail();
    if (!batchResult.ok) {
      fail();
      return;
    }
    setBatches(batchResult.data);
    const selected =
      batchResult.data.find((item) => item.id === preferred)?.id ||
      batchResult.data[0]?.id ||
      "";
    setBatch(selected);
    if (selected) await readRoster(who, workspace, selected, null, current);
  }
  async function load(who: string, current: () => boolean) {
    const retained = intent.current?.actor === who ? intent.current : null;
    const previousAcademy = retained?.workspace || academy,
      previousBatch = retained?.batch || batch;
    reset();
    setActor(who);
    const a = await familyAcademies(who);
    if (!current()) return;
    if (!a.ok) {
      fail();
      return;
    }
    setAcademies(a.data);
    const selected =
      a.data.find((item) => item.id === previousAcademy)?.id || a.data[0]?.id;
    if (selected) await readAcademy(who, selected, current, previousBatch);
    if (current() && intent.current)
      setNotice(
        intent.current.actor !== who
          ? "original"
          : intent.current.rejected
            ? "conflict"
            : intent.current.confirmed
              ? "failed"
              : "unknown",
      );
  }
  const b = useEnrollmentBoundary(reset, load);
  const frozen = pending || b.busy;
  async function perform(who: string, current: () => boolean) {
    const i = intent.current;
    if (!i) return;
    setActor(who);
    if (who !== i.actor) {
      reset();
      setActor(who);
      setNotice("original");
      return;
    }
    if (!i.confirmed && !i.rejected) {
      const result = await (
        i.kind === "save"
          ? saveEnrollment(i.actor, i.input)
          : changeEnrollment(i.actor, i.input)
      ).catch(() => ({ ok: false as const }));
      if (!current()) return;
      if (!result.ok) {
        if ("conflict" in result && result.conflict === true) i.rejected = true;
        else {
          setNotice("unknown");
          return;
        }
      } else {
        // A receipt describes the original operation, never the current roster state.
        i.confirmed = true;
      }
    }
    if (i.rejected) {
      // A known rejection is safe to release only after fresh identity and roster checks.
      // A failed reconciliation retains this rejected intent and retries reads only.
      const session = await familySession();
      if (!current()) return;
      if (!session.ok || session.data !== i.actor) {
        reset();
        if (session.ok) setActor(session.data);
        setNotice(session.ok ? "original" : "failed");
        return;
      }
      setAcademy(i.workspace);
      setBatch(i.batch);
      if (await readRoster(i.actor, i.workspace, i.batch, null, current)) {
        intent.current = null;
        setPending(false);
        setPendingActor("");
        setNotice("conflict");
      }
      return;
    }
    setAcademy(i.workspace);
    setBatch(i.batch);
    if (await readRoster(i.actor, i.workspace, i.batch, null, current)) {
      intent.current = null;
      setPending(false);
      setPendingActor("");
      setNotice("saved");
    }
  }
  function save() {
    if (intent.current || !actor || !academy || !batch || !child) return;
    intent.current = {
      kind: "save",
      actor,
      workspace: academy,
      batch,
      confirmed: false,
      input: {
        workspaceId: academy,
        batchId: batch,
        childId: child,
        requestId: crypto.randomUUID(),
      },
    };
    setPending(true);
    setPendingActor(actor);
    setNotice(null);
    void b.run(perform);
  }
  function change(row: Enrollment, status: EnrollmentState) {
    if (intent.current || !actor) return;
    const reason =
      status === "paused" || status === "withdrawn" ? reasons[row.id] : null;
    if (reason === "" || reason === undefined) return;
    intent.current = {
      kind: "change",
      actor,
      workspace: academy,
      batch,
      confirmed: false,
      input: {
        enrollmentId: row.id,
        status,
        expectedVersion: row.version,
        reason,
        requestId: crypto.randomUUID(),
      },
    };
    setPending(true);
    setPendingActor(actor);
    setNotice(null);
    void b.run(perform);
  }
  async function scoped(
    work: (who: string, current: () => boolean) => Promise<void>,
  ) {
    await b.run(async (who, current) => {
      if (who !== actor) {
        reset();
        await load(who, current);
        return;
      }
      setNotice(null);
      await work(who, current);
    });
  }
  return (
    <section
      aria-labelledby="enrollments-title"
      className="mt-8 border-t border-[#D4DAD5] pt-6"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-[#1F6F6B]">
            ParentPlus
          </p>
          <h2 id="enrollments-title" className="mt-1 text-2xl font-extrabold">
            {t.title}
          </h2>
        </div>
        <div className="w-36 shrink-0">{selector}</div>
      </div>
      <p className="mt-3 text-sm text-[#5C6B73]">{t.intro}</p>
      {!b.ready && (
        <p role="status" className="mt-4">
          {t.unavailable}
        </p>
      )}
      <div className={card}>
        <label className="block text-sm font-semibold">
          {t.academy}
          <select
            aria-label={t.academy}
            className={field}
            value={academy}
            disabled={!b.ready || frozen || !academies?.length}
            onChange={(event) => {
              const value = event.target.value;
              void scoped((who, current) => readAcademy(who, value, current));
            }}
          >
            {!academies?.length && <option value="">{t.noAcademies}</option>}
            {academies?.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </select>
        </label>
        {academies?.length === 0 && (
          <p className="mt-3 text-sm">{t.noAcademies}</p>
        )}
        {batches?.length === 0 && <p className="mt-3 text-sm">{t.noBatches}</p>}
        {batches && batches.length > 0 && (
          <div
            className="mt-4 flex flex-wrap gap-2"
            role="group"
            aria-label={t.title}
          >
            {batches.map((item) => (
              <button
                key={item.id}
                aria-pressed={batch === item.id}
                disabled={frozen}
                className={`rounded-full border px-4 py-2 text-sm font-semibold ${batch === item.id ? "border-[#1F6F6B] bg-[#1F6F6B] text-white" : "border-[#D4DAD5] bg-[#F3F5F1]"}`}
                onClick={() => {
                  void scoped(async (who, current) => {
                    setBatch(item.id);
                    setCursor(null);
                    await readRoster(who, academy, item.id, null, current);
                  });
                }}
              >
                {item.name}
              </button>
            ))}
          </div>
        )}
        {batch && (
          <p className="mt-3 text-sm text-[#5C6B73]">
            {batches?.find((item) => item.id === batch)?.courseName}
          </p>
        )}
        {candidates && (
          <>
            <label className="mt-4 block text-sm font-semibold">
              {t.child}
              <select
                aria-label={t.child}
                className={field}
                value={child}
                disabled={frozen}
                onChange={(event) => setChild(event.target.value)}
              >
                <option value="">{t.choose}</option>
                {candidates.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </label>
            {candidates.length === 0 && (
              <p className="mt-3 text-sm">{t.noCandidates}</p>
            )}
            <button
              className={button}
              disabled={frozen || !child || !batch || !b.ready}
              onClick={save}
            >
              {t.enrol}
            </button>
            <div className="flex flex-wrap gap-3 text-sm">
              {childCursor && (
                <button
                  className="mt-3 underline"
                  disabled={frozen}
                  onClick={() => {
                    void scoped((who, current) =>
                      readCandidates(who, academy, null, current),
                    );
                  }}
                >
                  {t.firstChildren}
                </button>
              )}
              {candidates.length === 50 && (
                <button
                  className="mt-3 underline"
                  disabled={frozen}
                  onClick={() => {
                    void scoped((who, current) =>
                      readCandidates(
                        who,
                        academy,
                        candidates.at(-1)!.id,
                        current,
                      ),
                    );
                  }}
                >
                  {t.moreChildren}
                </button>
              )}
            </div>
          </>
        )}
      </div>
      <button
        className="mt-4 rounded-xl border border-[#1F6F6B] px-4 py-2 text-sm font-semibold text-[#1F6F6B] disabled:opacity-50"
        disabled={!b.ready || b.busy || pending}
        onClick={() => {
          void b.run(load);
        }}
      >
        {t.refresh}
      </button>
      {pending && (
        <button
          className={`${button} ml-2`}
          disabled={!b.ready || b.busy || (!!actor && actor !== pendingActor)}
          onClick={() => {
            setNotice(null);
            void b.run(perform);
          }}
        >
          {t.check}
        </button>
      )}
      {b.busy && (
        <p role="status" className="mt-3 text-sm">
          {t.loading}
        </p>
      )}
      {(notice || b.failed) && (
        <p
          role={notice === "saved" ? "status" : "alert"}
          className="mt-3 text-sm"
        >
          {notice ? t[notice] : t.failed}
        </p>
      )}
      {roster && (
        <div className="mt-4 space-y-3">
          {roster.length === 0 && <p className={card}>{t.empty}</p>}
          {roster.map((row) => (
            <article
              key={row.id}
              className="rounded-2xl bg-white p-5 shadow-sm"
            >
              <div className="flex items-center justify-between gap-3">
                <h3 className="font-bold">{row.childName}</h3>
                <span className="rounded-full bg-[#EDF4EF] px-3 py-1 text-xs font-semibold text-[#1F6F6B]">
                  {t[row.status]}
                </span>
              </div>
              {(row.status === "active" || row.status === "paused") && (
                <>
                  <label className="mt-4 block text-sm">
                    {t.reason}
                    <select
                      aria-label={t.reason}
                      className={field}
                      value={reasons[row.id] || ""}
                      disabled={frozen}
                      onChange={(event) =>
                        setReasons((previous) => ({
                          ...previous,
                          [row.id]: event.target.value as EnrollmentReason | "",
                        }))
                      }
                    >
                      <option value="">{t.chooseReason}</option>
                      {(
                        ["temporary_break", "schedule_change", "other"] as const
                      ).map((reason) => (
                        <option key={reason} value={reason}>
                          {t[reason]}
                        </option>
                      ))}
                    </select>
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {row.status === "active" ? (
                      <button
                        className={button}
                        disabled={frozen || !reasons[row.id]}
                        onClick={() => change(row, "paused")}
                      >
                        {t.pause}
                      </button>
                    ) : (
                      <button
                        className={button}
                        disabled={frozen}
                        onClick={() => change(row, "active")}
                      >
                        {t.resume}
                      </button>
                    )}
                    <button
                      className={button}
                      disabled={frozen}
                      onClick={() => change(row, "completed")}
                    >
                      {t.complete}
                    </button>
                    <button
                      className="mt-3 rounded-xl border border-[#A64B3C] px-3 py-2 text-sm text-[#A64B3C] disabled:opacity-50"
                      disabled={frozen || !reasons[row.id]}
                      onClick={() => change(row, "withdrawn")}
                    >
                      {t.withdraw}
                    </button>
                  </div>
                </>
              )}
            </article>
          ))}
          <div className="flex flex-wrap gap-2">
            {cursor && (
              <button
                className={button}
                disabled={frozen}
                onClick={() => {
                  void scoped(async (who, current) => {
                    await readRoster(who, academy, batch, null, current);
                  });
                }}
              >
                {t.first}
              </button>
            )}
            {roster.length === 50 && (
              <button
                className={button}
                disabled={frozen}
                onClick={() => {
                  void scoped(async (who, current) => {
                    await readRoster(
                      who,
                      academy,
                      batch,
                      roster.at(-1)!.id,
                      current,
                    );
                  });
                }}
              >
                {t.next}
              </button>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
