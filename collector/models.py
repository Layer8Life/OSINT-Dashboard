"""Domain types. Terms follow CONTEXT.md."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal, Optional

SignalType = Literal["news", "earthquake", "hazard"]
Category = Literal["tech", "science", "world"]
LocationBasis = Literal["event_site", "organisation_hq"]


@dataclass
class Source:
    outlet: str
    title: str
    url: str
    published_at: str  # ISO 8601 UTC


@dataclass
class Location:
    lat: float
    lon: float
    name: str
    basis: LocationBasis
    organisation: Optional[str] = None


@dataclass
class Event:
    id: str
    signal_type: SignalType
    title: str
    first_seen: str
    last_seen: str
    significance: float  # 0..1, drives marker size
    category: Optional[Category] = None  # News only
    summary: Optional[str] = None
    location: Optional[Location] = None  # None means Unplaced
    sources: list[Source] = field(default_factory=list)
    closed: bool = False
    # Signal-specific detail, e.g. {"magnitude": 6.1} or {"alertLevel": "Red", "hazardType": "TC"}
    details: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_json(data: dict) -> "Event":
        loc = data.get("location")
        return Event(
            id=data["id"],
            signal_type=data["signal_type"],
            title=data["title"],
            first_seen=data["first_seen"],
            last_seen=data["last_seen"],
            significance=data.get("significance", 0.0),
            category=data.get("category"),
            summary=data.get("summary"),
            location=Location(**loc) if loc else None,
            sources=[Source(**s) for s in data.get("sources", [])],
            closed=data.get("closed", False),
            details=data.get("details", {}),
        )


@dataclass
class Article:
    """One RSS item, before it is attached to an Event."""

    outlet: str
    title: str
    url: str
    blurb: str
    published_at: str
    feed_category: Category

    def as_source(self) -> Source:
        return Source(self.outlet, self.title, self.url, self.published_at)
