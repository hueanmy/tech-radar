"""Security — các feed breaking news về infosec, vulnerabilities, exploits."""
from __future__ import annotations

from core import Item
from sources import fetch_feed, filter_by_keywords

FEEDS = [
    ("The Hacker News",      "https://feeds.feedburner.com/TheHackersNews"),
    ("Bleeping Computer",    "https://www.bleepingcomputer.com/feed/"),
    ("Krebs on Security",    "https://krebsonsecurity.com/feed/"),
    ("Schneier on Security", "https://www.schneier.com/feed/atom/"),
    ("SecurityWeek",         "https://www.securityweek.com/feed/"),
    ("Google Project Zero",  "https://googleprojectzero.blogspot.com/feeds/posts/default"),
]


def fetch(cfg: dict) -> list[Item]:
    enabled_labels = cfg.get("feeds")
    items: list[Item] = []
    for label, url in FEEDS:
        if enabled_labels and label not in enabled_labels:
            continue
        items.extend(fetch_feed("Security", label, url))
    return filter_by_keywords(items, cfg.get("keywords") or [])
