"""Shared models, paths, logging."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

STATE_DIR = Path.home() / ".tech-radar"
STATE_FILE = STATE_DIR / "seen.json"
LOG_FILE = STATE_DIR / "radar.log"

USER_AGENT = "Mozilla/5.0 (tech-radar/1.0)"
HTTP_TIMEOUT = 20
MAX_ITEMS_PER_FEED = 20


@dataclass
class Item:
    source: str           # group key — drives Slack section grouping
    title: str
    url: str
    published: str = ""
    summary: str = ""

    @property
    def id(self) -> str:
        return self.url.rstrip("/")


def log(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a") as f:
            f.write(line + "\n")
    except Exception:
        pass
