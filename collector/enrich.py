"""Turns new Articles into News Event groups: grouping, Category, Location and Summary.

Primary path is Gemini's free tier; the offline fallback (geo.py + title similarity) runs
for any batch the LLM cannot handle, so a Refresh always completes. See ADR 0002.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Optional

import requests

from . import config, geo
from .models import Article, Category, Event, Location
from .util import log


@dataclass
class Group:
    """Articles that belong together. event_id set means they join an existing open Event."""

    articles: list[Article]
    event_id: Optional[str] = None
    title: str = ""
    category: Optional[Category] = None
    summary: Optional[str] = None
    location: Optional[Location] = None
    key: str = field(default="")


# --- Fallback ---------------------------------------------------------------

_STOP = set(
    "the a an and or of to in on for with at by from as is are was were be has have had it its "
    "this that after over into new says say said how why what who will can could may more than "
    "about up out not but his her their they you we our us".split()
)
SIMILARITY_THRESHOLD = 0.45


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2 and w not in _STOP}


def _similarity(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def fallback_groups(articles: list[Article], open_events: list[Event]) -> list[Group]:
    existing = [(e, _tokens(e.title)) for e in open_events]
    groups: list[tuple[Group, set[str]]] = []
    for art in articles:
        toks = _tokens(art.title)
        best, best_score = None, SIMILARITY_THRESHOLD
        for event, etoks in existing:
            score = _similarity(toks, etoks)
            if event.category == art.feed_category and score >= best_score:
                best, best_score = ("event", event), score
        for group, gtoks in groups:
            score = _similarity(toks, gtoks)
            if group.category == art.feed_category and score >= best_score:
                best, best_score = ("group", group), score
        if best and best[0] == "event":
            match = next((g for g, _ in groups if g.event_id == best[1].id), None)
            if match is None:
                groups.append((Group([art], event_id=best[1].id), toks))
            else:
                match.articles.append(art)
        elif best:
            best[1].articles.append(art)
        else:
            group = Group(
                [art],
                title=art.title,
                category=art.feed_category,
                location=geo.locate(art.title, art.blurb),
            )
            groups.append((group, toks))
    return [g for g, _ in groups]


# --- LLM --------------------------------------------------------------------

PROMPT = """You are the enrichment step of an OSINT news dashboard. Group news Articles into Events.

An Event is one real-world happening. Several Articles from different outlets about the same
happening belong to the same Event. Attach an Article to an existing open Event when it reports
on that same happening; otherwise create a new Event (several new Articles may share one).

For each NEW Event provide:
- "title": neutral, factual, at most 90 characters, no outlet names.
- "category": exactly one of "tech", "science", "world" (feedCategory is only a hint).
  tech = technology, computing, internet, AI, gadgets, tech companies and policy.
  science = research, space, health/medical science, climate science, nature.
  world = politics, conflict, economy, society, disasters, everything else.
- "summary": 2-3 sentences in your own words, using only the facts in the headlines and blurbs.
  Do not copy sentences from the blurbs.
- "location": where to plot it, or null.
  If the Event happened at an identifiable place, use that place: basis "event_site".
  Otherwise, if a main organisation or institution is named, use its headquarters city:
  basis "organisation_hq" and set "organisation" to its name.
  Otherwise null. Never guess a place that is not supported by the text.
  "lat"/"lon" are decimal degrees of the place; "name" is a short human-readable place name.

Reply with JSON only, in this exact shape:
{"assignments":[{"article":<article index>,"event":"<existing event id or new event key>"}],
 "newEvents":[{"key":"<new event key, e.g. n1>","title":"...","category":"tech|science|world",
   "summary":"...","location":{"name":"...","lat":0.0,"lon":0.0,"basis":"event_site|organisation_hq",
   "organisation":null}}]}
Every article index must appear exactly once in "assignments".

OPEN EVENTS:
%s

