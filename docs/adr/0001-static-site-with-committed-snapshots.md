# Static site with Snapshots committed by a scheduled job, no backend

The dashboard has a £0 budget and only needs new data every 6 hours, so there is no server or database. A GitHub Actions cron runs the Python collector each Refresh and commits the resulting Snapshot as JSON to a public repo; the React front end is a static site on GitHub Pages that reads those JSON files directly. Live, sub-hour signals (flights, ships) are out of scope as a consequence.

## Considered Options

- **Hosted backend + database** (e.g. a small API on a free tier): rejected — free tiers sleep or expire, and nothing needs real-time queries.
- **Private repo**: rejected — Pages from a private repo needs a paid plan, and all collected data is already public information.

## Consequences

- Snapshots are pruned after 90 days to keep the repo small.
- The front end must detect a failed or missed Refresh itself and show the dashboard as Stale.
- Open-Event state for grouping Ongoing Events lives in the committed JSON, so the collector reads the previous Snapshot at the start of each Refresh.
