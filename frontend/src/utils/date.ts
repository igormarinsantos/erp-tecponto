/**
 * Parses a server-provided date/datetime string ("YYYY-MM-DD" or
 * "YYYY-MM-DD HH:mm:ss", no timezone marker) as local time.
 *
 * `new Date("YYYY-MM-DD")` is parsed as UTC midnight per the ECMA-262 spec.
 * Formatting that in local time shifts it back a day for any timezone behind
 * UTC (all of Brazil) — e.g. a diagnosis saved today at 17:00 in São Paulo
 * would display as "yesterday, 21:00". Appending a time component before
 * parsing forces the local-time interpretation instead.
 */
export function parseServerDate(value: string | null | undefined): Date | null {
  if (!value) return null;
  const normalized = value.includes("T") || value.includes(" ") ? value.replace(" ", "T") : `${value}T00:00:00`;
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? null : date;
}
