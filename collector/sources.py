"""Fetchers for each Signal Type: RSS (News), USGS (Earthquake), GDACS (Hazard)."""

from __future__ import annotations

import html
import re
from calendar import timegm
from datetime import datetime, timedelta, timezone

import feedparser

from . import config
from .models import Article, Event, Location, Source
from .util import http_get, iso, log, now_utc

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _clean(text: str, limit: int = 300) -> str:
    text = _WS_RE.sub(" ", html.unescape(_TAG_RE.sub(" ", text or ""))).strip()
    return text if len(text) <= limit else text[: limit - 1].rsplit(" ", 1)[0] + "…"


# --- News -------------------------------------------------------------------


def fetch_articles(since: datetime) -> list[Article]:
    articles: list[Article] = []
    for category, feeds in config.FEEDS.items():
        for outlet, url in feeds:
            try:
                parsed = feedparser.parse(http_get(url).content)
            except Exception as exc:  # one bad feed must not fail the Refresh
                log.warning("feed %s failed: %s", outlet, exc)
                continue
            count = 0
            for entry in parsed.entries:
                link = entry.get("link")
                title = _clean(entry.get("title", ""), 200)
                if not link or not title:
                    continue
                stamp = entry.get("published_parsed") or entry.get("updated_parsed")
                published = (
                    datetime.fromtimestamp(timegm(stamp), timezone.utc) if stamp else now_utc()
                )
                raw_date = (entry.get("published") or entry.get("updated") or "").strip()
                if stamp and len(raw_date) <= 10:  # date-only (e.g. Nature): assume end of that day
                    published = min(published + timedelta(days=1, seconds=-1), now_utc())
                if published < since:
                    continue
                articles.append(
                    Article(
                        outlet=outlet,
                        title=title,
                        url=link,
                        blurb=_clean(entry.get("summary", "")),
                        published_at=iso(published),
                        feed_category=category,  # type: ignore[arg-type]
                    )
                )
                count += 1
            log.info("feed %s: %d articles", outlet, count)
    return articles


# --- Earthquakes ------------------------------------------------------------

USGS_FEEDS = (
    "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_week.geojson",
    "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_week.geojson",
)


def _quake_significance(mag: float) -> float:
    return max(0.15, min(1.0, (mag - 4.0) / 4.0))


def fetch_earthquakes() -> list[Event]:
    events: dict[str, Event] = {}
    for url in USGS_FEEDS:
        try:
            features = http_get(url).json()["features"]
        except Exception as exc:
            log.warning("USGS feed failed: %s", exc)
            continue
        for f in features:
            p = f["properties"]
            mag = p.get("mag") or 0.0
            significant = "significant" in url
            if mag < config.EARTHQUAKE_MIN_MAGNITUDE and not significant:
                continue
            lon, lat = f["geometry"]["coordinates"][:2]
            when = iso(datetime.fromtimestamp(p["time"] / 1000, timezone.utc))
            event_id = f"eq-{f['id']}"
            events[event_id] = Event(
                id=event_id,
                signal_type="earthquake",
                title=p.get("title") or f"M {mag:.1f} earthquake",
                first_seen=when,
                last_seen=when,
                significance=_quake_significance(mag),
                location=Location(lat=lat, lon=lon, name=p.get("place") or "", basis="event_site"),
                sources=[Source("USGS", p.get("title") or "", p.get("url") or "", when)],
                details={
                    "magnitude": mag,
                    "depthKm": f["geometry"]["coordinates"][2],
                    "tsunami": bool(p.get("tsunami")),
                    "alert": p.get("alert"),
                },
            )
    log.info("earthquakes: %d", len(events))
    return list(events.values())


# --- Hazards ----------------------------------------------------------------

GDACS_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"
# Earthquakes come from USGS, so GDACS EQ is excluded to avoid duplicates.
HAZARD_TYPES = {
    "TC": "Tropical cyclone",
    "FL": "Flood",
    "VO": "Volcano",
    "WF": "Wildfire",
    "DR": "Drought",
}


def _gdacs_time(value: str) -> str:
    return iso(datetime.fromisoformat(value).replace(tzinfo=timezone.utc))


def fetch_hazards() -> list[Event]:
    today = now_utc()
    params = {
        "eventlist": ";".join(HAZARD_TYPES),
        "alertlevel": ";".join(sorted(config.HAZARD_ALERT_LEVELS)),
        "fromDate": (today - timedelta(days=config.KEEP_IN_LATEST_DAYS)).strftime("%Y-%m-%d"),
        "toDate": today.strftime("%Y-%m-%d"),
    }
    try:
        features = http_get(GDACS_URL, params=params).json().get("features", [])
    except Exception as exc:
        log.warning("GDACS failed: %s", exc)
        return []

    events = []
    for f in features:
        p = f["properties"]
        level = p.get("alertlevel")
        if level not in config.HAZARD_ALERT_LEVELS:
            continue
        kind = HAZARD_TYPES.get(p["eventtype"], p["eventtype"])
        name = p.get("name") or ""
        title = name if len(name) <= 90 else f"{kind}: {p.get('eventname') or 'multiple countries'}"
        countries = [c["countryname"] for c in p.get("affectedcountries") or []]
        place = countries[0] if len(countries) == 1 else (
            f"{len(countries)} countries" if countries else (p.get("country") or "")
        )
        lon, lat = f["geometry"]["coordinates"][:2]
        last_seen = min(_gdacs_time(p.get("datemodified") or p["todate"]), iso(today))
        report = (p.get("url") or {}).get("report", "")
        event_id = f"hz-{p['eventtype']}-{p['eventid']}"
        events.append(
            Event(
                id=event_id,
                signal_type="hazard",
                title=title,
                first_seen=_gdacs_time(p["fromdate"]),
                last_seen=last_seen,
                significance=1.0 if level == "Red" else 0.6,
                location=Location(lat=lat, lon=lon, name=place, basis="event_site"),
                sources=[Source("GDACS", _clean(p.get("htmldescription") or title, 200), report, last_seen)],
                details={
                    "hazardType": kind,
                    "alertLevel": level,
                    "severity": (p.get("severitydata") or {}).get("severitytext"),
                },
            )
        )
    log.info("hazards: %d", len(events))
    return events
