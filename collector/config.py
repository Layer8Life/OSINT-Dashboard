"""Collector settings: feeds, Significance thresholds, and paths."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "web" / "public" / "data"
LATEST_PATH = DATA_DIR / "latest.json"
SNAPSHOT_DIR = DATA_DIR / "snapshots"
CACHE_DIR = ROOT / "collector" / ".cache"
ORGANISATIONS_PATH = ROOT / "collector" / "organisations.json"

REFRESH_HOURS = 6
# An Event with no new Sources for this long is Closed.
CLOSE_AFTER_HOURS = 48
# Events whose Last Seen is older than this drop out of latest.json (they remain in Snapshots).
KEEP_IN_LATEST_DAYS = 7
SNAPSHOT_RETENTION_DAYS = 90
# Articles older than this are ignored on a Refresh (covers the very first run and missed runs).
MAX_ARTICLE_AGE_HOURS = 30

MAX_NEW_NEWS_EVENTS_PER_CATEGORY = 40

EARTHQUAKE_MIN_MAGNITUDE = 4.5
HAZARD_ALERT_LEVELS = {"Orange", "Red"}

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "").strip() or "gemini-2.5-flash"
LLM_BATCH_SIZE = 40
# Free tier allows a handful of requests per minute; space calls out.
LLM_SECONDS_BETWEEN_CALLS = 7

CATEGORIES = ("tech", "science", "world")

# Feed category is only a hint; the LLM assigns the final Category.
FEEDS: dict[str, list[tuple[str, str]]] = {
    "tech": [
        ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
        ("The Verge", "https://www.theverge.com/rss/index.xml"),
        ("TechCrunch", "https://techcrunch.com/feed/"),
        ("Wired", "https://www.wired.com/feed/rss"),
        ("The Register", "https://www.theregister.com/headlines.atom"),
        ("BBC Technology", "https://feeds.bbci.co.uk/news/technology/rss.xml"),
    ],
    "science": [
        ("Nature", "https://www.nature.com/nature.rss"),
        ("ScienceDaily", "https://www.sciencedaily.com/rss/all.xml"),
        ("New Scientist", "https://www.newscientist.com/feed/home/"),
        ("Phys.org", "https://phys.org/rss-feed/"),
        ("NASA", "https://www.nasa.gov/news-release/feed/"),
        ("BBC Science", "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml"),
    ],
    "world": [
        ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml"),
        ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
        ("The Guardian", "https://www.theguardian.com/world/rss"),
        ("DW", "https://rss.dw.com/rdf/rss-en-world"),
        ("NPR", "https://feeds.npr.org/1004/rss.xml"),
        ("France 24", "https://www.france24.com/en/rss"),
    ],
}

USER_AGENT = "OSINT-Dashboard/1.0 (+https://github.com/)"
HTTP_TIMEOUT = 30
