"""Playwright — GitHub releases (microsoft/playwright)."""
from __future__ import annotations

from core import Item
from sources import fetch_feed


def fetch(cfg: dict) -> list[Item]:
    return fetch_feed(
        "Playwright", "Releases",
        "https://github.com/microsoft/playwright/releases.atom",
    )
