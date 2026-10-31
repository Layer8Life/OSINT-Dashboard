import type { Category, Filters, LiveWindow, OsintEvent, SignalType } from "./types";
import { CATEGORY_COLOR, CATEGORY_LABEL, SIGNAL_COLOR, SIGNAL_LABEL } from "./theme";

interface Props {
  filters: Filters;
  onChange: (f: Filters) => void;
  visible: OsintEvent[];
}

const CATEGORIES: Category[] = ["tech", "science", "world"];
const SIGNALS: SignalType[] = ["news", "earthquake", "hazard"];
const WINDOWS: LiveWindow[] = ["6h", "24h", "7d"];

function toggle<T>(set: Set<T>, value: T): Set<T> {
  const next = new Set(set);
  if (next.has(value)) next.delete(value);
  else next.add(value);
  return next;
}

export function FiltersPanel({ filters, onChange, visible }: Props) {
  const count = (pred: (e: OsintEvent) => boolean) => visible.filter(pred).length;

  return (
    <div className="filters">
      <label className="search">
        <span className="sr-only">Search</span>
        <input
          type="search"
          placeholder="Search events, places, outlets…"
          value={filters.search}
          onChange={(e) => onChange({ ...filters, search: e.target.value })}
        />
      </label>

      <section>
        <h3 className="section-title">Live Window</h3>
        <div className="segmented" role="radiogroup">
          {WINDOWS.map((w) => (
            <button
              key={w}
              role="radio"
              aria-checked={filters.window === w}
              className={filters.window === w ? "on" : ""}
              onClick={() => onChange({ ...filters, window: w })}
            >
              {w}
            </button>
          ))}
        </div>
      </section>

      <section>
        <h3 className="section-title">Signal Type</h3>
        {SIGNALS.map((s) => (
          <label key={s} className="toggle">
            <input
              type="checkbox"
              checked={filters.signals.has(s)}
              onChange={() => onChange({ ...filters, signals: toggle(filters.signals, s) })}
            />
            <span className={`shape shape--${s}`} style={{ ["--c" as string]: s === "news" ? "#cbd5e1" : SIGNAL_COLOR[s] }} />
            <span className="toggle__label">{SIGNAL_LABEL[s]}</span>
            <span className="count">{count((e) => e.signal_type === s)}</span>
          </label>
        ))}
      </section>

      <section>
        <h3 className="section-title">News Category</h3>
        {CATEGORIES.map((c) => (
          <label key={c} className="toggle">
            <input
              type="checkbox"
              checked={filters.categories.has(c)}
              disabled={!filters.signals.has("news")}
              onChange={() => onChange({ ...filters, categories: toggle(filters.categories, c) })}
            />
            <span className="swatch" style={{ background: CATEGORY_COLOR[c] }} />
            <span className="toggle__label">{CATEGORY_LABEL[c]}</span>
            <span className="count">{count((e) => e.category === c)}</span>
          </label>
        ))}
      </section>

      <section className="legend">
        <h3 className="section-title">Legend</h3>
        <p>Marker size = Significance. Markers fade with age. Pulsing rings = seen in the last 6h.</p>
      </section>
    </div>
  );
}
