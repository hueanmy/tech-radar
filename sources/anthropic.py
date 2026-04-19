"""Anthropic — News, Engineering Blog, Claude Code Changelog, Courses, Events."""
from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from core import Item, MAX_ITEMS_PER_FEED, log
from sources import fetch_feed, http_get

FEEDS = {
    "news": ("Anthropic News", None,
             "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_news.xml"),
    "engineering": ("Engineering Blog", None,
                    "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_engineering.xml"),
    "changelog": ("Claude Code Changelog", None,
                  "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_changelog_claude_code.xml"),
    "courses": ("Anthropic Courses", None,
                "https://github.com/anthropics/courses/commits.atom"),
}

EVENTS_URL = "https://www.anthropic.com/events"
_DATE_RE = re.compile(
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4}\b"
)


def _fetch_events() -> list[Item]:
    try:
        html = http_get(EVENTS_URL)
    except Exception as e:
        log(f"  ✗ Events: {e}")
        return []

    soup = BeautifulSoup(html, "html.parser")
    items: list[Item] = []
    seen: set[str] = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/webinars/" not in href and "/events/" not in href:
            continue
        full_url = urljoin("https://www.anthropic.com", href).rstrip("/")
        if full_url in seen:
            continue
        if full_url.endswith("/webinars") or full_url.endswith("/events"):
            continue

        title = (a.get("aria-label") or "").strip()
        if not title:
            parent = a.find_parent(["div", "article", "li"]) or a
            heading = parent.find(["h2", "h3", "h4", "h5"])
            if heading:
                title = heading.get_text(strip=True)
        if not title:
            title = a.get_text(strip=True)
        if not title or len(title) < 5:
            continue

        date_str = ""
        parent = a.find_parent(["div", "article", "li"])
        if parent:
            m = _DATE_RE.search(parent.get_text(" ", strip=True))
            if m:
                date_str = m.group(0)

        seen.add(full_url)
        items.append(Item(source="Events", title=title, url=full_url, published=date_str))
        if len(items) >= MAX_ITEMS_PER_FEED:
            break

    log(f"  ✓ Events: {len(items)} items")
    return items


def fetch(cfg: dict) -> list[Item]:
    enabled = cfg.get("feeds") or list(FEEDS.keys()) + ["events"]
    items: list[Item] = []
    for key in enabled:
        if key == "events":
            items.extend(_fetch_events())
        elif key in FEEDS:
            source, label, url = FEEDS[key]
            items.extend(fetch_feed(source, label, url))
    return items
