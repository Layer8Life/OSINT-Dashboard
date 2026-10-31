# OSINT Global Watch

A personal OSINT dashboard: News (Tech, Science, World), Earthquakes and natural Hazards, plotted as Events on an auto-rotating 3D globe. Refreshed every 6 hours by GitHub Actions, served free from GitHub Pages.

- Vocabulary: [CONTEXT.md](CONTEXT.md)
- Why it's built this way: [docs/adr](docs/adr)

## Layout

| Path | What |
| --- | --- |
| `collector/` | Python Refresh job: fetches feeds, groups Articles into Events, writes JSON |
| `collector/config.py` | Feeds, Significance thresholds, caps, timings |
| `collector/organisations.json` | Hand-kept Organisation HQ list (offline fallback) |
| `web/` | Vite + React + TypeScript + globe.gl front end |
| `web/public/data/latest.json` | Current Events (last 7 days), read by the site |
| `web/public/data/snapshots/` | One file per Refresh with the Events it touched (kept 90 days) |
| `.github/workflows/refresh.yml` | 6-hourly cron: collect → commit → build → deploy |

## Run locally

```bash
python -m venv .venv
```

```bash
.venv/Scripts/python -m pip install -r collector/requirements.txt
```

```bash
.venv/Scripts/python -m collector
```

```bash
npm install --prefix web
```

```bash
npm run dev --prefix web
```

Without `GEMINI_API_KEY` set, the collector uses the offline fallback (spaCy + GeoNames + Organisation HQ list): no Summaries, weaker grouping.

Tests: `.venv/Scripts/python -m pytest collector/tests`

## Deploy (one-time setup)

1. Create a **public** GitHub repo and push this folder to `main`.
2. Get a free API key from Google AI Studio and add it as a repository secret named `GEMINI_API_KEY` (Settings → Secrets and variables → Actions).
3. Settings → Pages → Source: **GitHub Actions**.
4. Actions → Refresh → **Run workflow** for the first Refresh. After that it runs at 00/06/12/18 UTC.

Optional: if Google renames or retires the Flash model, add a repository **variable** `GEMINI_MODEL` with the new model id (default `gemini-2.5-flash`).
