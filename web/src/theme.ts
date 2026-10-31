import type { Category, OsintEvent, SignalType } from "./types";

export const CATEGORY_COLOR: Record<Category, string> = {
  tech: "#38bdf8",
  science: "#a3e635",
  world: "#facc15",
};

export const SIGNAL_COLOR: Record<Exclude<SignalType, "news">, string> = {
  earthquake: "#fb923c",
  hazard: "#f43f5e",
};

export const CATEGORY_LABEL: Record<Category, string> = { tech: "Tech", science: "Science", world: "World" };
export const SIGNAL_LABEL: Record<SignalType, string> = { news: "News", earthquake: "Earthquake", hazard: "Hazard" };

export function eventColor(e: OsintEvent): string {
  if (e.signal_type === "news") return CATEGORY_COLOR[e.category ?? "world"];
  return SIGNAL_COLOR[e.signal_type];
}

export function eventLabel(e: OsintEvent): string {
  return e.signal_type === "news" ? CATEGORY_LABEL[e.category ?? "world"] : SIGNAL_LABEL[e.signal_type];
}
