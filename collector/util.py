from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone

import requests

from . import config

log = logging.getLogger("collector")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def short_hash(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:12]


def http_get(url: str, **kwargs) -> requests.Response:
    headers = {"User-Agent": config.USER_AGENT, **kwargs.pop("headers", {})}
    resp = requests.get(url, headers=headers, timeout=config.HTTP_TIMEOUT, **kwargs)
    resp.raise_for_status()
    return resp
