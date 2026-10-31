"""Offline Location lookup: GeoNames gazetteer plus the hand-kept Organisation HQ list.

Used by the fallback enrichment path, and to sanity-check nothing else.
"""

from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from dataclasses import dataclass
from functools import lru_cache

from . import config
from .models import Location
from .util import http_get, log

CITIES_URL = "https://download.geonames.org/export/dump/cities15000.zip"
COUNTRIES_URL = "https://download.geonames.org/export/dump/countryInfo.txt"

# Heuristic (no spaCy) matching only trusts big places, to avoid "Nice", "Mobile", "Reading"...
HEURISTIC_MIN_POPULATION = 500_000
AMBIGUOUS_WORDS = {
    "nice", "mobile", "reading", "bath", "split", "most", "orange", "victoria", "march",
    "may", "university", "independence", "liberty", "union", "commerce", "phoenix",
}


@dataclass(frozen=True)
class Place:
    name: str
    lat: float
    lon: float
    population: int
    is_country: bool = False


def _download(url: str, filename: str) -> bytes:
    path = config.CACHE_DIR / filename
    if not path.exists():
        log.info("downloading %s", url)
        config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_bytes(http_get(url).content)
    return path.read_bytes()


@lru_cache(maxsize=1)
def gazetteer() -> dict[str, Place]:
    places: dict[str, Place] = {}
    by_geoname_id: dict[str, Place] = {}

    with zipfile.ZipFile(io.BytesIO(_download(CITIES_URL, "cities15000.zip"))) as zf:
        with zf.open("cities15000.txt") as fh:
            reader = csv.reader(io.TextIOWrapper(fh, "utf-8"), delimiter="\t", quoting=csv.QUOTE_NONE)
            for row in reader:
                place = Place(row[1], float(row[4]), float(row[5]), int(row[14] or 0))
                by_geoname_id[row[0]] = place
                for key in {row[1].lower(), row[2].lower()}:
                    if key not in places or places[key].population < place.population:
                        places[key] = place

    # Countries are plotted at their capital (countryInfo has no coordinates).
    text = _download(COUNTRIES_URL, "countryInfo.txt").decode("utf-8")
    capitals = {p.name.lower(): p for p in by_geoname_id.values()}
    for line in text.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        cols = line.split("\t")
        country, capital = cols[4], cols[5]
        cap = capitals.get(capital.lower())
        if cap:
            places[country.lower()] = Place(country, cap.lat, cap.lon, int(cols[7] or 0), True)
    for alias, country in {"us": "united states", "usa": "united states", "uk": "united kingdom",
                           "britain": "united kingdom", "england": "united kingdom",
                           "america": "united states", "dr congo": "democratic republic of the congo",
                           "drc": "democratic republic of the congo", "gaza": "palestinian territory"}.items():
        if country in places:
            places[alias] = places[country]
    return places


@lru_cache(maxsize=1)
def organisations() -> dict[str, dict]:
    raw = json.loads(config.ORGANISATIONS_PATH.read_text("utf-8"))
    index = {}
    for name, info in raw.items():
        for alias in [name, *info.get("aliases", [])]:
            index[alias.lower()] = {"name": name, **info}
    return index


@lru_cache(maxsize=1)
def _nlp():
    try:
        import spacy

        return spacy.load("en_core_web_sm", disable=["lemmatizer"])
    except Exception:
        log.info("spaCy model unavailable; using heuristic entity extraction")
        return None


_POSSESSIVE_RE = re.compile(r"['’]s$")


def _key(name: str) -> str:
    return _POSSESSIVE_RE.sub("", name.strip(" .,:;\"'’").lower()).removeprefix("the ")


_CAPS_RE = re.compile(r"\b([A-Z][\w.&'-]*(?:\s+[A-Z][\w.&'-]*){0,2})")


def _candidates(text: str) -> tuple[list[str], list[str]]:
    """Return (place candidates, organisation candidates) in reading order."""
    nlp = _nlp()
    if nlp is not None:
        doc = nlp(text)
        places = [e.text for e in doc.ents if e.label_ in ("GPE", "LOC")]
        orgs = [e.text for e in doc.ents if e.label_ in ("ORG", "PRODUCT", "PERSON")]
        return places, orgs + places
    spans = []
    for match in _CAPS_RE.finditer(text):
        words = match.group(1).split()
        # every sub-span, longest first, so "New York City" beats "York"
        for size in range(len(words), 0, -1):
            for i in range(len(words) - size + 1):
                spans.append(" ".join(words[i : i + size]))
    return spans, spans


def locate(title: str, blurb: str) -> Location | None:
    """Event Site if a place is named, else Organisation HQ, else None (Unplaced)."""
    text = f"{title}. {blurb}"
    place_names, org_names = _candidates(text)
    heuristic = _nlp() is None
    places = gazetteer()
    for name in place_names:
        key = _key(name)
        place = places.get(key)
        if not place or key in AMBIGUOUS_WORDS:
            continue
        if heuristic and not place.is_country and place.population < HEURISTIC_MIN_POPULATION:
            continue
        return Location(place.lat, place.lon, place.name, "event_site")
    orgs = organisations()
    for name in org_names:
        org = orgs.get(_key(name))
        if org:
            return Location(org["lat"], org["lon"], org["city"], "organisation_hq", org["name"])
    return None
