import type { OsintEvent } from "./types";
import { eventColor, eventLabel } from "./theme";
import { relative } from "./time";

interface Props {
  event: OsintEvent;
  now: number;
  onClose: () => void;
}

function Details({ event }: { event: OsintEvent }) {
  const d = event.details as Record<string, string | number | boolean | null>;
  if (event.signal_type === "earthquake") {
    return (
      <dl className="card__facts">
        <dt>Magnitude</dt>
        <dd>{Number(d.magnitude).toFixed(1)}</dd>
        <dt>Depth</dt>
        <dd>{Math.round(Number(d.depthKm))} km</dd>
        {d.tsunami ? (
          <>
            <dt>Tsunami</dt>
            <dd>Warning issued</dd>
          </>
        ) : null}
      </dl>
    );
  }
  if (event.signal_type === "hazard") {
    return (
      <dl className="card__facts">
        <dt>Type</dt>
        <dd>{String(d.hazardType)}</dd>
        <dt>Alert</dt>
        <dd className={`alert alert--${String(d.alertLevel).toLowerCase()}`}>{String(d.alertLevel)}</dd>
        {d.severity ? (
          <>
            <dt>Severity</dt>
            <dd>{String(d.severity)}</dd>
          </>
        ) : null}
      </dl>
    );
  }
  return null;
}

export function EventCard({ event, now, onClose }: Props) {
  const loc = event.location;
  return (
    <article className="card" style={{ ["--c" as string]: eventColor(event) }}>
      <header className="card__head">
        <span className="chip">{eventLabel(event)}</span>
        {event.closed && <span className="chip chip--muted">Closed</span>}
        <span className="card__time">Last seen {relative(event.last_seen, now)}</span>
        <button className="icon-btn" onClick={onClose} aria-label="Close">
          ×
        </button>
      </header>
      <h2 className="card__title">{event.title}</h2>
      {loc ? (
        <p className="card__loc">
          <span className={`basis basis--${loc.basis}`}>
            {loc.basis === "event_site" ? "Event Site" : "Organisation HQ"}
          </span>
          {loc.basis === "organisation_hq" && loc.organisation ? `${loc.organisation}, ${loc.name}` : loc.name}
        </p>
      ) : (
        <p className="card__loc">
          <span className="basis">Unplaced</span>No place or organisation identified
        </p>
      )}
      {event.summary && <p className="card__summary">{event.summary}</p>}
      <Details event={event} />
      <h3 className="card__sub">
        {event.sources.length} source{event.sources.length === 1 ? "" : "s"}
      </h3>
      <ul className="card__sources">
        {event.sources.map((s) => (
          <li key={s.url}>
            <a href={s.url} target="_blank" rel="noreferrer noopener">
              <span className="outlet">{s.outlet}</span>
              {s.title}
            </a>
            <span className="muted"> · {relative(s.published_at, now)}</span>
          </li>
        ))}
      </ul>
    </article>
  );
}
