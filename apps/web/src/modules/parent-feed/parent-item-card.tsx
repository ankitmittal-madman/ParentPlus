"use client";
import Link from "next/link";
import { attendanceStatus } from "../attendance/contracts";
import { date, text, timestamp, uuid } from "../attendance/validation";
import { button } from "../attendance/copy";
import { safeParentAction, type ParentItemEnvelope } from "./contracts";
import { parentDate, useParentCopy } from "./copy";
export function ParentItemCard({ item }: { item: ParentItemEnvelope }) {
  const { t, lang } = useParentCopy(); const p = item.payload;
  // Immutable 053 writes attendance; attendance_record is a read-compatible founder alias.
  const known = ["attendance", "attendance_record"].includes(item.type) && item.schemaVersion === 1 && uuid(p.session_id) && date(p.date) && attendanceStatus(p.status) && timestamp(p.confirmed_at) && p.title === "Attendance recorded" && text(p.body, 2000);
  const action = known ? null : safeParentAction(p.action, item.childId);
  const human = item.type.slice(0, 80).replace(/[_-]+/g, " "); const title = text(p.title, 160) ? p.title : human.charAt(0).toUpperCase() + human.slice(1);
  return <article className="rounded-2xl border-l-4 border-[#1F6F6B] bg-white p-4 shadow-sm"><h3 className="break-words font-bold">{known ? t.attendanceTitle : title}</h3>{known ? <><p className="mt-2 font-semibold">{t[p.status as "present"]}</p><p className="text-sm">{parentDate(p.date as string, lang)}</p><p className="mt-1 text-xs text-[#5C6B73]">{t.confirmed}</p></> : <>{text(p.body, 2000) && <p className="mt-2 whitespace-pre-wrap break-words text-sm">{p.body}</p>}{action && <Link prefetch={false} className={`${button} mt-3 inline-flex items-center`} href={action.href}>{action.label}</Link>}</>}</article>;
}
