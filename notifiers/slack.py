"""Slack notifier — webhook (ưu tiên) hoặc bot token DM.

Đọc credentials theo thứ tự:
  1. CLAUDE_WATCHER_SLACK_*  (zshrc — đặt riêng cho project này)
  2. SLACK_*                 (env/`.env` generic)
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import requests

from core import HTTP_TIMEOUT, Item, log


def _env(*names: str) -> str:
    for n in names:
        v = os.environ.get(n, "").strip()
        if v:
            return v
    return ""


SLACK_WEBHOOK_URL = _env("CLAUDE_WATCHER_SLACK_WEBHOOK_URL", "SLACK_WEBHOOK_URL")
SLACK_BOT_TOKEN = _env("CLAUDE_WATCHER_SLACK_BOT_TOKEN", "SLACK_BOT_TOKEN")
SLACK_USER_ID = _env("CLAUDE_WATCHER_SLACK_USER_ID", "SLACK_USER_ID")
SLACK_CHANNEL = _env("CLAUDE_WATCHER_SLACK_CHANNEL", "SLACK_CHANNEL")
SITE_URL = _env("TECH_RADAR_SITE_URL") or "https://hueanmy.github.io/tech-radar/"

ICONS = {
    "Events": "📅",
    "Anthropic News": "📣",
    "Engineering Blog": "🛠️",
    "Claude Code Changelog": "🚀",
    "Anthropic Courses": "🎓",
    "AI YouTube": "📺",
    "Electron": "🖥️",
    "Apple/iOS": "🍎",
    "Playwright": "🎭",
    "GitHub Trending": "📈",
    "Security": "🛡️",
}


MAX_ITEMS_PER_CATEGORY = 5


def format_slack_message(new_items: list[Item]) -> dict:
    """Compact digest — summary + item list per source + CTA link to the site."""
    by_source: dict[str, list[Item]] = {}
    for item in new_items:
        by_source.setdefault(item.source, []).append(item)

    total = len(new_items)
    summary = " · ".join(
        f"{ICONS.get(s, '•')} {s} ({len(items)})"
        for s, items in sorted(by_source.items())
    )

    blocks = [
        {"type": "header", "text": {"type": "plain_text",
                                    "text": f"🔔 {total} update mới hôm nay"}},
        {"type": "context", "elements": [{"type": "mrkdwn",
                                          "text": f"_Quét lúc {datetime.now():%Y-%m-%d %H:%M}_"}]},
        {"type": "section", "text": {"type": "mrkdwn", "text": summary}},
        {"type": "divider"},
    ]

    for source, items in sorted(by_source.items()):
        icon = ICONS.get(source, "•")
        lines = [f"*{icon} {source}* ({len(items)})"]
        for it in items[:MAX_ITEMS_PER_CATEGORY]:
            lines.append(f"• <{it.url}|{it.title}>")
        if len(items) > MAX_ITEMS_PER_CATEGORY:
            lines.append(f"_…và {len(items) - MAX_ITEMS_PER_CATEGORY} mục khác_")
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(lines)}})

    blocks.append({
        "type": "actions",
        "elements": [{
            "type": "button",
            "style": "primary",
            "text": {"type": "plain_text", "text": "📖 Đọc đầy đủ trên Tech Radar"},
            "url": SITE_URL,
        }],
    })

    return {
        "text": f"{total} update mới hôm nay — {SITE_URL}",
        "blocks": blocks,
    }


def send_slack(payload: dict) -> bool:
    if SLACK_WEBHOOK_URL:
        try:
            resp = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=HTTP_TIMEOUT)
            resp.raise_for_status()
            log("  ✓ Sent to Slack via webhook")
            return True
        except Exception as e:
            log(f"  ✗ Webhook failed: {e}")

    if SLACK_BOT_TOKEN and SLACK_USER_ID:
        try:
            resp = requests.post(
                "https://slack.com/api/chat.postMessage",
                headers={
                    "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                json={"channel": SLACK_USER_ID, **payload},
                timeout=HTTP_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("ok"):
                log(f"  ✓ Sent to Slack via bot token (DM to {SLACK_USER_ID})")
                return True
            log(f"  ✗ Slack API error: {data.get('error')}")
        except Exception as e:
            log(f"  ✗ Bot token send failed: {e}")

    log("  ✗ No Slack credentials configured")
    return False
