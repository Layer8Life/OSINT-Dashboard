import { useMemo, useState } from "react";
import { applyFilters, useLatest, useNow } from "./data";
import { EventCard } from "./EventCard";
import { FeedPanel } from "./FeedPanel";
import { FiltersPanel } from "./FiltersPanel";
import { GlobeView } from "./GlobeView";
import { TopBar } from "./TopBar";
import type { Filters } from "./types";
import { WINDOW_HOURS } from "./types";

const DEFAULT_FILTERS: Filters = {
  categories: new Set(["tech", "science", "world"]),
  signals: new Set(["news", "earthquake", "hazard"]),
  window: "24h",
  search: "",
};

export function App() {
  const { data, error } = useLatest();
  const now = useNow();
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [drawer, setDrawer] = useState<"filters" | "feed" | null>(null);

  const visible = useMemo(() => applyFilters(data?.events ?? [], filters, now), [data, filters, now]);
  const placed = useMemo(() => visible.filter((e) => e.location), [visible]);
  const selected = data?.events.find((e) => e.id === selectedId) ?? null;

  const select = (id: string) => {
    setSelectedId(id);
    setDrawer(null);
  };
  const toggleDrawer = (d: "filters" | "feed") => setDrawer((cur) => (cur === d ? null : d));

  return (
    <div className={`app${drawer ? ` drawer-${drawer}` : ""}`}>
      <TopBar
        meta={data?.meta ?? null}
        error={error}
        now={now}
        onToggleFilters={() => toggleDrawer("filters")}
        onToggleFeed={() => toggleDrawer("feed")}
      />
      <aside className="panel panel--left">
        <FiltersPanel filters={filters} onChange={setFilters} visible={visible} />
      </aside>
      <main className="stage">
        <GlobeView
          events={placed}
          selectedId={selectedId}
          windowHours={WINDOW_HOURS[filters.window]}
          now={now}
          onSelect={select}
        />
        {!data && !error && <div className="loading">Acquiring signals…</div>}
        {selected && <EventCard event={selected} now={now} onClose={() => setSelectedId(null)} />}
      </main>
      <aside className="panel panel--right">
        <FeedPanel events={visible} selectedId={selectedId} now={now} onSelect={select} />
      </aside>
      {drawer && <div className="scrim" onClick={() => setDrawer(null)} />}
    </div>
  );
}
