"""YouTube — uploads feed (RSS) cho mỗi channel_id."""
from __future__ import annotations

from core import Item
from sources import fetch_feed, filter_by_keywords

DEFAULTS = [
    {"name": "Fireship",           "id": "UCsBjURrPoezykLs9EqgamOA"},
    {"name": "AI Explained",       "id": "UCNJ1Ymd5yFuUPtn21xtRbbw"},
    {"name": "Matt Wolfe",         "id": "UChpleBmo18P08aKCIgti38g"},
    {"name": "Matthew Berman",     "id": "UCawZsQWqfGSbCI5yjkdVkTA"},
    {"name": "Two Minute Papers",  "id": "UCbfYPyITQ-7l4upoX8nvctg"},
]


def fetch(cfg: dict) -> list[Item]:
    channels = cfg.get("channels") or DEFAULTS
    items: list[Item] = []
    for ch in channels:
        url = f"https://www.youtube.com/feeds/videos.xml?channel_id={ch['id']}"
        items.extend(fetch_feed("AI YouTube", ch["name"], url))
    return filter_by_keywords(items, cfg.get("keywords", []))
