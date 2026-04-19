"""Electron — blog posts + GitHub releases."""
from __future__ import annotations

from core import Item
from sources import fetch_feed


def fetch(cfg: dict) -> list[Item]:
    items: list[Item] = []
    items.extend(fetch_feed("Electron", "Blog",
                            "https://www.electronjs.org/blog/rss.xml"))
    items.extend(fetch_feed("Electron", "Releases",
                            "https://github.com/electron/electron/releases.atom"))
    return items
