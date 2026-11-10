/** Narrow JSON guards shared by the attendance and parent RPC decoders. */
export const object = (v: unknown): v is Record<string, unknown> => v !== null && typeof v === "object" && !Array.isArray(v);
export const uuid = (v: unknown): v is string => typeof v === "string" && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(v);
export const id = (v: string) => v.toLowerCase();
export const integer = (v: unknown, min = 0, max = 2147483647): v is number => typeof v === "number" && Number.isInteger(v) && v >= min && v <= max;
export const text = (v: unknown, max = 120): v is string => typeof v === "string" && v.trim().length > 0 && Array.from(v).length <= max;
export const token = (v: unknown): v is string => typeof v === "string" && /^[a-f0-9]{64}$/.test(v);
export function date(v: unknown): v is string {
  if (typeof v !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(v) || v < "2000-01-01" || v > "2100-12-31")
    return false;
  const d = new Date(`${v}T00:00:00Z`);
  return Number.isFinite(d.getTime()) && d.toISOString().slice(0, 10) === v;
}
export function timestamp(v: unknown): v is string {
  return typeof v === "string" && /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?(?:Z|\+00:00)$/.test(v) && Number.isFinite(Date.parse(v)) && new Date(v).toISOString().slice(0, 10) === v.slice(0, 10);
}
export function zone(v: unknown): v is string {
  if (typeof v !== "string" || v.length > 100 || !v)
    return false;
  try {
    new Intl.DateTimeFormat("en", { timeZone: v });
    return true;
  }
  catch {
    return false;
  }
}
export const exact = (v: Record<string, unknown>, keys: string[]) => Object.keys(v).length === keys.length && keys.every(k => Object.hasOwn(v, k));
export function bounded<T>(v: unknown, max: number, decode: (v: unknown) => T | null, key: (v: T) => string): T[] | null {
  if (!Array.isArray(v) || v.length > max)
    return null;
  const result: T[] = [];
  const seen = new Set<string>();
  for (const x of v) {
    const item = decode(x);
    if (!item || seen.has(key(item)))
      return null;
    seen.add(key(item));
    result.push(item);
  }
  return result;
}
export const increasing = <T,>(items: T[], compare: (a: T, b: T) => number) => items.every((item, i) => i === 0 || compare(items[i - 1], item) < 0);
/** RPC timestamps are UTC; normalize their accepted fractional precision before comparing. */
export function timestampOrder(a: string, b: string): number {
  const normalize = (value: string) => {
    const fraction = value.slice(19).replace(/(?:Z|\+00:00)$/, "").slice(1).padEnd(6, "0");
    return `${value.slice(0, 19)}.${fraction}`;
  };
  const left = normalize(a);
  const right = normalize(b);
  return left < right ? -1 : left > right ? 1 : 0;
}
export const sessionOrder = (a: {
  startsAt: string;
  id: string;
}, b: {
  startsAt: string;
  id: string;
}) => timestampOrder(a.startsAt, b.startsAt) || a.id.localeCompare(b.id);
export const signalOrder = (a: {
  childId: string;
  actorId: string;
}, b: {
  childId: string;
  actorId: string;
}) => a.childId.localeCompare(b.childId) || a.actorId.localeCompare(b.actorId);
