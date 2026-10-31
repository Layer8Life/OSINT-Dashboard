"""One Refresh: fetch every Signal Type, merge into open Events, write latest.json and a Snapshot."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from . import config, sources
from .enrich import Group, enrich
from .models import Article, Event
from .util import iso, log, now_utc, parse_iso, short_hash


def news_significance(source_count: int) -> float:
    # 1 Source -> 0.2, 16+ Sources -> 1.0
    return round(min(1.0, 0.2 + 0.8 * math.log2(max(1, source_count)) / 4), 3)


def next_refresh_after(moment: datetime) -> datetime:
    """Refreshes run on the 00/06/12/18 UTC schedule."""
    base = moment.replace(minute=0, second=0, microsecond=0)
    hours_to_add = config.REFRESH_HOURS - (base.hour % config.REFRESH_HOURS)
    return base + timedelta(hours=hours_to_add)


def load_latest() -> tuple[dict[str, Event], dict]:
    if not config.LATEST_PATH.exists():
        return {}, {}
    data = json.loads(config.LATEST_PATH.read_text("utf-8"))
    events = {e["id"]: Event.from_json(e) for e in data.get("events", [])}
    return events, data.get("meta", {})


def _dedupe_articles(articles: list[Article], known_urls: set[str]) -> list[Article]:
    seen_urls, seen_titles, fresh = set(known_urls), set(), []
    for a in articles:
        title_key = a.title.lower()
        if a.url in seen_urls or title_key in seen_titles:
            continue
        seen_urls.add(a.url)
        seen_titles.add(title_key)
        fresh.append(a)
    return fresh


def apply_groups(events: dict[str, Event], groups: list[Group]) -> set[str]:
    """Attach groups to Events, applying the per-Category cap to new Events. Returns touched ids."""
    touched: set[str] = set()

    new_by_category: dict[str, list[Group]] = defaultdict(list)
    for g in groups:
        if g.event_id and g.event_id in events:
            event = events[g.event_id]
            urls = {s.url for s in event.sources}
            for art in g.articles:
                if art.url not in urls:
                    event.sources.append(art.as_source())
                    urls.add(art.url)
            event.last_seen = max([event.last_seen, *(a.published_at for a in g.articles)])
            event.significance = news_significance(len(event.sources))
            touched.add(event.id)
        else:
            new_by_category[g.category or g.articles[0].feed_category].append(g)

    for category, cat_groups in new_by_category.items():
        cat_groups.sort(key=lambda g: len(g.articles), reverse=True)
        dropped = len(cat_groups) - config.MAX_NEW_NEWS_EVENTS_PER_CATEGORY
        if dropped > 0:
            log.info("cap: dropping %d new %s Events", dropped, category)
        for g in cat_groups[: config.MAX_NEW_NEWS_EVENTS_PER_CATEGORY]:
            times = [a.published_at for a in g.articles]
            event = Event(
                id=f"news-{short_hash(g.articles[0].url)}",
                signal_type="news",
                title=g.title or g.articles[0].title,
                first_seen=min(times),
                last_seen=max(times),
                significance=news_significance(len(g.articles)),
                category=category,  # type: ignore[arg-type]
                summary=g.summary,
                location=g.location,
                sources=[a.as_source() for a in g.articles],
            )
            events[event.id] = event
            touched.add(event.id)
    return touched


def upsert_feed_events(events: dict[str, Event], incoming: list[Event]) -> set[str]:
    """Earthquake and Hazard Events come pre-identified from their feeds."""
    touched = set()
    for new in incoming:
        old = events.get(new.id)
        if old is not None:
            new.first_seen = min(old.first_seen, new.first_seen)
            if old.to_json() == new.to_json():
                continue
        events[new.id] = new
        touched.add(new.id)
    return touched


def close_and_prune(events: dict[str, Event], now: datetime) -> None:
    close_before = iso(now - timedelta(hours=config.CLOSE_AFTER_HOURS))
    drop_before = iso(now - timedelta(days=config.KEEP_IN_LATEST_DAYS))
    for event_id in list(events):
        event = events[event_id]
        if event.last_seen < drop_before:
            del events[event_id]
        elif event.last_seen < close_before:
            event.closed = True


def write_outputs(events: dict[str, Event], touched: set[str], meta: dict, now: datetime) -> None:
    ordered = sorted(events.values(), key=lambda e: e.last_seen, reverse=True)
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.LATEST_PATH.write_text(
        json.dumps({"meta": meta, "events": [e.to_json() for e in ordered]}, ensure_ascii=False),
        "utf-8",
    )

    config.SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    name = now.strftime("%Y-%m-%dT%H-%MZ") + ".json"
    snapshot = {"meta": meta, "events": [e.to_json() for e in ordered if e.id in touched]}
    (config.SNAPSHOT_DIR / name).write_text(json.dumps(snapshot, ensure_ascii=False), "utf-8")

    cutoff = now - timedelta(days=config.SNAPSHOT_RETENTION_DAYS)
    for path in config.SNAPSHOT_DIR.glob("*.json"):
        if path.name == "index.json":
            continue
        stamp = datetime.strptime(path.stem, "%Y-%m-%dT%H-%MZ").replace(tzinfo=timezone.utc)
        if stamp < cutoff:
            path.unlink()
    index = sorted(p.name for p in config.SNAPSHOT_DIR.glob("*.json") if p.name != "index.json")
    (config.SNAPSHOT_DIR / "index.json").write_text(json.dumps(index), "utf-8")


def run() -> dict:
    now = now_utc()
    events, _ = load_latest()
    close_and_prune(events, now)

    known_urls = {s.url for e in events.values() for s in e.sources}
    since = now - timedelta(hours=config.MAX_ARTICLE_AGE_HOURS)
    articles = _dedupe_articles(sources.fetch_articles(since), known_urls)
    log.info("new articles: %d", len(articles))

    open_events = [e for e in events.values() if not e.closed]
    groups, method = enrich(articles, open_events)
    touched = apply_groups(events, groups)
    touched |= upsert_feed_events(events, sources.fetch_earthquakes())
    touched |= upsert_feed_events(events, sources.fetch_hazards())
    close_and_prune(events, now)

    counts: dict[str, int] = defaultdict(int)
    for e in events.values():
        counts[e.signal_type] += 1
        if e.location is None:
            counts["unplaced"] += 1
    meta = {
        "generatedAt": iso(now),
        "nextRefreshAt": iso(next_refresh_after(now)),
        "refreshHours": config.REFRESH_HOURS,
        "enrichment": method,
        "newArticles": len(articles),
        "counts": dict(counts),
    }
    write_outputs(events, touched, meta, now)
    log.info("refresh done: %s", meta)
    return meta
