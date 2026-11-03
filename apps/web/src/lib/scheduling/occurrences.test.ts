import { describe, expect, it } from "vitest";
import { expandSchedule, type ScheduleRule } from "./occurrences";

const oneOff: ScheduleRule = {
  startDate: "2026-11-03", startTime: "17:00", timeZone: "Asia/Kolkata",
  durationMinutes: 60, recurrence: { kind: "once" },
};

describe("expandSchedule", () => {
  it("converts a one-off workspace time to UTC", () => {
    expect(expandSchedule(oneOff)).toEqual([{ localDate: "2026-11-03", startsAt: "2026-11-03T11:30:00Z", endsAt: "2026-11-03T12:30:00Z" }]);
  });

  it("expands weekly sessions through an inclusive end date", () => {
    const result = expandSchedule({ ...oneOff, recurrence: { kind: "weekly", untilDate: "2026-11-17" } });
    expect(result.map((item) => item.localDate)).toEqual(["2026-11-03", "2026-11-10", "2026-11-17"]);
  });

  it("keeps local weekly time across an offset change", () => {
    const result = expandSchedule({ ...oneOff, startDate: "2026-03-01", startTime: "10:00", timeZone: "America/New_York", recurrence: { kind: "weekly", untilDate: "2026-03-08" } });
    expect(result.map((item) => item.startsAt)).toEqual(["2026-03-01T15:00:00Z", "2026-03-08T14:00:00Z"]);
  });

  it("rejects a nonexistent daylight-saving time", () => {
    expect(() => expandSchedule({ ...oneOff, startDate: "2026-03-08", startTime: "02:30", timeZone: "America/New_York" })).toThrow(/ambiguous or nonexistent/i);
  });

  it("rejects an ambiguous daylight-saving time", () => {
    expect(() => expandSchedule({ ...oneOff, startDate: "2026-11-01", startTime: "01:30", timeZone: "America/New_York" })).toThrow(/ambiguous or nonexistent/i);
  });

  it("rejects invalid dates times and time zones", () => {
    for (const change of [{ startDate: "2026-02-30" }, { startTime: "24:00" }, { timeZone: "Invalid/Zone" }, { timeZone: "+05:30" }]) {
      expect(() => expandSchedule({ ...oneOff, ...change })).toThrow();
    }
  });

  it("rejects invalid durations", () => {
    for (const durationMinutes of [0, -1, 1.5, 1441, Number.NaN]) {
      expect(() => expandSchedule({ ...oneOff, durationMinutes })).toThrow();
    }
  });

  it("rejects a weekly end date before the start", () => {
    expect(() => expandSchedule({ ...oneOff, recurrence: { kind: "weekly", untilDate: "2026-11-02" } })).toThrow();
  });

  it("rejects weekly expansion beyond the local safety limit", () => {
    expect(() => expandSchedule({ ...oneOff, recurrence: { kind: "weekly", untilDate: "2030-11-03" } })).toThrow(/limit/i);
  });
  it("does not add a weekly session beyond the end date", () => {
    const result = expandSchedule({ ...oneOff, recurrence: { kind: "weekly", untilDate: "2026-11-16" } });
    expect(result.map((item) => item.localDate)).toEqual(["2026-11-03", "2026-11-10"]);
  });

  it("accepts exactly the local occurrence limit", () => {
    const result = expandSchedule({ ...oneOff, startDate: "2026-01-06", recurrence: { kind: "weekly", untilDate: "2027-12-28" } });
    expect(result).toHaveLength(104);
    expect(result.at(-1)?.localDate).toBe("2027-12-28");
  });

  it("rejects a later weekly occurrence in a daylight-saving gap", () => {
    expect(() => expandSchedule({ ...oneOff, startDate: "2026-03-01", startTime: "02:30", timeZone: "America/New_York", recurrence: { kind: "weekly", untilDate: "2026-03-08" } })).toThrow(/ambiguous or nonexistent/i);
  });

  it("rejects a half-hour daylight-saving gap", () => {
    expect(() => expandSchedule({ ...oneOff, startDate: "2026-10-04", startTime: "02:15", timeZone: "Australia/Lord_Howe" })).toThrow(/ambiguous or nonexistent/i);
  });

  it("calculates duration as elapsed time across a daylight-saving change", () => {
    const result = expandSchedule({ ...oneOff, startDate: "2026-03-08", startTime: "01:30", timeZone: "America/New_York", durationMinutes: 120 });
    expect(result[0]).toMatchObject({ startsAt: "2026-03-08T06:30:00Z", endsAt: "2026-03-08T08:30:00Z" });
  });

  it("rejects the first occurrence beyond the local limit", () => {
    expect(() => expandSchedule({ ...oneOff, startDate: "2026-01-06", recurrence: { kind: "weekly", untilDate: "2028-01-04" } })).toThrow(/limit/i);
  });

  it("returns a valid extended ISO instant when the end crosses year 9999", () => {
    const result = expandSchedule({ ...oneOff, startDate: "9999-12-31", startTime: "23:59", timeZone: "UTC", durationMinutes: 1 });
    expect(result[0].endsAt).toBe("+010000-01-01T00:00:00Z");
  });

});
