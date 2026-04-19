"""GitHub Trending — dùng community RSS của mshibanami/GitHubTrendingRSS.

Hỗ trợ filter theo language (config.yaml: `languages`) và keyword (`keywords`).
"""
from __future__ import annotations

from core import Item
from sources import fetch_feed, filter_by_keywords

_BASE = "https://mshibanami.github.io/GitHubTrendingRSS/daily"


def fetch(cfg: dict) -> list[Item]:
    langs = cfg.get("languages") or ["all"]
    items: list[Item] = []
    for lang in langs:
        url = f"{_BASE}/{lang}.xml"
        items.extend(fetch_feed("GitHub Trending", lang, url))
    return filter_by_keywords(items, cfg.get("keywords", []))
