from datetime import datetime, timedelta, timezone

import pytest

from collector import config, enrich as enrich_mod, refresh
from collector.enrich import Group, enrich, fallback_groups
from collector.models import Article, Event
from collector.util import iso

NOW = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)


def art(title, url=None, category="world", hours_ago=1, outlet="BBC"):
    return Article(outlet, title, url or f"https://x/{abs(hash(title))}", "", iso(NOW - timedelta(hours=hours_ago)), category)


def news_event(eid, title, hours_ago=1, category="world"):
    t = iso(NOW - timedelta(hours=hours_ago))
    return Event(id=eid, signal_type="news", title=title, first_seen=t, last_seen=t, significance=0.2, category=category)


@pytest.fixture(autouse=True)
def no_geo(monkeypatch):
    monkeypatch.setattr(enrich_mod.geo, "locate", lambda title, blurb: None)


def test_fallback_groups_similar_titles_together():
    groups = fallback_groups(
        [
            art("Massive earthquake strikes northern Japan coast"),
            art("Earthquake strikes northern Japan coast, tsunami warning"),
            art("Apple unveils new MacBook Pro", category="tech"),
        ],
        [],
    )
    assert sorted(len(g.articles) for g in groups) == [1, 2]


def test_fallback_attaches_to_open_event_of_same_category():
    open_event = news_event("news-1", "Hurricane Zeta makes landfall in Louisiana")
    groups = fallback_groups([art("Hurricane Zeta makes landfall in Louisiana, thousands evacuate")], [open_event])
    assert groups[0].event_id == "news-1"


def test_apply_groups_updates_existing_event_last_seen_and_sources():
    events = {"news-1": news_event("news-1", "Story", hours_ago=10)}
    events["news-1"].sources = []
    refresh.apply_groups(events, [Group([art("Story follow-up", hours_ago=1)], event_id="news-1")])
    assert events["news-1"].last_seen == iso(NOW - timedelta(hours=1))
    assert len(events["news-1"].sources) == 1


def test_apply_groups_caps_new_events_per_category(monkeypatch):
    monkeypatch.setattr(config, "MAX_NEW_NEWS_EVENTS_PER_CATEGORY", 2)
    groups = [Group([art(f"t{i}") for _ in range(n)], title=f"t{n}", category="world") for i, n in enumerate([1, 3, 2])]
    # give each article a unique url
    for gi, g in enumerate(groups):
        for ai, a in enumerate(g.articles):
            a.url = f"https://x/{gi}/{ai}"
    events = {}
    refresh.apply_groups(events, groups)
    assert sorted(len(e.sources) for e in events.values()) == [2, 3]


def test_close_after_48h_and_drop_after_7d():
    events = {
        "a": news_event("a", "fresh", hours_ago=5),
        "b": news_event("b", "quiet", hours_ago=50),
        "c": news_event("c", "old", hours_ago=24 * 8),
    }
    refresh.close_and_prune(events, NOW)
    assert not events["a"].closed
    assert events["b"].closed
    assert "c" not in events


def test_next_refresh_follows_six_hour_schedule():
    assert refresh.next_refresh_after(datetime(2026, 10, 31, 13, 20, tzinfo=timezone.utc)).hour == 18
    assert refresh.next_refresh_after(datetime(2026, 10, 31, 18, 5, tzinfo=timezone.utc)).hour == 0


def test_news_significance_grows_with_sources():
    assert refresh.news_significance(1) == 0.2
    assert refresh.news_significance(16) == 1.0
    assert refresh.news_significance(4) > refresh.news_significance(2)


def test_llm_reply_is_parsed_and_validated(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test")
    reply = {
        "assignments": [
            {"article": 0, "event": "n1"},
            {"article": 1, "event": "n1"},
            {"article": 2, "event": "news-open"},
        ],
        "newEvents": [
            {
                "key": "n1",
                "title": "OpenAI releases model",
                "category": "tech",
                "summary": "A model was released.",
                "location": {"name": "San Francisco", "lat": 37.76, "lon": -122.41, "basis": "organisation_hq", "organisation": "OpenAI"},
            }
        ],
    }
    monkeypatch.setattr(enrich_mod, "_call_gemini", lambda prompt: reply)
    open_event = news_event("news-open", "Election results")
    groups, method = enrich([art("a"), art("b"), art("c")], [open_event])
    assert method == "llm"
    new = next(g for g in groups if g.event_id is None)
    assert new.category == "tech" and len(new.articles) == 2
    assert new.location.basis == "organisation_hq" and new.location.organisation == "OpenAI"
    assert next(g for g in groups if g.event_id == "news-open").articles[0].title == "c"


def test_llm_bad_location_becomes_unplaced(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test")
    reply = {
        "assignments": [{"article": 0, "event": "n1"}],
        "newEvents": [{"key": "n1", "title": "x", "category": "science", "summary": "s",
                       "location": {"name": "?", "lat": 0, "lon": 0, "basis": "event_site"}}],
    }
    monkeypatch.setattr(enrich_mod, "_call_gemini", lambda prompt: reply)
    groups, _ = enrich([art("a")], [])
    assert groups[0].location is None


def test_llm_unavailable_falls_back(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test")

    def boom(prompt):
        raise enrich_mod.LLMUnavailable("429")

    monkeypatch.setattr(enrich_mod, "_call_gemini", boom)
    groups, method = enrich([art("a story")], [])
    assert method == "fallback" and len(groups) == 1
