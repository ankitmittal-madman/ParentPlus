"use client";
import { useState } from "react";
import { familyChildren } from "@/lib/families/actions";
import { listParentEnrollments } from "@/lib/enrollments/actions";
import type { Child } from "@/modules/families/contracts";
import type { ParentEnrollment } from "./contracts";
import {
  useEnrollmentCopy,
  useEnrollmentBoundary,
  button,
  field,
  card,
} from "./shared";

export default function ParentClassesPanel() {
  const { t, selector } = useEnrollmentCopy();
  const [actor, setActor] = useState(""),
    [children, setChildren] = useState<Child[] | null>(null),
    [child, setChild] = useState("");
  const [classes, setClasses] = useState<ParentEnrollment[] | null>(null),
    [failed, setFailed] = useState(false);
  function reset() {
    setActor("");
    setChildren(null);
    setChild("");
    setClasses(null);
    setFailed(false);
  }
  async function read(who: string, selected: string, current: () => boolean) {
    setClasses(null);
    setFailed(false);
    setChild(selected);
    const result = await listParentEnrollments(who, selected);
    if (!current()) return;
    if (!result.ok) {
      setFailed(true);
      return;
    }
    setClasses(result.data);
  }
  async function load(who: string, current: () => boolean) {
    const previous = child;
    reset();
    setActor(who);
    const result = await familyChildren(who);
    if (!current()) return;
    if (!result.ok) {
      setFailed(true);
      return;
    }
    setChildren(result.data);
    const selected =
      result.data.find((item) => item.id === previous)?.id ||
      result.data[0]?.id;
    if (selected) await read(who, selected, current);
  }
  const b = useEnrollmentBoundary(reset, load);
  return (
    <section
      aria-labelledby="child-classes-title"
      className="mt-8 border-t border-[#D4DAD5] pt-6"
    >
      <div className="flex items-start justify-between gap-3">
        <h2 id="child-classes-title" className="text-2xl font-extrabold">
          {t.classes}
        </h2>
        <div className="w-36 shrink-0">{selector}</div>
      </div>
      <p className="mt-3 text-sm text-[#5C6B73]">{t.classesIntro}</p>
      {!b.ready && (
        <p role="status" className="mt-3">
          {t.unavailable}
        </p>
      )}
      {children && children.length > 0 && (
        <label className="mt-4 block text-sm font-semibold">
          {t.classChild}
          <select
            className={field}
            aria-label={t.classChild}
            value={child}
            disabled={b.busy}
            onChange={(event) => {
              const selected = event.target.value;
              void b.run(async (who, current) => {
                if (who !== actor) {
                  await load(who, current);
                  return;
                }
                await read(who, selected, current);
              });
            }}
          >
            {children.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
      )}
      <button
        className={button}
        disabled={!b.ready || b.busy}
        onClick={() => {
          void b.run(load);
        }}
      >
        {t.refreshClasses}
      </button>
      {b.busy && (
        <p role="status" className="mt-3">
          {t.classesLoading}
        </p>
      )}
      {(failed || b.failed) && (
        <p role="alert" className="mt-3">
          {t.classesFailed}
        </p>
      )}
      {children?.length === 0 && <p className={card}>{t.noChildren}</p>}
      {classes?.length === 0 && <p className={card}>{t.noClasses}</p>}
      {classes?.map((item) => (
        <article className={card} key={item.id}>
          <div className="flex items-center justify-between gap-3">
            <h3 className="font-bold">{item.academyName}</h3>
            <span className="rounded-full bg-[#EDF4EF] px-3 py-1 text-xs font-semibold text-[#1F6F6B]">
              {t[item.status]}
            </span>
          </div>
          <p className="mt-3 text-sm">
            {item.courseName} · {item.batchName}
          </p>
        </article>
      ))}
    </section>
  );
}
