// Mirrors collector/models.py. Terms follow CONTEXT.md.

export type SignalType = "news" | "earthquake" | "hazard";
export type Category = "tech" | "science" | "world";
export type LocationBasis = "event_site" | "organisation_hq";

export interface Source {
  outlet: string;
  title: string;
  url: string;
  published_at: string;
}

export interface Location {
  lat: number;
  lon: number;
  name: string;
  basis: LocationBasis;
  organisation: string | null;
}

export interface OsintEvent {
  id: string;
  signal_type: SignalType;
  title: string;
  first_seen: string;
  last_seen: string;
  significance: number;
  category: Category | null;
  summary: string | null;
  location: Location | null;
  sources: Source[];
  closed: boolean;
  details: Record<string, unknown>;
}

export interface Meta {
  generatedAt: string;
  nextRefreshAt: string;
  refreshHours: number;
  enrichment: "llm" | "fallback" | "mixed" | "none";
  newArticles: number;
  counts: Record<string, number>;
}

export interface Latest {
  meta: Meta;
  events: OsintEvent[];
}

export type LiveWindow = "6h" | "24h" | "7d";
export const WINDOW_HOURS: Record<LiveWindow, number> = { "6h": 6, "24h": 24, "7d": 168 };

export interface Filters {
  categories: Set<Category>;
  signals: Set<SignalType>;
  window: LiveWindow;
  search: string;
}
