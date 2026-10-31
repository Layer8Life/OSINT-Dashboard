import { useState } from "react";
import type { OsintEvent } from "./types";
import { eventColor, eventLabel } from "./theme";
import { relative } from "./time";

interface Props {
  events: OsintEvent[];
  selectedId: string | null;
  now: number;
  onSelect: (id: string) => void;
}

const PAGE = 80;

export function FeedPanel({ events, selectedId, now, onSelect }: Props) {
  const [tab, setTab] = useState<"placed" | "unplaced">("placed");
  const placed = events.filter((e) => e.location);
  const unplaced = events.filter((e) => !e.location);
  const list = tab === "placed" ? placed : unplaced;

  return (
    <div className="feed">
      <div className="tabs" role="tablist">
        <button role="tab" aria-selected={tab === "placed"} onClick={() => setTab("placed")}>
          On globe <span className="count">{placed.length}</span>
        </button>
        <button role="tab" aria-selected={tab === "unplaced"} onClick={() => setTab("unplaced")}>
          Unplaced <span className="count">{unplaced.length}</span>
        </button>
      </div>
      {list.length === 0 && <p className="empty">No Events match the current filters.</p>}
      <ul className="feed__list">
        {list.slice(0, PAGE).map((e) => (
          <li key={e.id}>
            <button
              className={`feed__item${e.id === selectedId ? " is-selected" : ""}`}
              style={{ ["--c" as string]: eventColor(e) }}
              onClick={() => onSelect(e.id)}
            >
              <span className="feed__meta">
                <span className={`shape shape--${e.signal_type}`} />
                {eventLabel(e)}
                <span className="muted">· {relative(e.last_seen, now)}</span>
                {e.sources.length > 1 && <span className="muted">· {e.sources.length} sources</span>}
              </span>
              <span className="feed__title">{e.title}</span>
              {e.location && <span className="feed__place">{e.location.name}</span>}
            </button>
          </li>
        ))}
      </ul>
      {list.length > PAGE && <p className="empty">Showing newest {PAGE} of {list.length}. Narrow with filters or search.</p>}
    </div>
  );
}
