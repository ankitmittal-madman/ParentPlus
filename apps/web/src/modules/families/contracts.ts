export const isId = (v: unknown): v is string =>
  typeof v === "string" &&
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(v);
export const isToken = (v: unknown): v is string =>
  typeof v === "string" && /^[0-9a-f]{64}$/.test(v);
export const isName = (v: unknown): v is string =>
  typeof v === "string" && v.trim().length > 0 && Array.from(v).length <= 120;
export const isDate = (v: unknown): v is string =>
  typeof v === "string" &&
  v.length <= 40 &&
  /^\d{4}-\d\d-\d\dT/.test(v) &&
  Number.isFinite(Date.parse(v));
export type Result<T> = { ok: true; data: T } | { ok: false };
export type Invite = { inviteId: string; expiresAt: string };
export type Preview = {
  academyName: string;
  expiresAt: string;
  state: "pending" | "accepted";
};
export type RosterRow = {
  id: string;
  name: string;
  status: "active" | "alumni" | "restricted" | "archived";
};
export type Child = { id: string; name: string };
export function rows<T>(
  value: unknown,
  max: number,
  project: (r: Record<string, unknown>) => T | null,
): T[] | null {
  if (!Array.isArray(value) || value.length > max) return null;
  const output: T[] = [];
  for (const item of value) {
    if (!item || typeof item !== "object" || Array.isArray(item)) return null;
    const row = project(item);
    if (row === null) return null;
    output.push(row);
  }
  return output;
}
export function rosterRows(
  value: unknown,
  nameKey: string,
  max: number,
): RosterRow[] | null {
  const seen = new Set<string>();
  return rows(value, max, (r) => {
    if (
      !isId(r.relationship_id) ||
      seen.has(r.relationship_id.toLowerCase()) ||
      !isName(r[nameKey]) ||
      !["active", "alumni", "restricted", "archived"].includes(
        String(r.relationship_status),
      )
    )
      return null;
    seen.add(r.relationship_id.toLowerCase());
    return {
      id: r.relationship_id,
      name: r[nameKey] as string,
      status: r.relationship_status as RosterRow["status"],
    };
  });
}
