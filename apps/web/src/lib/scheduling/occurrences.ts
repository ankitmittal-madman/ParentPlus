import { Temporal } from "@js-temporal/polyfill";

export type ScheduleRule = {
  startDate: string;
  startTime: string;
  timeZone: string;
  durationMinutes: number;
  recurrence: { kind: "once" } | { kind: "weekly"; untilDate: string };
};

type Occurrence = { localDate: string; startsAt: string; endsAt: string };
const MAX_OCCURRENCES = 104;

export class ScheduleTimeError extends RangeError {
  constructor(
    readonly kind: "ambiguous" | "nonexistent",
    readonly localDate: string,
    readonly localTime: string,
    readonly timeZone: string,
  ) {
    super("The local time is ambiguous or nonexistent; choose another time.");
    this.name = "ScheduleTimeError";
  }
}

function parseDate(value: string): Temporal.PlainDate {
  if (typeof value !== "string" || !/^(?!0000)\d{4}-\d{2}-\d{2}$/.test(value)) {
    throw new RangeError("Enter a valid calendar date.");
  }
  try {
    return Temporal.PlainDate.from(value);
  } catch {
    throw new RangeError("Enter a valid calendar date.");
  }
}

export function expandSchedule(rule: ScheduleRule): Occurrence[] {
  if (!rule || !rule.recurrence || !["once", "weekly"].includes(rule.recurrence.kind)) {
    throw new RangeError("Choose a valid recurrence.");
  }
  const start = parseDate(rule.startDate);
  if (typeof rule.startTime !== "string" || !/^([01]\d|2[0-3]):[0-5]\d$/.test(rule.startTime)) {
    throw new RangeError("Enter a valid local time.");
  }
  if (typeof rule.timeZone !== "string" || !/^[A-Za-z][A-Za-z0-9_+./-]*$/.test(rule.timeZone)) {
    throw new RangeError("Enter a valid workspace time zone.");
  }
  try {
    new Intl.DateTimeFormat("en", { timeZone: rule.timeZone });
  } catch {
    throw new RangeError("Enter a valid workspace time zone.");
  }
  if (!Number.isInteger(rule.durationMinutes) || rule.durationMinutes < 1 || rule.durationMinutes > 1440) {
    throw new RangeError("Enter a duration between 1 and 1440 minutes.");
  }
  const until = rule.recurrence.kind === "weekly" ? parseDate(rule.recurrence.untilDate) : start;
  if (Temporal.PlainDate.compare(until, start) < 0) {
    throw new RangeError("The end date must not precede the start date.");
  }
  const localTime = Temporal.PlainTime.from(rule.startTime);
  const occurrences: Occurrence[] = [];
  for (let date = start; Temporal.PlainDate.compare(date, until) <= 0; date = date.add({ weeks: 1 })) {
    if (occurrences.length >= MAX_OCCURRENCES) {
      throw new RangeError("The schedule exceeds the local occurrence limit.");
    }
    let instant: Temporal.Instant;
    const localDateTime = date.toPlainDateTime(localTime);
    try {
      instant = localDateTime.toZonedDateTime(rule.timeZone, { disambiguation: "reject" }).toInstant();
    } catch (error) {
      if (!(error instanceof RangeError)) throw error;
      const earlier = localDateTime.toZonedDateTime(rule.timeZone, { disambiguation: "earlier" });
      const later = localDateTime.toZonedDateTime(rule.timeZone, { disambiguation: "later" });
      if (earlier.epochNanoseconds === later.epochNanoseconds) throw error;
      const kind = earlier.toPlainDateTime().equals(localDateTime) && later.toPlainDateTime().equals(localDateTime)
        ? "ambiguous" : "nonexistent";
      throw new ScheduleTimeError(kind, date.toString(), rule.startTime, rule.timeZone);
    }
    occurrences.push({
      localDate: date.toString(),
      startsAt: instant.toString(),
      endsAt: instant.add({ minutes: rule.durationMinutes }).toString(),
    });
    if (rule.recurrence.kind === "once") break;
  }
  return occurrences;
}
