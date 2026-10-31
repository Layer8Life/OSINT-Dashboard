import type { Meta } from "./types";
import { isStale } from "./data";
import { countdown, relative, utcClock } from "./time";

interface Props {
  meta: Meta | null;
  error: string | null;
  now: number;
  onToggleFilters: () => void;
  onToggleFeed: () => void;
}

const ENRICHMENT_LABEL = { llm: "AI enrichment", mixed: "Partial AI enrichment", fallback: "Offline enrichment", none: "No new articles" };

export function TopBar({ meta, error, now, onToggleFilters, onToggleFeed }: Props) {
  const stale = meta ? isStale(meta.generatedAt, now) : false;
  return (
    <header className="topbar">
      <button className="icon-btn drawer-btn" onClick={onToggleFilters} aria-label="Filters">
        ☰
      </button>
      <div className="brand">
        <span className="brand__dot" />
        OSINT<span className="hide-xs"> <span className="brand__sep">//</span> Global Watch</span>
      </div>
      <div className="status">
        {error && !meta && <span className="badge badge--stale">Data unavailable: {error}</span>}
        {meta && (
          <>
            <span className="status__item" title={meta.generatedAt}>
              <span className="hide-xs">Last Refresh </span>
              <strong>{utcClock(meta.generatedAt)}</strong>
              <span className="muted"> ({relative(meta.generatedAt, now)})</span>
            </span>
            <span className="status__item hide-sm">
              Next <strong>{countdown(meta.nextRefreshAt, now)}</strong>
            </span>
            <span className={`badge hide-sm${meta.enrichment === "llm" ? "" : " badge--muted"}`}>
              {ENRICHMENT_LABEL[meta.enrichment]}
            </span>
            {stale && <span className="badge badge--stale">Stale</span>}
          </>
        )}
      </div>
      <button className="icon-btn drawer-btn" onClick={onToggleFeed} aria-label="Event feed">
        ≡
      </button>
    </header>
  );
}
