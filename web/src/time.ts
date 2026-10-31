export const HOUR = 3_600_000;

export function ageHours(iso: string, now: number): number {
  return (now - Date.parse(iso)) / HOUR;
}

export function relative(iso: string, now: number): string {
  const mins = Math.round((now - Date.parse(iso)) / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 48) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

export function countdown(iso: string, now: number): string {
  const mins = Math.max(0, Math.round((Date.parse(iso) - now) / 60_000));
  if (mins === 0) return "due now";
  const h = Math.floor(mins / 60);
  return h ? `in ${h}h ${mins % 60}m` : `in ${mins}m`;
}

export function utcClock(iso: string): string {
  const d = new Date(iso);
  return `${String(d.getUTCHours()).padStart(2, "0")}:${String(d.getUTCMinutes()).padStart(2, "0")} UTC`;
}