NEW ARTICLES:
%s
"""


class LLMUnavailable(Exception):
    pass


def _call_gemini(prompt: str) -> dict:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{config.GEMINI_MODEL}:generateContent"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2},
    }
    try:
        resp = requests.post(
            url, json=body, headers={"x-goog-api-key": config.GEMINI_API_KEY}, timeout=120
        )
    except requests.RequestException as exc:
        raise LLMUnavailable(str(exc)) from exc
    if resp.status_code in (401, 403, 429) or resp.status_code >= 500:
        raise LLMUnavailable(f"HTTP {resp.status_code}: {resp.text[:200]}")
    resp.raise_for_status()
    text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text)


def _parse_location(raw: object) -> Optional[Location]:
    if not isinstance(raw, dict):
        return None
    try:
        lat, lon = float(raw["lat"]), float(raw["lon"])
    except (KeyError, TypeError, ValueError):
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180) or (lat == 0 and lon == 0):
        return None
    basis = raw.get("basis")
    if basis not in ("event_site", "organisation_hq"):
        return None
    org = raw.get("organisation") if basis == "organisation_hq" else None
    return Location(lat, lon, str(raw.get("name") or ""), basis, org or None)


def _llm_batch(batch: list[Article], context: list[dict], batch_no: int) -> list[Group]:
    articles_json = json.dumps(
        [
            {"index": i, "outlet": a.outlet, "title": a.title, "blurb": a.blurb, "feedCategory": a.feed_category}
            for i, a in enumerate(batch)
        ],
        ensure_ascii=False,
    )
    result = _call_gemini(PROMPT % (json.dumps(context, ensure_ascii=False), articles_json))

    known_ids = {c["id"] for c in context}
    new_meta = {}
    for raw in result.get("newEvents", []):
        key = str(raw.get("key", ""))
        category = raw.get("category")
        new_meta[key] = Group(
            [],
            title=str(raw.get("title") or "")[:120],
            category=category if category in config.CATEGORIES else None,
            summary=(raw.get("summary") or None),
            location=_parse_location(raw.get("location")),
            key=f"b{batch_no}-{key}",
        )

    by_target: dict[str, Group] = {}
    assigned: set[int] = set()
    for item in result.get("assignments", []):
        try:
            idx = int(item["article"])
            target = str(item["event"])
        except (KeyError, TypeError, ValueError):
            continue
        if idx in assigned or not 0 <= idx < len(batch):
            continue
        if target in known_ids:
            group = by_target.setdefault(target, Group([], event_id=target))
        elif target in new_meta:
            group = by_target.setdefault(target, new_meta[target])
        else:
            continue
        group.articles.append(batch[idx])
        assigned.add(idx)

    groups = [g for g in by_target.values() if g.articles]
    for g in groups:
        if g.event_id is None:
            first = g.articles[0]
            g.title = g.title or first.title
            g.category = g.category or first.feed_category
    leftovers = [a for i, a in enumerate(batch) if i not in assigned]
    if leftovers:
        log.info("LLM left %d articles unassigned; using fallback for them", len(leftovers))
        groups += fallback_groups(leftovers, [])
    return groups


def enrich(articles: list[Article], open_events: list[Event]) -> tuple[list[Group], str]:
    """Returns (groups, method) where method is "llm", "fallback" or "mixed"."""
    if not articles:
        return [], "none"
    if not config.GEMINI_API_KEY:
        log.info("no GEMINI_API_KEY; using offline fallback")
        return fallback_groups(articles, open_events), "fallback"

    news_open = [e for e in open_events if e.signal_type == "news" and not e.closed]
    news_open.sort(key=lambda e: e.last_seen, reverse=True)
    context = [{"id": e.id, "title": e.title, "category": e.category} for e in news_open[:150]]

    groups: list[Group] = []
    used_llm = used_fallback = False
    llm_ok = True
    size = config.LLM_BATCH_SIZE
    for batch_no, start in enumerate(range(0, len(articles), size)):
        batch = articles[start : start + size]
        if llm_ok:
            try:
                if batch_no:
                    time.sleep(config.LLM_SECONDS_BETWEEN_CALLS)
                batch_groups = _llm_batch(batch, context, batch_no)
                used_llm = True
            except LLMUnavailable as exc:
                log.warning("LLM unavailable, switching to fallback: %s", exc)
                llm_ok = False
            except Exception as exc:  # malformed reply etc.: fallback for this batch only
                log.warning("LLM batch %d failed: %s", batch_no, exc)
                batch_groups = None
            else:
                groups += batch_groups
                # New Events from this batch become matchable by later batches.
                context += [
                    {"id": g.key, "title": g.title, "category": g.category}
                    for g in batch_groups
                    if g.event_id is None and g.key
                ]
                continue
        used_fallback = True
        groups += fallback_groups(batch, news_open)

    groups = _merge_cross_batch(groups)
    method = "mixed" if used_llm and used_fallback else ("llm" if used_llm else "fallback")
    return groups, method


def _merge_cross_batch(groups: list[Group]) -> list[Group]:
    """A later batch may assign Articles to a new-Event key created by an earlier batch."""
    by_key = {g.key: g for g in groups if g.event_id is None and g.key}
    merged: list[Group] = []
    for g in groups:
        if g.event_id and g.event_id in by_key:
            by_key[g.event_id].articles += g.articles
        else:
            merged.append(g)
    return merged
