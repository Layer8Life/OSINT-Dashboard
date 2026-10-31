import { useEffect, useState } from "react";
import type { Filters, Latest, OsintEvent } from "./types";
import { WINDOW_HOURS } from "./types";
import { ageHours, HOUR } from "./time";

const POLL_MS = 10 * 60_000;
export const STALE_AFTER_HOURS = 7;

export function useLatest() {
  const [data, setData] = useState<Latest | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const res = await fetch(`${import.meta.env.BASE_URL}data/latest.json?t=${Date.now()}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = (await res.json()) as Latest;
        if (!cancelled) {
          setData(json);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      }
    };
    load();
    const id = setInterval(load, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return { data, error };
}

export function useNow(intervalMs = 30_000): number {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
  return now;
}

export function isStale(generatedAt: string, now: number): boolean {
  return now - Date.parse(generatedAt) > STALE_AFTER_HOURS * HOUR;
}

export function applyFilters(events: OsintEvent[], f: Filters, now: number): OsintEvent[] {
  const maxAge = WINDOW_HOURS[f.window];
  const q = f.search.trim().toLowerCase();
  return events.filter((e) => {
    if (!f.signals.has(e.signal_type)) return false;
    if (e.signal_type === "news" && e.category && !f.categories.has(e.category)) return false;
    if (ageHours(e.last_seen, now) > maxAge) return false;
    if (!q) return true;
    return (
      e.title.toLowerCase().includes(q) ||
      (e.summary ?? "").toLowerCase().includes(q) ||
      (e.location?.name ?? "").toLowerCase().includes(q) ||
      (e.location?.organisation ?? "").toLowerCase().includes(q) ||
      e.sources.some((s) => s.outlet.toLowerCase().includes(q))
    );
  });
}
