"""Apple Developer — News RSS + Swift blog."""
from __future__ import annotations

from core import Item
from sources import fetch_feed


def fetch(cfg: dict) -> list[Item]:
    items: list[Item] = []
    items.extend(fetch_feed("Apple/iOS", "Dev News",
                            "https://developer.apple.com/news/rss/news.rss"))
    items.extend(fetch_feed("Apple/iOS", "Swift Blog",
                            "https://www.swift.org/atom.xml"))
    return items
